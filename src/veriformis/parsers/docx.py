"""DOCX -> Veriformis IR.

Read the document body, map paragraph styles to IR block roles, collect
semantic run formatting (bold/italic/strike/code), and drop absolutely
everything else. Tracked changes are accepted (insertions kept, deletions
dropped); comments, bookmarks, revision marks are stripped entirely.
Colors, fonts, highlighting, and direct-formatting runs that don't carry
semantic meaning are ignored.

The parser walks the OOXML tree directly via lxml rather than relying on
python-docx's high-level API, because we need ordered iteration of body
children (paragraphs + tables interleaved) and fine control over list
detection and hyperlink unwrapping.

Provenance follows the extracted-stream contract. The canonical stream orders
body blocks first, then footnotes by ID, then endnotes by ID. Each block is
separated by ``"\\n\\n"`` and receives a unique span and block index into that
stream. These locations never refer to the raw ZIP bytes. ``page`` stays
``None`` because DOCX extraction is unpaginated.
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path

from docx import Document as OpenDocument
from lxml import etree

from veriformis.diagnostics import (
    DiagnosticLocation,
    make_diagnostic,
    make_parse_report,
)
from veriformis.ir import (
    Blockquote,
    Bold,
    Cell,
    Citation,
    Code,
    CodeBlock,
    Document,
    Endnote,
    EndnoteRef,
    Footnote,
    FootnoteRef,
    Heading,
    HorizontalRule,
    Image,
    Inline,
    Italic,
    LineBreak,
    Link,
    ListBlock,
    ListItem,
    Math,
    Paragraph,
    Strikethrough,
    Subscript,
    Superscript,
    Table,
    Text,
    attach_canonical_provenance,
)
from veriformis.parsers import docx_styles as style_map
from veriformis.sources import ParseResult, register_source

_CITATION_RE = re.compile(r"\[@([A-Za-z][\w:.\-]*)(?:,\s*([^\]]+))?\]")
PARSER_VERSION = "1.2.0"


def _split_citations_in_text(value: str) -> list[Inline]:
    """Split a plain text string into alternating Text and Citation
    nodes. Text segments without any citation pattern produce a single
    Text node."""
    result: list[Inline] = []
    last = 0
    for m in _CITATION_RE.finditer(value):
        if m.start() > last:
            result.append(Text(value=value[last : m.start()]))
        result.append(Citation(key=m.group(1), locator=m.group(2)))
        last = m.end()
    if last < len(value):
        result.append(Text(value=value[last:]))
    if not result and value:
        result.append(Text(value=value))
    return result


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"

NS = {"w": W_NS, "r": R_NS, "a": A_NS, "pic": PIC_NS}


def _q(tag: str) -> str:
    """Shortcut: `w:pPr` -> `{...}pPr`."""
    prefix, local = tag.split(":", 1)
    return f"{{{NS[prefix]}}}{local}"


_BODY_WRAPPER_TAGS = {
    _q("w:customXml"),
    _q("w:sdt"),
}

_PARAGRAPH_WRAPPER_TAGS = {
    _q("w:bdo"),
    _q("w:customXml"),
    _q("w:dir"),
    _q("w:fldSimple"),
    _q("w:sdt"),
    _q("w:smartTag"),
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_docx_file(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> ParseResult:
    """File entry: parse, register the source, return ParseResult."""
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    doc, stream, diagnostic_specs = _parse_docx(p, raw_bytes=captured)
    source = register_source(
        p,
        "docx",
        stream,
        logical_path=logical_path,
        parser_version=PARSER_VERSION,
        raw_bytes=captured,
    )
    doc.source_id = source.id
    diagnostics = [
        make_diagnostic(
            source_id=source.id,
            parser_name=source.parser,
            parser_version=source.parser_version,
            **spec,
        )
        for spec in diagnostic_specs
    ]
    return ParseResult(
        document=doc,
        source=source,
        diagnostics=make_parse_report(
            source_id=source.id,
            parser_name=source.parser,
            parser_version=source.parser_version,
            diagnostics=diagnostics,
        ),
    )


def _parse_docx(
    path: Path, *, raw_bytes: bytes | None = None
) -> tuple[Document, str, list[dict]]:
    """Parse a .docx into a Document and its extracted-text stream."""
    docx = OpenDocument(BytesIO(raw_bytes) if raw_bytes is not None else path)
    body = docx.element.body

    # Build a relationship map: rId -> target (for hyperlinks and images)
    rels: dict[str, str] = {}
    part = docx.part
    for rel_id, rel in part.rels.items():
        rels[rel_id] = rel.target_ref

    # Inventory loss before revision cleanup mutates the source tree. The
    # inventory uses the same boundary allowlists as the parser, so an OOXML
    # construct is either consumed, recovered through a transparent wrapper,
    # or represented by a located diagnostic.
    diagnostic_specs = _loss_diagnostic_specs(body, rels)

    # Pre-process: strip revision marks, comments, bookmarks, etc.
    _clean_revisions(body)

    # Build numbering info for list detection
    numbering = _load_numbering(docx)

    doc_ir = Document()

    # Parse footnotes and endnotes (from word/{foot,end}notes.xml) before
    # the body walk.
    note_source = raw_bytes if raw_bytes is not None else path
    doc_ir.footnotes, footnote_specs = _load_notes(
        note_source, rels, numbering, note_kind="footnote"
    )
    doc_ir.endnotes, endnote_specs = _load_notes(
        note_source, rels, numbering, note_kind="endnote"
    )
    diagnostic_specs.extend(footnote_specs)
    diagnostic_specs.extend(endnote_specs)
    diagnostic_specs.extend(
        _unresolved_note_reference_specs(
            body,
            footnote_ids=set(doc_ir.footnotes),
            endnote_ids=set(doc_ir.endnotes),
        )
    )

    _walk_body(body, doc_ir.children, rels, numbering)
    return doc_ir, attach_canonical_provenance(doc_ir), diagnostic_specs


# ---------------------------------------------------------------------------
# Footnote/endnote loading (word/footnotes.xml + word/endnotes.xml)
# ---------------------------------------------------------------------------

_NOTE_CONFIG = {
    "footnote": {
        "xml_file": "word/footnotes.xml",
        "container_tag": "w:footnote",
        "marker_tag": "w:footnoteRef",
        "ir_cls": Footnote,
    },
    "endnote": {
        "xml_file": "word/endnotes.xml",
        "container_tag": "w:endnote",
        "marker_tag": "w:endnoteRef",
        "ir_cls": Endnote,
    },
}


def _load_notes(
    path: Path | bytes,
    rels: dict,
    numbering: dict,
    *,
    note_kind: str,
) -> tuple[dict, list[dict]]:
    """Parse ``word/{note_kind}s.xml`` into a dict of ``Footnote`` or
    ``Endnote`` objects keyed by the internal integer ID."""
    cfg = _NOTE_CONFIG[note_kind]
    notes: dict = {}
    diagnostics: list[dict] = []
    try:
        archive = BytesIO(path) if isinstance(path, bytes) else path
        with zipfile.ZipFile(archive) as z:
            if cfg["xml_file"] not in z.namelist():
                return notes, diagnostics
            data = z.read(cfg["xml_file"])
    except (zipfile.BadZipFile, KeyError):
        diagnostics.append(
            _invalid_note_part_spec(note_kind, cfg["xml_file"], "unreadable")
        )
        return notes, diagnostics

    try:
        root = etree.fromstring(data)
    except etree.XMLSyntaxError:
        diagnostics.append(
            _invalid_note_part_spec(note_kind, cfg["xml_file"], "invalid-xml")
        )
        return notes, diagnostics

    for el in root.findall(_q(cfg["container_tag"])):
        fn_type = el.get(_q("w:type"))
        if fn_type in ("separator", "continuationSeparator", "continuationNotice"):
            diagnostics.append(
                {
                    "code": f"docx.{note_kind}-separator-omitted",
                    "severity": "info",
                    "disposition": "omitted",
                    "loss_kind": "presentation",
                    "location": DiagnosticLocation(
                        kind="ooxml",
                        part=cfg["xml_file"],
                        xpath=root.getroottree().getpath(el),
                    ),
                    "message": (
                        f"A generated DOCX {note_kind} separator was omitted from "
                        "canonical text."
                    ),
                    "details": {"note_type": fn_type},
                }
            )
            continue
        internal_id = el.get(_q("w:id"))
        if not internal_id:
            diagnostics.append(
                {
                    "code": f"docx.{note_kind}-id-missing",
                    "severity": "error",
                    "disposition": "refused",
                    "loss_kind": "text",
                    "location": DiagnosticLocation(
                        kind="ooxml",
                        part=cfg["xml_file"],
                        xpath=root.getroottree().getpath(el),
                    ),
                    "message": f"A DOCX {note_kind} body has no durable note identity.",
                    "details": {},
                }
            )
            continue
        if internal_id in notes:
            diagnostics.append(
                {
                    "code": f"docx.{note_kind}-id-duplicate",
                    "severity": "error",
                    "disposition": "refused",
                    "loss_kind": "text",
                    "location": DiagnosticLocation(
                        kind="ooxml",
                        part=cfg["xml_file"],
                        xpath=root.getroottree().getpath(el),
                    ),
                    "message": (
                        f"A duplicate DOCX {note_kind} identity would overwrite "
                        "note text, so canonical recovery was refused."
                    ),
                    "details": {"note_id": internal_id},
                }
            )
            continue
        diagnostics.extend(
            _loss_diagnostic_specs(
                el,
                rels,
                part_name=cfg["xml_file"],
                include_page_provenance=False,
            )
        )
        marker = el.find(f".//{_q(cfg['marker_tag'])}")
        if marker is not None:
            diagnostics.append(
                {
                    "code": f"docx.{note_kind}-marker-normalized",
                    "severity": "info",
                    "disposition": "normalized",
                    "loss_kind": "metadata",
                    "location": DiagnosticLocation(
                        kind="ooxml",
                        part=cfg["xml_file"],
                        xpath=root.getroottree().getpath(marker),
                    ),
                    "message": (
                        f"The generated DOCX {note_kind} marker was represented by "
                        "the canonical note identity."
                    ),
                    "details": {"note_id": internal_id},
                }
            )
        # Clean this subtree of revision marks before walking
        _clean_revisions(el)
        # Strip the auto-numbering marker run at the start
        _strip_note_ref_marker(el, cfg["marker_tag"])

        children: list = []
        _walk_body(el, children, rels, numbering)
        notes[internal_id] = cfg["ir_cls"](id=internal_id, children=children)
    return notes, diagnostics


def _invalid_note_part_spec(note_kind: str, part: str, reason: str) -> dict:
    return {
        "code": f"docx.{note_kind}-part-invalid",
        "severity": "error",
        "disposition": "refused",
        "loss_kind": "text",
        "location": DiagnosticLocation(kind="ooxml", part=part, xpath="/"),
        "message": f"The DOCX {note_kind} part could not be parsed safely.",
        "details": {"reason": reason},
    }


def _unresolved_note_reference_specs(
    body: etree._Element,
    *,
    footnote_ids: set[str],
    endnote_ids: set[str],
) -> list[dict]:
    specs: list[dict] = []
    tree = body.getroottree()
    for note_kind, tag, known in (
        ("footnote", "w:footnoteReference", footnote_ids),
        ("endnote", "w:endnoteReference", endnote_ids),
    ):
        for element in body.iter(_q(tag)):
            note_id = element.get(_q("w:id")) or ""
            if note_id in known:
                continue
            specs.append(
                {
                    "code": f"docx.{note_kind}-reference-unresolved",
                    "severity": "error",
                    "disposition": "refused",
                    "loss_kind": "text",
                    "location": DiagnosticLocation(
                        kind="ooxml",
                        part="word/document.xml",
                        xpath=tree.getpath(element),
                    ),
                    "message": (
                        f"A DOCX {note_kind} reference has no recoverable note body."
                    ),
                    "details": {"note_id": note_id},
                }
            )
    return specs


def _strip_note_ref_marker(el: etree._Element, marker_tag: str) -> None:
    """Remove the auto-numbered marker run from the start of a footnote or
    endnote body, along with any immediately-following whitespace-only run
    that Word inserts as a cosmetic spacer. The marker carries no content —
    the note's identity already lives in the Footnote/Endnote id."""
    # Collect marker-bearing runs first so we can inspect their siblings.
    marker_runs: list[etree._Element] = []
    for run in list(el.iter(_q("w:r"))):
        if run.find(_q(marker_tag)) is not None:
            marker_runs.append(run)

    for run in marker_runs:
        parent = run.getparent()
        if parent is None:
            continue
        for marker in list(run.iter(_q(marker_tag))):
            marker_parent = marker.getparent()
            if marker_parent is not None:
                marker_parent.remove(marker)

        # Keep a marker-bearing run when it also contains recoverable payload.
        # Only an emptied marker-only run can justify removing Word's generated
        # cosmetic spacer after it.
        if _run_has_canonical_payload(run):
            continue
        idx = list(parent).index(run)
        next_el = parent[idx + 1] if idx + 1 < len(parent) else None
        if next_el is not None and _is_whitespace_only_run(next_el):
            parent.remove(next_el)
        parent.remove(run)


