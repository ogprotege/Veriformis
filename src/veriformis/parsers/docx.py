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

Provenance follows the extracted-stream contract: the canonical stream is
built incrementally from the top-level blocks in document order — each
block's ``block_text()`` plus a ``"\\n\\n"`` separator — and every top-level
block carries ``span = Span(pos_before, pos_before + len(block_text))``
plus a sequential ``block_index`` indexing that stream (never the raw
file). ``page`` stays ``None`` (DOCX is unpaginated).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from docx import Document as OpenDocument
from lxml import etree

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
    Span,
    Strikethrough,
    Subscript,
    Superscript,
    Table,
    Text,
    block_text,
)
from veriformis.parsers import docx_styles as style_map
from veriformis.sources import ParseResult, register_source

_CITATION_RE = re.compile(r"\[@([A-Za-z][\w:.\-]*)(?:,\s*([^\]]+))?\]")


def _split_citations_in_text(value: str) -> list[Inline]:
    """Split a plain text string into alternating Text and Citation
    nodes. Text segments without any citation pattern produce a single
    Text node."""
    result: list[Inline] = []
    last = 0
    for m in _CITATION_RE.finditer(value):
        if m.start() > last:
            result.append(Text(value=value[last:m.start()]))
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_docx_file(path: str | Path) -> ParseResult:
    """File entry: parse, register the source, return ParseResult."""
    p = Path(path)
    doc, stream = _parse_docx(p)
    source = register_source(p, "docx", stream)
    doc.source_id = source.id
    return ParseResult(document=doc, source=source)


def _parse_docx(path: Path) -> tuple[Document, str]:
    """Parse a .docx into a Document and its extracted-text stream."""
    docx = OpenDocument(path)
    body = docx.element.body

    # Build a relationship map: rId -> target (for hyperlinks and images)
    rels: dict[str, str] = {}
    part = docx.part
    for rel_id, rel in part.rels.items():
        rels[rel_id] = rel.target_ref

    # Pre-process: strip revision marks, comments, bookmarks, etc.
    _clean_revisions(body)

    # Build numbering info for list detection
    numbering = _load_numbering(docx)

    doc_ir = Document()

    # Parse footnotes and endnotes (from word/{foot,end}notes.xml) before
    # the body walk.
    doc_ir.footnotes = _load_notes(path, rels, numbering, note_kind="footnote")
    doc_ir.endnotes = _load_notes(path, rels, numbering, note_kind="endnote")

    _walk_body(body, doc_ir.children, rels, numbering)
    return doc_ir, _attach_provenance(doc_ir)


def _attach_provenance(doc: Document) -> str:
    """Build the canonical stream from the final top-level blocks, setting
    each block's ``span`` (char offsets into the stream) and sequential
    ``block_index`` as its text is appended. Returns the stream."""
    parts: list[str] = []
    pos = 0
    for index, block in enumerate(doc.children):
        text = block_text(block)
        block.span = Span(pos, pos + len(text))
        block.block_index = index
        parts.append(text)
        parts.append("\n\n")
        pos += len(text) + 2
    if parts:
        parts.pop()  # drop the trailing separator
    return "".join(parts)


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
    path: Path,
    rels: dict,
    numbering: dict,
    *,
    note_kind: str,
) -> dict:
    """Parse ``word/{note_kind}s.xml`` into a dict of ``Footnote`` or
    ``Endnote`` objects keyed by the internal integer ID."""
    cfg = _NOTE_CONFIG[note_kind]
    notes: dict = {}
    try:
        with zipfile.ZipFile(path) as z:
            if cfg["xml_file"] not in z.namelist():
                return notes
            data = z.read(cfg["xml_file"])
    except (zipfile.BadZipFile, KeyError):
        return notes

    try:
        root = etree.fromstring(data)
    except etree.XMLSyntaxError:
        return notes

    for el in root.findall(_q(cfg["container_tag"])):
        fn_type = el.get(_q("w:type"))
        if fn_type in ("separator", "continuationSeparator"):
            continue
        internal_id = el.get(_q("w:id"))
        if not internal_id:
            continue
        # Clean this subtree of revision marks before walking
        _clean_revisions(el)
        # Strip the auto-numbering marker run at the start
        _strip_note_ref_marker(el, cfg["marker_tag"])

        children: list = []
        _walk_body(el, children, rels, numbering)
        notes[internal_id] = cfg["ir_cls"](id=internal_id, children=children)
    return notes


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
        # Drop an immediately-following whitespace-only run if present.
        idx = list(parent).index(run)
        next_el = parent[idx + 1] if idx + 1 < len(parent) else None
        if next_el is not None and next_el.tag == _q("w:r"):
            # Check whether this run's text content is purely whitespace.
            text_parts = [(t.text or "") for t in next_el.iter(_q("w:t"))]
            joined = "".join(text_parts)
            if joined and not joined.strip():
                parent.remove(next_el)
        parent.remove(run)


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
            fmt = (fmt_el.get(_q("w:val")) if fmt_el is not None else "bullet") or "bullet"
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
    children = [c for c in body if c.tag in (_q("w:p"), _q("w:tbl"))]
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
            if "ListBullet" in sn or sn == "List Bullet" or "ListParagraph" in sn or sn == "List Paragraph":
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
    for child in p.iter():
        if child.tag == _q("w:t"):
            parts.append(child.text or "")
        elif child.tag == _q("w:tab"):
            parts.append("\t")
        elif child.tag == _q("w:br"):
            parts.append("\n")
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
    header_alignments: list = []

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
            header_cells = cells
            header_alignments = cell_alignments
        else:
            body_rows.append(cells)

    n_cols = len(header_cells)
    alignments = header_alignments + [None] * (n_cols - len(header_alignments))
    return Table(
        headers=header_cells,
        rows=body_rows,
        alignments=alignments[:n_cols],
    )


# ---------------------------------------------------------------------------
# Paragraph inlines (runs, hyperlinks, images, breaks)
# ---------------------------------------------------------------------------

def _paragraph_inlines(
    p: etree._Element,
    rels: dict,
) -> list[Inline]:
    out: list[Inline] = []
    for child in p:
        if child.tag == _q("w:r"):
            out.extend(_run_inlines(child, rels))
        elif child.tag == _q("w:hyperlink"):
            href = rels.get(child.get(_q("r:id")) or "", "")
            if not href:
                anchor = child.get(_q("w:anchor"))
                if anchor:
                    href = f"#{anchor}"
            link_children: list[Inline] = []
            for sub in child.findall(_q("w:r")):
                link_children.extend(_run_inlines(sub, rels))
            if link_children:
                out.append(Link(children=link_children, href=href))
        # Everything else in a paragraph body (smartTag wrappers, etc.)
        # we ignore — aggressive strip.
    return _coalesce_text(out)


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
        if rPr.find(_q("w:strike")) is not None and not _val_false(rPr.find(_q("w:strike"))):
            strike = True
        if rPr.find(_q("w:dstrike")) is not None and not _val_false(rPr.find(_q("w:dstrike"))):
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
        # w:sym, w:instrText, etc. are ignored

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
            normalized.append(Link(
                children=_coalesce_text(n.children),
                href=n.href,
                title=n.title,
            ))
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