def _run_has_canonical_payload(run: etree._Element) -> bool:
    for child in run:
        if child.tag == _q("w:t") and (child.text or ""):
            return True
        if child.tag in {
            _q("w:tab"),
            _q("w:br"),
            _q("w:cr"),
            _q("w:noBreakHyphen"),
            _q("w:softHyphen"),
            _q("w:drawing"),
            _q("w:footnoteReference"),
            _q("w:endnoteReference"),
        }:
            return True
    return False


def _is_whitespace_only_run(element: etree._Element) -> bool:
    if element.tag != _q("w:r"):
        return False
    text_parts: list[str] = []
    for child in element:
        if child.tag == _q("w:rPr"):
            continue
        if child.tag != _q("w:t"):
            return False
        text_parts.append(child.text or "")
    joined = "".join(text_parts)
    return bool(joined) and not joined.strip()


# ---------------------------------------------------------------------------
# Pre-pass: strip non-semantic scaffolding
# ---------------------------------------------------------------------------

_STRIP_TAGS = {
    _q("w:commentRangeStart"),
    _q("w:commentRangeEnd"),
    _q("w:commentReference"),
    _q("w:bookmarkStart"),
    _q("w:bookmarkEnd"),
    _q("w:proofErr"),
    _q("w:lastRenderedPageBreak"),
}


def _loss_diagnostic_specs(
    body: etree._Element,
    rels: dict[str, str],
    *,
    part_name: str = "word/document.xml",
    include_page_provenance: bool = True,
) -> list[dict]:
    """Inventory known DOCX degradations before the parser mutates OOXML."""
    specs: list[dict] = []
    if include_page_provenance:
        specs.append(
            {
                "code": "docx.page-provenance-unavailable",
                "severity": "info",
                "disposition": "omitted",
                "loss_kind": "metadata",
                "location": DiagnosticLocation(
                    kind="ooxml",
                    part="word/document.xml",
                    xpath="/w:document/w:body",
                ),
                "message": "DOCX layout is unpaginated during canonical extraction; page numbers are unavailable.",
                "details": {},
            }
        )
    tree = body.getroottree()

    seen: set[tuple[str, str]] = set()

    def add(
        element: etree._Element,
        code: str,
        severity: str,
        disposition: str,
        loss_kind: str,
        message: str,
        *,
        details: dict | None = None,
    ) -> None:
        xpath = tree.getpath(element)
        key = (code, xpath)
        if key in seen:
            return
        seen.add(key)
        specs.append(
            {
                "code": code,
                "severity": severity,
                "disposition": disposition,
                "loss_kind": loss_kind,
                "location": DiagnosticLocation(
                    kind="ooxml",
                    part=part_name,
                    xpath=xpath,
                ),
                "message": message,
                "details": {
                    "element": etree.QName(element.tag).localname,
                    **(details or {}),
                },
            }
        )

    for element in list(body.iter()):
        local = etree.QName(element.tag).localname
        if local.startswith("comment"):
            add(
                element,
                "docx.comment-omitted",
                "warning",
                "omitted",
                "text",
                "A DOCX comment marker was omitted from the canonical document.",
            )
        elif local.startswith("bookmark"):
            add(
                element,
                "docx.bookmark-omitted",
                "info",
                "omitted",
                "metadata",
                "A DOCX bookmark marker was omitted from the canonical document.",
            )
        elif element.tag == _q("w:del") or element.tag == _q("w:delText"):
            add(
                element,
                "docx.revision-deletion-omitted",
                "warning",
                "omitted",
                "text",
                "Rejected tracked-change text was omitted in favor of the accepted document state.",
            )
        elif element.tag == _q("w:ins"):
            add(
                element,
                "docx.revision-insertion-normalized",
                "info",
                "normalized",
                "metadata",
                "Accepted tracked-change text was retained without revision markup.",
            )
        elif element.tag == _q("w:lastRenderedPageBreak"):
            add(
                element,
                "docx.page-break-omitted",
                "info",
                "omitted",
                "metadata",
                "A rendered page-break marker was omitted from the unpaginated canonical document.",
            )
        elif element.tag == _q("w:proofErr"):
            add(
                element,
                "docx.proofing-marker-omitted",
                "info",
                "omitted",
                "metadata",
                "A Word proofing-range marker was omitted from the canonical document.",
            )
        elif element.tag == _q("w:br") and element.get(_q("w:type")) == "page":
            add(
                element,
                "docx.page-break-omitted",
                "info",
                "omitted",
                "metadata",
                "A page break was omitted from the unpaginated canonical document.",
            )
    for paragraph in body.iter(_q("w:p")):
        if _paragraph_is_toc_field(paragraph):
            add(
                paragraph,
                "docx.toc-cache-omitted",
                "info",
                "omitted",
                "structure",
                "A generated table-of-contents cache was omitted from the canonical document.",
            )

    _inventory_body_boundaries(body, add)
    _inventory_table_boundaries(body, add)
    for paragraph in body.iter(_q("w:p")):
        _inventory_paragraph_boundary(paragraph, rels, add)
    for run in body.iter(_q("w:r")):
        _inventory_run_boundary(run, rels, add)
    return specs


def _inventory_table_boundaries(body: etree._Element, add) -> None:
    """Refuse table semantics the current flat-cell IR cannot preserve."""
    for table in body.iter(_q("w:tbl")):
        if any(ancestor.tag == _q("w:tbl") for ancestor in table.iterancestors()):
            contains_text = _element_has_text_payload(table)
            add(
                table,
                "docx.nested-table-unsupported",
                "error" if contains_text else "warning",
                "refused" if contains_text else "omitted",
                "text" if contains_text else "structure",
                (
                    "A nested DOCX table contains text that the flat canonical "
                    "table model cannot preserve."
                    if contains_text
                    else "An empty nested DOCX table was omitted."
                ),
                details={"contains_text": contains_text},
            )
        rows = table.findall(_q("w:tr"))
        for row_index, row in enumerate(rows):
            if row_index == 0 or not _table_row_is_header(row):
                continue
            add(
                row,
                "docx.table-header-row-unsupported",
                "error",
                "refused",
                "structure",
                (
                    "Only the first DOCX table row can map to the canonical "
                    "single-header-row model."
                ),
                details={"row_index": row_index},
            )
    for merge in body.iter():
        if merge.tag not in {_q("w:gridSpan"), _q("w:vMerge")}:
            continue
        if merge.tag == _q("w:gridSpan") and merge.get(_q("w:val")) == "1":
            continue
        add(
            merge,
            "docx.table-cell-merge-unsupported",
            "error",
            "refused",
            "structure",
            (
                "Merged DOCX table-cell semantics cannot be represented "
                "losslessly in the canonical table model."
            ),
            details={
                "merge_kind": etree.QName(merge.tag).localname,
                "value": merge.get(_q("w:val")) or "",
            },
        )


def _element_has_text_payload(element: etree._Element) -> bool:
    """Return whether an unconsumed element appears to carry textual data."""
    for descendant in element.iter():
        local = etree.QName(descendant.tag).localname
        if local in {"t", "delText", "instrText"} and (descendant.text or ""):
            return True
    return False


def _unsupported_details(element: etree._Element) -> dict:
    name = etree.QName(element.tag)
    return {
        "namespace": name.namespace or "",
        "contains_text": _element_has_text_payload(element),
    }


def _wrapper_content(element: etree._Element) -> etree._Element | None:
    """Return the semantic content container for a transparent OOXML wrapper."""
    if element.tag == _q("w:sdt"):
        return element.find(_q("w:sdtContent"))
    return element


def _inventory_body_boundaries(body: etree._Element, add) -> None:
    """Report every direct body-level decision, including nested wrappers."""

    def inspect(container: etree._Element) -> None:
        for child in container:
            if child.tag in {_q("w:p"), _q("w:tbl")}:
                continue
            if child.tag == _q("w:sectPr"):
                # Section layout is represented by the mandatory page-
                # provenance diagnostic. Header/footer references need their
                # own text-loss diagnostic.
                for reference in child:
                    if reference.tag in {
                        _q("w:headerReference"),
                        _q("w:footerReference"),
                    }:
                        add(
                            reference,
                            "docx.header-footer-omitted",
                            "warning",
                            "omitted",
                            "text",
                            "A referenced DOCX header or footer was not included in canonical body text.",
                            details={
                                "relationship_id": reference.get(_q("r:id")) or ""
                            },
                        )
                continue
            if child.tag in _BODY_WRAPPER_TAGS:
                add(
                    child,
                    "docx.body-wrapper-normalized",
                    "info",
                    "normalized",
                    "structure",
                    "A body-level OOXML wrapper was removed while its supported block content was retained.",
                )
                content = _wrapper_content(child)
                if content is not None:
                    inspect(content)
                continue
            if child.tag in _STRIP_TAGS or child.tag in {
                _q("w:del"),
                _q("w:delText"),
                _q("w:ins"),
            }:
                continue
            loss_kind = (
                "text"
                if (child.tag == _q("w:altChunk") or _element_has_text_payload(child))
                else "structure"
            )
            add(
                child,
                "docx.unsupported-body-element",
                "warning",
                "omitted",
                loss_kind,
                "An unsupported body-level OOXML element was omitted from the canonical document.",
                details=_unsupported_details(child),
            )

    inspect(body)


def _inventory_paragraph_boundary(
    paragraph: etree._Element,
    rels: dict[str, str],
    add,
) -> None:
    """Inventory paragraph content that the inline walker consumes or omits."""
    is_toc = _paragraph_is_toc_field(paragraph)

    def inspect(container: etree._Element) -> None:
        for child in container:
            if child.tag in {_q("w:r"), _q("w:pPr")}:
                continue
            if child.tag == _q("w:hyperlink"):
                rel_id = child.get(_q("r:id")) or ""
                anchor = child.get(_q("w:anchor")) or ""
                if not anchor and (not rel_id or rel_id not in rels):
                    add(
                        child,
                        "docx.hyperlink-target-unresolved",
                        "warning",
                        "omitted",
                        "metadata",
                        "Hyperlink text was retained but its target could not be resolved.",
                        details={"relationship_id": rel_id},
                    )
                inspect(child)
                continue
            if child.tag in _PARAGRAPH_WRAPPER_TAGS:
                code = (
                    "docx.simple-field-normalized"
                    if child.tag == _q("w:fldSimple")
                    else "docx.paragraph-wrapper-normalized"
                )
                add(
                    child,
                    code,
                    "info",
                    "normalized",
                    "structure",
                    "A paragraph-level OOXML wrapper was removed while its supported inline content was retained.",
                )
                content = _wrapper_content(child)
                if content is not None:
                    inspect(content)
                continue
            if child.tag in _STRIP_TAGS or child.tag in {
                _q("w:del"),
                _q("w:delText"),
                _q("w:ins"),
            }:
                continue
            # TOC field markers and instructions are accounted for by the
            # paragraph-level TOC diagnostic.
            if is_toc and child.tag in {_q("w:fldChar"), _q("w:instrText")}:
                continue
            add(
                child,
                "docx.unsupported-paragraph-element",
                "warning",
                "omitted",
                "text" if _element_has_text_payload(child) else "structure",
                "An unsupported paragraph-level OOXML element was omitted from the canonical document.",
                details=_unsupported_details(child),
            )

    inspect(paragraph)

    ppr = paragraph.find(_q("w:pPr"))
    if ppr is not None:
        handled = {_q("w:pStyle"), _q("w:numPr"), _q("w:pBdr")}
        for prop in ppr:
            if prop.tag not in handled:
                add(
                    prop,
                    "docx.paragraph-presentation-omitted",
                    "info",
                    "omitted",
                    "presentation",
                    "A paragraph presentation property was not represented in canonical IR.",
                    details=_unsupported_details(prop),
                )


def _inventory_run_boundary(
    run: etree._Element,
    rels: dict[str, str],
    add,
) -> None:
    """Inventory run children and presentation properties."""
    paragraph = next(
        (ancestor for ancestor in run.iterancestors() if ancestor.tag == _q("w:p")),
        None,
    )
    is_toc = paragraph is not None and _paragraph_is_toc_field(paragraph)
    handled = {
        _q("w:rPr"),
        _q("w:t"),
        _q("w:tab"),
        _q("w:br"),
        _q("w:cr"),
        _q("w:noBreakHyphen"),
        _q("w:softHyphen"),
        _q("w:drawing"),
        _q("w:footnoteReference"),
        _q("w:endnoteReference"),
        _q("w:footnoteRef"),
        _q("w:endnoteRef"),
    }
    for child in run:
        if child.tag in handled:
            if child.tag == _q("w:drawing"):
                blip = child.find(f".//{{{A_NS}}}blip")
                rel_id = (
                    ""
                    if blip is None
                    else (
                        blip.get(f"{{{R_NS}}}embed")
                        or blip.get(f"{{{R_NS}}}link")
                        or ""
                    )
                )
                if blip is None or not rel_id or rel_id not in rels:
                    add(
                        child,
                        "docx.drawing-omitted",
                        "warning",
                        "omitted",
                        "structure",
                        "A drawing without a resolvable image relationship was omitted.",
                        details={"relationship_id": rel_id},
                    )
            continue
        if child.tag == _q("w:sym"):
            add(
                child,
                "docx.symbol-omitted",
                "warning",
                "omitted",
                "text",
                "A font-mapped Word symbol could not be converted safely and was omitted.",
                details={
                    "font": child.get(_q("w:font")) or "",
                    "char": child.get(_q("w:char")) or "",
                },
            )
            continue
        if child.tag == _q("w:instrText"):
            if not is_toc:
                add(
                    child,
                    "docx.field-instruction-omitted",
                    "info",
                    "omitted",
                    "metadata",
                    "A Word field instruction was omitted while visible field-result text was retained.",
                    details={"instruction": child.text or ""},
                )
            continue
        if child.tag == _q("w:fldChar"):
            if not is_toc:
                add(
                    child,
                    "docx.field-marker-omitted",
                    "info",
                    "omitted",
                    "metadata",
                    "A Word field boundary marker was omitted from canonical text.",
                    details={"field_char_type": child.get(_q("w:fldCharType")) or ""},
                )
            continue
        if child.tag in _STRIP_TAGS or child.tag in {_q("w:delText")}:
            continue
        add(
            child,
            "docx.unsupported-run-element",
            "warning",
            "omitted",
            "text" if _element_has_text_payload(child) else "structure",
            "An unsupported run-level OOXML element was omitted from the canonical document.",
            details=_unsupported_details(child),
        )

    rpr = run.find(_q("w:rPr"))
    if rpr is not None:
        semantic = {
            _q("w:b"),
            _q("w:i"),
            _q("w:strike"),
            _q("w:dstrike"),
            _q("w:vertAlign"),
            _q("w:rStyle"),
            _q("w:rFonts"),
        }
        for prop in rpr:
            if prop.tag not in semantic:
                add(
                    prop,
                    "docx.run-presentation-omitted",
                    "info",
                    "omitted",
                    "presentation",
                    "A run presentation property was not represented in canonical IR.",
                    details=_unsupported_details(prop),
                )


# w:ins wraps inserted content — accept by unwrapping
# w:del wraps deleted content — drop entirely


def _clean_revisions(root: etree._Element) -> None:
    # Drop elements we never want
    for el in list(root.iter()):
        if el.tag in _STRIP_TAGS:
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    # Drop w:del (rejected deletions -> final text)
    for el in list(root.iter(_q("w:del"))):
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)

    # w:delText inside accepted content -> also drop
    for el in list(root.iter(_q("w:delText"))):
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)

    # Unwrap w:ins (accepted insertions)
    for el in list(root.iter(_q("w:ins"))):
        parent = el.getparent()
        if parent is None:
            continue
        idx = list(parent).index(el)
        for child in list(el):
            parent.insert(idx, child)
            idx += 1
        parent.remove(el)


# ---------------------------------------------------------------------------
# Numbering (list detection)
# ---------------------------------------------------------------------------


def _load_numbering(docx) -> dict:
    """Return a map of numId -> {level_index: 'bullet' | 'decimal'}."""
    numbering: dict = {}
    try:
        num_part = docx.part.numbering_part
    except Exception:
        return numbering
    if num_part is None:
        return numbering

    root = num_part.element  # the w:numbering element

    # abstractNumId -> {ilvl: fmt}
    abstract: dict[str, dict[int, str]] = {}
    for anum in root.findall(_q("w:abstractNum")):
        aid = anum.get(_q("w:abstractNumId"))
        levels: dict[int, str] = {}
        for lvl in anum.findall(_q("w:lvl")):
            ilvl = int(lvl.get(_q("w:ilvl")) or "0")
            fmt_el = lvl.find(_q("w:numFmt"))
            fmt = (
                fmt_el.get(_q("w:val")) if fmt_el is not None else "bullet"
            ) or "bullet"
            levels[ilvl] = fmt
        abstract[aid] = levels

    # num -> abstractNumId
    for num in root.findall(_q("w:num")):
        nid = num.get(_q("w:numId"))
        aref = num.find(_q("w:abstractNumId"))
        aid = aref.get(_q("w:val")) if aref is not None else None
        if aid is not None and aid in abstract:
            numbering[nid] = abstract[aid]

    return numbering


# ---------------------------------------------------------------------------
# Body walker
# ---------------------------------------------------------------------------


def _walk_body(
    body: etree._Element,
    out: list,
    rels: dict,
    numbering: dict,
) -> None:
    # Collect ordered (paragraph | table) children. Consecutive list
    # paragraphs get grouped into ListBlock blocks.
    i = 0
    children = list(_iter_body_blocks(body))
    n = len(children)

    while i < n:
        el = children[i]
        if el.tag == _q("w:tbl"):
            out.append(_parse_table(el, rels))
            i += 1
            continue

        # Paragraph
        info = _paragraph_info(el, numbering)

        # Coalesce a run of consecutive Source Code paragraphs into one
        # CodeBlock.
        if info["style"] and style_map.is_code_block(info["style"]):
            code_lines: list[str] = []
            j = i
            while j < n:
                cel = children[j]
                if cel.tag != _q("w:p"):
                    break
                cinfo = _paragraph_info(cel, numbering)
                if not (cinfo["style"] and style_map.is_code_block(cinfo["style"])):
                    break
                code_lines.append(_paragraph_plain_text(cel))
                j += 1
            out.append(CodeBlock(text="\n".join(code_lines), language=None))
            i = j
            continue

        if info["list_num_id"] is not None:
            # Collect run of list paragraphs sharing the same numId
            j = i
            items_raw: list[tuple[int, etree._Element, dict]] = []
            while j < n:
                cel = children[j]
                if cel.tag != _q("w:p"):
                    break
                cinfo = _paragraph_info(cel, numbering)
                if cinfo["list_num_id"] != info["list_num_id"]:
                    break
                items_raw.append((cinfo["list_level"], cel, cinfo))
                j += 1
            out.append(_build_list(items_raw, info["list_kind"], rels))
            i = j
            continue

        block = _paragraph_to_block(el, info, rels)
        if isinstance(block, Blockquote):
            # Coalesce a run of consecutive blockquote paragraphs into one
            # Blockquote. Word stores a multi-paragraph block quote as several
            # consecutive Quote-styled paragraphs; without this each would
            # become its own separate single-paragraph Blockquote.
            j = i + 1
            while j < n:
                cel = children[j]
                if cel.tag != _q("w:p"):
                    break
                cinfo = _paragraph_info(cel, numbering)
                nxt = _paragraph_to_block(cel, cinfo, rels)
                if not isinstance(nxt, Blockquote):
                    break
                block.children.extend(nxt.children)
                j += 1
            out.append(block)
            i = j
            continue
        if block is not None:
            out.append(block)
        i += 1


def _iter_body_blocks(container: etree._Element):
    """Yield supported blocks in order through transparent body wrappers."""
    for child in container:
        if child.tag in {_q("w:p"), _q("w:tbl")}:
            yield child
        elif child.tag in _BODY_WRAPPER_TAGS:
            content = _wrapper_content(child)
            if content is not None:
                yield from _iter_body_blocks(content)


# ---------------------------------------------------------------------------
# Paragraph inspection
# ---------------------------------------------------------------------------


def _paragraph_info(p: etree._Element, numbering: dict) -> dict:
    pPr = p.find(_q("w:pPr"))
    style_name: str | None = None
    num_id: str | None = None
    ilvl = 0
    list_kind = "bullet"
    has_hr_border = False

    if pPr is not None:
        pStyle = pPr.find(_q("w:pStyle"))
        if pStyle is not None:
            style_name = pStyle.get(_q("w:val"))
        numPr = pPr.find(_q("w:numPr"))
        if numPr is not None:
            nid_el = numPr.find(_q("w:numId"))
            ilvl_el = numPr.find(_q("w:ilvl"))
            if nid_el is not None:
                num_id = nid_el.get(_q("w:val"))
            if ilvl_el is not None:
                try:
                    ilvl = int(ilvl_el.get(_q("w:val")) or "0")
                except ValueError:
                    ilvl = 0
            if num_id and num_id in numbering:
                fmt = numbering[num_id].get(ilvl, "bullet")
                list_kind = "ordered" if fmt != "bullet" else "bullet"

        # Fallback: detect list items by style name alone, even without numPr.
        # python-docx writes 'List Bullet' / 'List Number' paragraphs without
        # auto-attaching a numPr unless the template defines one; we still
        # want to recognize them as list items.
        if num_id is None and style_name is not None:
            sn = style_name
            if (
                "ListBullet" in sn
                or sn == "List Bullet"
                or "ListParagraph" in sn
                or sn == "List Paragraph"
            ):
                num_id = "__style:bullet"
                list_kind = "bullet"
            elif "ListNumber" in sn or sn == "List Number":
                num_id = "__style:number"
                list_kind = "ordered"

        # When we synthesized a numId from style, also use left indent as the
        # level signal.
        if num_id and num_id.startswith("__style:"):
            ind = pPr.find(_q("w:ind"))
            if ind is not None:
                left = ind.get(_q("w:left")) or ind.get(_q("w:start"))
                if left:
                    try:
                        # Twips: 360 per 0.25"; 18pt ~= 360 twips
                        twips = int(left)
                        ilvl = max(0, round(twips / 360))
                    except ValueError:
                        pass
        pBdr = pPr.find(_q("w:pBdr"))
        if pBdr is not None:
            bottom = pBdr.find(_q("w:bottom"))
            if bottom is not None and not _paragraph_has_text(p):
                has_hr_border = True

    return {
        "style": style_name,
        "list_num_id": num_id,
        "list_level": ilvl,
        "list_kind": list_kind,
        "is_hr": has_hr_border,
    }


def _paragraph_has_text(p: etree._Element) -> bool:
    for t in p.iter(_q("w:t")):
        if (t.text or "").strip():
            return True
    return False


def _paragraph_to_block(
    p: etree._Element,
    info: dict,
    rels: dict,
):
    style = info["style"] or "Normal"

    # A Word TOC field's visible text is a cached snapshot that Word
    # regenerates on open; the canonical IR has no TOC block, so the
    # paragraph is dropped.
    if _paragraph_is_toc_field(p):
        return None

    if info["is_hr"]:
        return HorizontalRule()

    level = style_map.heading_level(style)
    if level is not None:
        return Heading(level=level, children=_paragraph_inlines(p, rels))

    if style_map.is_code_block(style):
        text = _paragraph_plain_text(p)
        return CodeBlock(text=text, language=None)

    if style_map.is_blockquote(style):
        return Blockquote(children=[Paragraph(children=_paragraph_inlines(p, rels))])

    # Plain paragraph. If it's a standalone image or a standalone math run,
    # promote to the block-level form.
    inlines = _paragraph_inlines(p, rels)
    if not inlines:
        return None
    if len(inlines) == 1 and isinstance(inlines[0], Image):
        return inlines[0]
    if len(inlines) == 1 and isinstance(inlines[0], Math):
        # Inline math that's alone in its own paragraph = display math.
        return Math(source=inlines[0].source, display=True)
    return Paragraph(children=inlines)


def _paragraph_is_toc_field(p: etree._Element) -> bool:
    """A paragraph hosts a TOC field if it contains a ``<w:fldChar
    w:fldCharType="begin"/>`` and a subsequent ``<w:instrText>`` whose
    content begins with ``TOC`` (after optional whitespace). Word also
    nests TOC fields inside hyperlinks for each entry, but the outer
    shell always has the TOC instruction."""
    has_begin = False
    for el in p.iter():
        if el.tag == _q("w:fldChar"):
            if el.get(_q("w:fldCharType")) == "begin":
                has_begin = True
        elif el.tag == _q("w:instrText"):
            text = (el.text or "").lstrip()
            if text.startswith("TOC") and has_begin:
                return True
    return False


def _paragraph_plain_text(p: etree._Element) -> str:
    parts: list[str] = []

    def append_run(run: etree._Element) -> None:
        for child in run:
            if child.tag == _q("w:t"):
                parts.append(child.text or "")
            elif child.tag == _q("w:tab"):
                parts.append("\t")
            elif child.tag == _q("w:br"):
                if child.get(_q("w:type")) != "page":
                    parts.append("\n")
            elif child.tag == _q("w:cr"):
                parts.append("\n")
            elif child.tag == _q("w:noBreakHyphen"):
                parts.append("\N{NON-BREAKING HYPHEN}")
            elif child.tag == _q("w:softHyphen"):
                parts.append("\N{SOFT HYPHEN}")

    def walk(container: etree._Element) -> None:
        for child in container:
            if child.tag == _q("w:r"):
                append_run(child)
            elif child.tag == _q("w:hyperlink") or child.tag in _PARAGRAPH_WRAPPER_TAGS:
                content = _wrapper_content(child)
                if content is not None:
                    walk(content)

    walk(p)
    return "".join(parts)


# ---------------------------------------------------------------------------
# List building
# ---------------------------------------------------------------------------


def _build_list(
    items_raw: list,
    kind: str,
    rels: dict,
) -> ListBlock:
    """Given a flat list of (level, paragraph_elem, info) tuples sharing a
    numId, construct a nested ListBlock/ListItem tree.
    """
    ordered = kind == "ordered"
    root = ListBlock(ordered=ordered, items=[])
    stack: list[tuple[int, ListBlock]] = [(0, root)]

    for level, p_el, info in items_raw:
        while stack and stack[-1][0] > level:
            stack.pop()
        if not stack:
            stack = [(0, root)]

        parent_level, parent_list = stack[-1]

        if parent_level < level:
            if not parent_list.items:
                parent_list.items.append(ListItem(children=[]))
            host_item = parent_list.items[-1]
            new_list = ListBlock(ordered=ordered, items=[])
            host_item.children.append(new_list)
            stack.append((level, new_list))
            parent_list = new_list

        inlines = _paragraph_inlines(p_el, rels)
        checked = _detect_and_strip_docx_task_marker(inlines)
        para = Paragraph(children=inlines)
        parent_list.items.append(ListItem(children=[para], checked=checked))

    return root


_TASK_BOX_UNCHECKED = "☐"
_TASK_BOX_CHECKED = "☒"
_TASK_BOX_CHECKED_ALT = "☑"  # alternative checked glyph


def _detect_and_strip_docx_task_marker(inlines: list) -> bool | None:
    """Detect a GFM task-list checkbox at the start of a DOCX list item.

    We look for the Unicode ballot-box characters commonly used to render
    checkboxes (☐ / ☒), or the ☑ alternative. If present, strip the marker
    from the first Text node and return the check state."""
    if not inlines or not isinstance(inlines[0], Text):
        return None
    txt = inlines[0].value
    if not txt:
        return None
    first = txt[0]
    if first == _TASK_BOX_UNCHECKED:
        stripped = txt[1:].lstrip(" ")
        inlines[0] = Text(value=stripped)
        return False
    if first in (_TASK_BOX_CHECKED, _TASK_BOX_CHECKED_ALT):
        stripped = txt[1:].lstrip(" ")
        inlines[0] = Text(value=stripped)
        return True
    return None


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------


def _parse_table(
    tbl: etree._Element,
    rels: dict,
) -> Table:
    rows_el = tbl.findall(_q("w:tr"))
    if not rows_el:
        return Table()

    header_cells: list[Cell] = []
    body_rows: list[list[Cell]] = []
    column_alignments: list = []

    for idx, tr in enumerate(rows_el):
        cells = []
        cell_alignments = []
        for tc in tr.findall(_q("w:tc")):
            cell_inlines: list[Inline] = []
            paragraphs = tc.findall(_q("w:p"))
            for p in paragraphs:
                para_inlines = _paragraph_inlines(p, rels)
                if cell_inlines and para_inlines:
                    cell_inlines.append(Text(value=" "))
                cell_inlines.extend(para_inlines)
            cells.append(Cell(children=cell_inlines))
            # Column alignment: read the first paragraph's w:pPr/w:jc
            # value, if any. Header row drives per-column alignment.
            align = None
            if paragraphs:
                pPr = paragraphs[0].find(_q("w:pPr"))
                if pPr is not None:
                    jc = pPr.find(_q("w:jc"))
                    if jc is not None:
                        v = jc.get(_q("w:val"))
                        if v in ("left", "center", "right"):
                            align = v
            cell_alignments.append(align)
        if idx == 0:
            column_alignments = cell_alignments
        if idx == 0 and _table_row_is_header(tr):
            header_cells = cells
        else:
            body_rows.append(cells)

    first_row = header_cells or (body_rows[0] if body_rows else [])
    n_cols = len(first_row)
    alignments = column_alignments + [None] * (n_cols - len(column_alignments))
    return Table(
        headers=header_cells,
        rows=body_rows,
        alignments=alignments[:n_cols],
    )


def _table_row_is_header(row: etree._Element) -> bool:
    row_properties = row.find(_q("w:trPr"))
    if row_properties is None:
        return False
    marker = row_properties.find(_q("w:tblHeader"))
    return marker is not None and not _val_false(marker)


# ---------------------------------------------------------------------------
# Paragraph inlines (runs, hyperlinks, images, breaks)
# ---------------------------------------------------------------------------


def _paragraph_inlines(
    p: etree._Element,
    rels: dict,
) -> list[Inline]:
    return _coalesce_text(_inline_container_inlines(p, rels))


def _inline_container_inlines(
    container: etree._Element,
    rels: dict,
) -> list[Inline]:
    """Recover supported inline content through transparent OOXML wrappers."""
    out: list[Inline] = []
    for child in container:
        if child.tag == _q("w:r"):
            out.extend(_run_inlines(child, rels))
        elif child.tag == _q("w:hyperlink"):
            href = rels.get(child.get(_q("r:id")) or "", "")
            if not href:
                anchor = child.get(_q("w:anchor"))
                if anchor:
                    href = f"#{anchor}"
            link_children = _inline_container_inlines(child, rels)
            if link_children:
                out.append(Link(children=_coalesce_text(link_children), href=href))
        elif child.tag in _PARAGRAPH_WRAPPER_TAGS:
            content = _wrapper_content(child)
            if content is not None:
                out.extend(_inline_container_inlines(content, rels))
    return out


def _run_inlines(
    r: etree._Element,
    rels: dict,
) -> list[Inline]:
    rPr = r.find(_q("w:rPr"))
    bold = italic = strike = is_code = False
    vert_align: str | None = None  # "superscript" | "subscript" | None
    is_math = _is_cambria_math_run(rPr)

    # If this run is marked as math, consume it wholesale as a Math node,
    # taking the run's text as the source. ``display`` is False here; the
    # standalone-paragraph detection in _paragraph_to_block promotes it.
    if is_math:
        text_parts = [(t.text or "") for t in r.iter(_q("w:t"))]
        source = "".join(text_parts)
        if source:
            return [Math(source=source, display=False)]
        return []

    if rPr is not None:
        if rPr.find(_q("w:b")) is not None and not _val_false(rPr.find(_q("w:b"))):
            bold = True
        if rPr.find(_q("w:i")) is not None and not _val_false(rPr.find(_q("w:i"))):
            italic = True
        if rPr.find(_q("w:strike")) is not None and not _val_false(
            rPr.find(_q("w:strike"))
        ):
            strike = True
        if rPr.find(_q("w:dstrike")) is not None and not _val_false(
            rPr.find(_q("w:dstrike"))
        ):
            strike = True
        vAlign = rPr.find(_q("w:vertAlign"))
        if vAlign is not None:
            v = vAlign.get(_q("w:val"))
            if v in ("superscript", "subscript"):
                vert_align = v
        rStyle = rPr.find(_q("w:rStyle"))
        if rStyle is not None:
            sval = rStyle.get(_q("w:val")) or ""
            if any(tok in sval for tok in ("Code", "Verbatim", "Mono")):
                is_code = True
        rFonts = rPr.find(_q("w:rFonts"))
        if rFonts is not None:
            fname = (
                rFonts.get(_q("w:ascii"))
                or rFonts.get(_q("w:hAnsi"))
                or rFonts.get(_q("w:cs"))
                or ""
            )
            if any(m in fname for m in ("Mono", "Courier", "Consolas", "Menlo")):
                is_code = True

    # Collect text / break / image / footnote-ref content
    pieces: list[Inline] = []
    for sub in r:
        if sub.tag == _q("w:t"):
            text = sub.text or ""
            if text:
                # Split on Pandoc-style ``[@key]`` / ``[@key, loc]`` citations
                # so they survive as Citation nodes rather than literal text.
                split = _split_citations_in_text(text)
                if split:
                    pieces.extend(split)
                else:
                    pieces.append(Text(value=text))
        elif sub.tag == _q("w:tab"):
            pieces.append(Text(value="\t"))
        elif sub.tag == _q("w:br"):
            if sub.get(_q("w:type")) == "page":
                continue
            pieces.append(LineBreak())
        elif sub.tag == _q("w:cr"):
            pieces.append(LineBreak())
        elif sub.tag == _q("w:noBreakHyphen"):
            pieces.append(Text(value="\N{NON-BREAKING HYPHEN}"))
        elif sub.tag == _q("w:softHyphen"):
            pieces.append(Text(value="\N{SOFT HYPHEN}"))
        elif sub.tag == _q("w:drawing"):
            img = _extract_drawing(sub, rels)
            if img is not None:
                pieces.append(img)
        elif sub.tag == _q("w:footnoteReference"):
            internal = sub.get(_q("w:id"))
            if internal:
                pieces.append(FootnoteRef(id=internal))
        elif sub.tag == _q("w:endnoteReference"):
            internal = sub.get(_q("w:id"))
            if internal:
                pieces.append(EndnoteRef(id=internal))
        # Unsupported or metadata-only run constructs are omitted only after
        # the diagnostic inventory records their exact OOXML location.

    if not pieces:
        return []

    # Apply formatting wrappers outside-in: code > strike > italic > bold
    # (code is terminal — if the run is code, don't also wrap in b/i.)
    if is_code:
        joined = "".join(p.value if isinstance(p, Text) else "" for p in pieces)
        if joined:
            return [Code(value=joined)]
        return []

    result: list[Inline] = pieces
    # Vertical alignment (super/sub) wraps innermost before other emphasis,
    # so bold/italic/strike survive around a sup/sub run.
    if vert_align == "superscript":
        result = [Superscript(children=result)]
    elif vert_align == "subscript":
        result = [Subscript(children=result)]
    if strike:
        result = [Strikethrough(children=result)]
    if italic:
        result = [Italic(children=result)]
    if bold:
        result = [Bold(children=result)]
    return result


def _val_false(el) -> bool:
    if el is None:
        return True
    v = el.get(_q("w:val"))
    return v in ("0", "false", "False")


def _is_cambria_math_run(rPr: etree._Element | None) -> bool:
    """Return True if the run's properties identify it as math content.
    Word renders OMML math runs in Cambria Math (``<w:rFonts
    w:ascii="Cambria Math"/>``); that's the marker we detect."""
    if rPr is None:
        return False
    rFonts = rPr.find(_q("w:rFonts"))
    if rFonts is None:
        return False
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fname = rFonts.get(_q(attr)) or ""
        if "Cambria Math" in fname:
            return True
    return False


def _extract_drawing(drawing: etree._Element, rels: dict) -> Image | None:
    blip = drawing.find(f".//{{{A_NS}}}blip")
    if blip is None:
        return None
    rid = blip.get(f"{{{R_NS}}}embed") or blip.get(f"{{{R_NS}}}link")
    src = rels.get(rid or "", "") if rid else ""
    # Alt text lives in docPr (wp namespace) — find it by localname.
    alt = ""
    for el in drawing.iter():
        if etree.QName(el.tag).localname == "docPr":
            alt = el.get("descr") or el.get("title") or ""
            break
    return Image(alt=alt, src=src, title=None)


_MERGEABLE_WRAPPERS = (Bold, Italic, Strikethrough, Superscript, Subscript)


def _coalesce_text(nodes: list[Inline]) -> list[Inline]:
    """Merge adjacent Text nodes, then adjacent same-type formatting
    wrappers, recursively. Word often fragments a bold phrase into
    multiple `<w:r>` elements that each reproduce the bold property;
    this reassembles them into a single IR node."""
    # First recurse into children of wrapper nodes so inner normalization
    # runs before outer merging.
    normalized: list[Inline] = []
    for n in nodes:
        if isinstance(n, _MERGEABLE_WRAPPERS):
            normalized.append(type(n)(children=_coalesce_text(n.children)))
        elif isinstance(n, Link):
            normalized.append(
                Link(
                    children=_coalesce_text(n.children),
                    href=n.href,
                    title=n.title,
                )
            )
        else:
            normalized.append(n)

    # Now merge adjacents at this level.
    out: list[Inline] = []
    for n in normalized:
        if out and isinstance(n, Text) and isinstance(out[-1], Text):
            out[-1] = Text(value=out[-1].value + n.value)
        elif out and isinstance(n, _MERGEABLE_WRAPPERS) and type(out[-1]) is type(n):
            merged_children = _coalesce_text(out[-1].children + n.children)
            out[-1] = type(n)(children=merged_children)
        else:
            out.append(n)
    return out
