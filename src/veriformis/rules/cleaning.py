"""Source-scoped, content-addressed cleaning plans.

Rules are evaluated once to create an exact plan. Preview and application
then replay that serialized plan against a digest-pinned IR document. Text
operations target scalar leaves, so cleaning never replaces a rich block with
a plain paragraph.
"""
from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, replace
from typing import Any, Literal

from veriformis.errors import CleaningPlanError, RuleError
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)
from veriformis.ir import (
    Blockquote,
    Bold,
    Cell,
    Code,
    CodeBlock,
    Document,
    Heading,
    Image,
    Italic,
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
    block_text,
    document_to_dict,
    iter_document_blocks,
)
from veriformis.rules.engine import Edit, Rule, TransformRecord
from veriformis.rules.engine import RegexRule

CLEANING_PLAN_SCHEMA = "veriformis.cleaning-plan/v1"
CLEANING_INPUT_SCHEMA = "veriformis.cleaning-input/v1"

PathPart = str | int


def _canonical_json(value: Any) -> str:
    return lossless_json_bytes(value).decode("utf-8")


def _digest_text(value: str) -> str:
    return sha256_digest(value)


def _digest_value(value: Any) -> str:
    return sha256_digest(lossless_json_bytes(value))


def document_digest(document: Document) -> str:
    return _digest_value(document_to_dict(document))


def cleaning_input_digest(
    document: Document,
    *,
    source_id: str,
    raw_sha256: str,
    canonical_artifact_id: str,
    canonical_stream_sha256: str,
    parser: str,
    parser_version: str,
    canonical_stream_contract_version: int,
) -> str:
    """Digest the portable parse snapshot consumed by a cleaning plan."""
    try:
        validate_id(source_id, kind="src")
        validate_id(canonical_artifact_id, kind="art")
        validate_sha256(raw_sha256)
        validate_sha256(canonical_stream_sha256)
    except ValueError as exc:
        raise RuleError(f"invalid cleaning input identity: {exc}") from exc
    if not parser or not parser_version:
        raise RuleError("cleaning input requires parser identity")
    if type(canonical_stream_contract_version) is not int:
        raise RuleError("cleaning input contract version must be an integer")
    return canonical_digest(
        {
            "schema_version": CLEANING_INPUT_SCHEMA,
            "source_id": source_id,
            "raw_sha256": raw_sha256,
            "canonical_artifact_id": canonical_artifact_id,
            "canonical_stream_sha256": canonical_stream_sha256,
            "document_sha256": document_digest(document),
            "parser": parser,
            "parser_version": parser_version,
            "canonical_stream_contract_version": (
                canonical_stream_contract_version
            ),
        }
    )


@dataclass(frozen=True)
class RuleSpec:
    name: str
    version: int
    scope: Literal["source-structure", "text-leaf"]
    params: dict[str, Any]


@dataclass(frozen=True)
class CleaningOperation:
    id: str
    kind: Literal["replace-text", "remove-block"]
    sequence: int
    source_id: str
    rule: str
    block_index: int
    path: tuple[PathPart, ...]
    start: int
    end: int
    expected: str
    replacement: str
    expected_sha256: str
    source_start: int | None = None
    source_end: int | None = None
    source_text_sha256: str | None = None


@dataclass(frozen=True)
class CleaningRun:
    rule: RuleSpec
    status: Literal[
        "applied", "no-change", "skipped-safety", "rejected-structure"
    ]
    operation_ids: tuple[str, ...]
    chars_removed: int
    bytes_removed: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CleaningPlan:
    schema_version: str
    id: str
    source_id: str
    base_input_sha256: str
    base_document_sha256: str
    output_document_sha256: str
    max_remove_ppm: int
    rules: tuple[RuleSpec, ...]
    runs: tuple[CleaningRun, ...]
    operations: tuple[CleaningOperation, ...]
    transform_record_ids: tuple[str, ...]


@dataclass(frozen=True)
class CleaningPreview:
    plan: CleaningPlan
    document: Document
    records: tuple[TransformRecord, ...]
    warnings: tuple[str, ...]


def _plan_payload(plan: CleaningPlan) -> dict[str, Any]:
    payload = asdict(plan)
    payload["id"] = ""
    return payload


def _plan_id(plan: CleaningPlan) -> str:
    return derive_id("cln", _plan_payload(plan))


def _operation_id(operation: CleaningOperation) -> str:
    payload = asdict(operation)
    payload["id"] = ""
    payload["replacement_sha256"] = sha256_digest(operation.replacement)
    return derive_id("op", payload)


def _record_id(record: TransformRecord) -> str:
    payload = asdict(record)
    payload["id"] = ""
    return derive_id("trn", payload)


def _rule_spec(rule: Rule) -> RuleSpec:
    name = rule.name
    params = dict(getattr(rule, "params", {}))
    if isinstance(rule, RegexRule):
        params.update(
            {
                "pattern": rule.pattern,
                "replacement": rule.replacement,
                "flags": rule.flags,
            }
        )
    return RuleSpec(
        name=name,
        version=1,
        scope="source-structure"
        if name in {"page-numbers", "headers-footers"}
        else "text-leaf",
        params=params,
    )


def _block_identity(block: Any) -> str:
    return _canonical_json(
        {
            "type": type(block).__name__,
            "value": asdict(block),
        }
    )


def _get_path(root: Any, path: tuple[PathPart, ...]) -> Any:
    value = root
    for part in path:
        if isinstance(value, (list, dict)):
            value = value[part]
        else:
            value = getattr(value, part)
    return value


def _set_path(root: Any, path: tuple[PathPart, ...], value: Any) -> None:
    if not path:
        raise CleaningPlanError("cleaning operation cannot replace the document root")
    parent = _get_path(root, path[:-1])
    last = path[-1]
    if isinstance(parent, (list, dict)):
        parent[last] = value
    else:
        setattr(parent, last, value)


_INLINE_WRAPPERS = (
    Bold,
    Italic,
    Strikethrough,
    Superscript,
    Subscript,
    Link,
)


def _text_leaves(
    node: Any,
    path: tuple[PathPart, ...],
    block_index: int,
    *,
    block_root: bool = False,
) -> list[tuple[tuple[PathPart, ...], int, str]]:
    # Literal/code/math payloads are semantic source, not prose.  Applying the
    # stock whitespace and punctuation rules to them can change program
    # behavior or mathematical meaning.  They stay visible in the block
    # projection so a prose rule that crosses their boundary is rejected, but
    # they are never editable without a future, explicitly typed literal rule.
    if isinstance(node, (Code, CodeBlock, Math)):
        return []
    if isinstance(node, Text):
        return [(path + ("value",), block_index, node.value)]
    if isinstance(node, Image):
        return (
            [(path + ("alt",), block_index, node.alt)]
            if block_root and node.alt
            else []
        )
    if isinstance(node, (Heading, Paragraph, *_INLINE_WRAPPERS, Cell)):
        out = []
        for index, child in enumerate(node.children):
            out.extend(
                _text_leaves(child, path + ("children", index), block_index)
            )
        return out
    if isinstance(node, Blockquote):
        out = []
        for index, child in enumerate(node.children):
            out.extend(
                _text_leaves(
                    child,
                    path + ("children", index),
                    block_index,
                    block_root=True,
                )
            )
        return out
    if isinstance(node, ListItem):
        out = []
        for index, child in enumerate(node.children):
            out.extend(
                _text_leaves(
                    child,
                    path + ("children", index),
                    block_index,
                    block_root=True,
                )
            )
        return out
    if isinstance(node, ListBlock):
        out = []
        for index, item in enumerate(node.items):
            out.extend(_text_leaves(item, path + ("items", index), block_index))
        return out
    if isinstance(node, Table):
        out = []
        for index, cell in enumerate(node.headers):
            out.extend(_text_leaves(cell, path + ("headers", index), block_index))
        for row_index, row in enumerate(node.rows):
            for cell_index, cell in enumerate(row):
                out.extend(
                    _text_leaves(
                        cell,
                        path + ("rows", row_index, cell_index),
                        block_index,
                    )
                )
        return out
    return []


def _all_text_leaves(document: Document):
    out = []
    for index, block in enumerate(document.children):
        block_index = block.block_index if block.block_index != -1 else index
        out.extend(
            _text_leaves(
                block,
                ("children", index),
                block_index,
                block_root=True,
            )
        )
    for collection_name in ("footnotes", "endnotes"):
        collection = getattr(document, collection_name)
        for note_id, note in sorted(collection.items()):
            for index, block in enumerate(note.children):
                block_index = block.block_index
                out.extend(
                    _text_leaves(
                        block,
                        (collection_name, note_id, "children", index),
                        block_index,
                        block_root=True,
                    )
                )
    return out


@dataclass(frozen=True)
class _ProjectedLeaf:
    path: tuple[PathPart, ...]
    block_index: int
    value: str
    start: int
    end: int


@dataclass(frozen=True)
class _BlockProjection:
    path: tuple[PathPart, ...]
    block_index: int
    text: str
    leaves: tuple[_ProjectedLeaf, ...]
    span_start: int | None
    span_end: int | None
    source_text_sha256: str | None


def _project_block(
    block: Any,
    path: tuple[PathPart, ...],
    block_index: int,
) -> _BlockProjection:
    rendered = block_text(block)
    cursor = 0
    projected: list[_ProjectedLeaf] = []
    for leaf_path, _, value in _text_leaves(
        block, path, block_index, block_root=True
    ):
        if not value:
            continue
        start = rendered.find(value, cursor)
        if start < 0:
            raise RuleError(
                f"IR text projection cannot locate leaf at {leaf_path!r}"
            )
        end = start + len(value)
        projected.append(
            _ProjectedLeaf(leaf_path, block_index, value, start, end)
        )
        cursor = end
    span = getattr(block, "span", None)
    return _BlockProjection(
        path=path,
        block_index=block_index,
        text=rendered,
        leaves=tuple(projected),
        span_start=span.start if span is not None else None,
        span_end=span.end if span is not None else None,
        source_text_sha256=sha256_digest(rendered) if span is not None else None,
    )


def _all_block_projections(document: Document) -> list[_BlockProjection]:
    projections = []
    for index, block in enumerate(document.children):
        block_index = block.block_index if block.block_index != -1 else index
        projections.append(
            _project_block(block, ("children", index), block_index)
        )
    for collection_name in ("footnotes", "endnotes"):
        collection = getattr(document, collection_name)
        for note_id, note in sorted(collection.items()):
            for index, block in enumerate(note.children):
                block_index = block.block_index
                projections.append(
                    _project_block(
                        block,
                        (collection_name, note_id, "children", index),
                        block_index,
                    )
                )
    return projections


def _cleaning_text(document: Document) -> str:
    """Deterministic text projection used only for cleaning safety metrics."""
    return "\n\n".join(
        projection.text for projection in _all_block_projections(document)
    )


def _source_locations(
    document: Document,
) -> dict[int, tuple[int, int, str]]:
    locations: dict[int, tuple[int, int, str]] = {}
    for index, block in enumerate(iter_document_blocks(document)):
        block_index = block.block_index if block.block_index != -1 else index
        span = getattr(block, "span", None)
        if span is None:
            continue
        if block_index in locations:
            raise RuleError(f"duplicate top-level block index {block_index}")
        locations[block_index] = (
            span.start,
            span.end,
            sha256_digest(block_text(block)),
        )
    return locations


def _apply_edits(text: str, edits: list[Edit]) -> str:
    ordered = sorted(edits, key=lambda edit: (edit.start, edit.end))
    previous_end = 0
    for edit in ordered:
        if not (0 <= edit.start <= edit.end <= len(text)):
            raise RuleError("rule emitted an out-of-bounds edit")
        if edit.start < previous_end:
            raise RuleError("rule emitted overlapping edits")
        previous_end = edit.end
    current = text
    for edit in reversed(ordered):
        current = current[: edit.start] + edit.replacement + current[edit.end :]
    return current


class _StructureBoundaryError(ValueError):
    pass


def _compile_projected_edits(
    projection: _BlockProjection,
    edits: list[Edit],
) -> tuple[dict[tuple[PathPart, ...], str], list[Edit]]:
    """Map canonical block edits back to scalar leaves without flattening.

    Edits crossing adjacent inline leaves are preserved. An edit touching a
    generated list, table, block, or line separator is rejected explicitly.
    """
    values = {leaf.path: leaf.value for leaf in projection.leaves}
    accepted: list[Edit] = []
    for edit in sorted(edits, key=lambda item: (item.start, item.end), reverse=True):
        if edit.start == edit.end:
            raise _StructureBoundaryError("zero-width insertions are not supported")
        affected = [
            leaf
            for leaf in projection.leaves
            if edit.start < leaf.end and edit.end > leaf.start
        ]
        covered = sum(
            min(edit.end, leaf.end) - max(edit.start, leaf.start)
            for leaf in affected
        )
        if not affected or covered != edit.end - edit.start:
            raise _StructureBoundaryError(
                f"edit {edit.start}:{edit.end} touches a generated structural separator"
            )
        for position, leaf in enumerate(affected):
            local_start = max(edit.start, leaf.start) - leaf.start
            local_end = min(edit.end, leaf.end) - leaf.start
            current = values[leaf.path]
            replacement = edit.replacement if position == 0 else ""
            values[leaf.path] = (
                current[:local_start] + replacement + current[local_end:]
            )
        accepted.append(edit)

    reconstructed = projection.text
    for leaf in sorted(projection.leaves, key=lambda item: item.start, reverse=True):
        reconstructed = (
            reconstructed[: leaf.start]
            + values[leaf.path]
            + reconstructed[leaf.end :]
        )
    expected = _apply_edits(projection.text, list(reversed(accepted)))
    if reconstructed != expected:
        raise RuleError("compiled leaf edits do not reproduce their canonical output")
    return values, list(reversed(accepted))


def _make_operation(
    *,
    kind: Literal["replace-text", "remove-block"],
    sequence: int,
    source_id: str,
    rule: str,
    block_index: int,
    path: tuple[PathPart, ...],
    start: int,
    end: int,
    expected: str,
    replacement: str,
    source_start: int | None = None,
    source_end: int | None = None,
    source_text_sha256: str | None = None,
) -> CleaningOperation:
    operation = CleaningOperation(
        id="",
        kind=kind,
        sequence=sequence,
        source_id=source_id,
        rule=rule,
        block_index=block_index,
        path=path,
        start=start,
        end=end,
        expected=expected,
        replacement=replacement,
        expected_sha256=_digest_text(expected),
        source_start=source_start,
        source_end=source_end,
        source_text_sha256=source_text_sha256,
    )
    return replace(operation, id=_operation_id(operation))


def _apply_operation(document: Document, operation: CleaningOperation) -> None:
    if operation.id != _operation_id(replace(operation, id="")):
        raise CleaningPlanError(f"operation {operation.id!r} digest mismatch")
    if operation.source_id != document.source_id:
        raise CleaningPlanError(
            f"operation {operation.id!r} targets source {operation.source_id!r}, "
            f"not {document.source_id!r}"
        )
    if operation.kind not in {"replace-text", "remove-block"}:
        raise CleaningPlanError(
            f"operation {operation.id!r} has unsupported kind {operation.kind!r}"
        )
    if (operation.source_start is None) != (operation.source_end is None):
        raise CleaningPlanError(
            f"operation {operation.id!r} has an incomplete source range"
        )
    if operation.source_start is not None and not (
        0 <= operation.source_start <= operation.source_end
    ):
        raise CleaningPlanError(
            f"operation {operation.id!r} has an invalid source range"
        )
    if operation.kind == "remove-block":
        if (
            operation.start != 0
            or operation.end != len(operation.expected)
            or operation.replacement
        ):
            raise CleaningPlanError(
                f"operation {operation.id!r} has invalid block-removal fields"
            )
        if (
            len(operation.path) != 2
            or operation.path[0] != "children"
            or not isinstance(operation.path[1], int)
        ):
            raise CleaningPlanError(
                f"operation {operation.id!r} is not a top-level block removal"
            )
        block = _get_path(document, operation.path)
        if not _is_plain_paragraph(block):
            raise CleaningPlanError(
                f"operation {operation.id!r} cannot remove a rich IR block"
            )
        expected_index = (
            block.block_index
            if getattr(block, "block_index", -1) != -1
            else operation.path[1]
        )
        if operation.block_index != expected_index:
            raise CleaningPlanError(
                f"operation {operation.id!r} block attribution mismatch"
            )
        actual = _block_identity(block)
        if actual != operation.expected or _digest_text(actual) != operation.expected_sha256:
            raise CleaningPlanError(
                f"operation {operation.id!r} block precondition failed"
            )
        parent = _get_path(document, operation.path[:-1])
        index = operation.path[-1]
        if not isinstance(index, int):
            raise CleaningPlanError("remove-block path must end in an index")
        del parent[index]
        return

    valid_targets = {
        path: block_index
        for path, block_index, _ in _all_text_leaves(document)
    }
    if operation.path not in valid_targets:
        raise CleaningPlanError(
            f"operation {operation.id!r} targets a non-editable IR field"
        )
    if operation.block_index != valid_targets[operation.path]:
        raise CleaningPlanError(
            f"operation {operation.id!r} block attribution mismatch"
        )
    current = _get_path(document, operation.path)
    if not isinstance(current, str):
        raise CleaningPlanError(
            f"operation {operation.id!r} does not target a text scalar"
        )
    if not (0 <= operation.start <= operation.end <= len(current)):
        raise CleaningPlanError(f"operation {operation.id!r} range is invalid")
    actual = current[operation.start : operation.end]
    if actual != operation.expected or _digest_text(actual) != operation.expected_sha256:
        raise CleaningPlanError(
            f"operation {operation.id!r} text precondition failed"
        )
    _set_path(
        document,
        operation.path,
        current[: operation.start]
        + operation.replacement
        + current[operation.end :],
    )


def _is_plain_paragraph(block: Any) -> bool:
    return (
        isinstance(block, Paragraph)
        and bool(block.children)
        and all(isinstance(child, Text) for child in block.children)
    )


def _structural_candidates(document: Document, rule: Rule) -> list[int]:
    if rule.name == "headers-footers":
        threshold = int(getattr(rule, "threshold", 3))
        counts: dict[str, int] = {}
        for block in document.children:
            if not _is_plain_paragraph(block):
                continue
            key = block_text(block).strip()
            if key and len(key) <= 80:
                counts[key] = counts.get(key, 0) + 1
        return [
            index
            for index, block in enumerate(document.children)
            if _is_plain_paragraph(block)
            and (key := block_text(block).strip())
            and len(key) <= 80
            and counts.get(key, 0) >= threshold
        ]
    if rule.name == "page-numbers":
        matches = []
        for index, block in enumerate(document.children):
            if not _is_plain_paragraph(block):
                continue
            text = block_text(block)
            result = rule.apply(text)
            if result.edits and not result.text.strip():
                matches.append(index)
        return matches
    return []


def _transform_record(
    *,
    source_id: str,
    rule: RuleSpec,
    block_index: int,
    operations: list[CleaningOperation],
    before: str,
    after: str,
    rule_index: int,
    warned: bool = False,
) -> TransformRecord:
    record = TransformRecord(
        rule=rule.name,
        params=dict(rule.params),
        block_index=block_index,
        edits=len(operations),
        bytes_removed=max(
            0, len(before.encode("utf-8")) - len(after.encode("utf-8"))
        ),
        warned=warned,
        source_id=source_id,
        chars_removed=max(0, len(before) - len(after)),
        operation_ids=tuple(operation.id for operation in operations),
        input_sha256=_digest_text(before),
        output_sha256=_digest_text(after),
        rule_index=rule_index,
    )
    return replace(record, id=_record_id(record))


def plan_cleaning(
    document: Document,
    rules: list[Rule],
    *,
    max_remove_frac: float = 0.3,
    base_input_sha256: str = "",
) -> CleaningPreview:
    if not (0.0 <= max_remove_frac <= 1.0):
        raise RuleError("max_remove_frac must be between 0 and 1")
    if base_input_sha256:
        try:
            validate_sha256(base_input_sha256)
            validate_id(document.source_id, kind="src")
        except ValueError as exc:
            raise RuleError(
                "durable cleaning plans require valid source and parse-input identities"
            ) from exc

    base_digest = document_digest(document)
    source_locations = _source_locations(document)
    working = copy.deepcopy(document)
    operations: list[CleaningOperation] = []
    runs: list[CleaningRun] = []
    records: list[TransformRecord] = []
    warnings: list[str] = []
    specs = tuple(_rule_spec(rule) for rule in rules)

    for rule_index, (rule, spec) in enumerate(zip(rules, specs, strict=True)):
        run_operations: list[CleaningOperation] = []
        run_records: list[TransformRecord] = []
        run_warnings: list[str] = []
        before_source = _cleaning_text(working)

        if spec.scope == "source-structure":
            candidates = _structural_candidates(working, rule)
            trial = copy.deepcopy(working)
            for index in sorted(candidates, reverse=True):
                del trial.children[index]
            candidate_text = max(0, len(before_source) - len(_cleaning_text(trial)))
            warned = bool(before_source) and candidate_text > max_remove_frac * len(before_source)
            if warned:
                warning = (
                    f"rule '{rule.name}' skipped: would remove "
                    f"{candidate_text}/{len(before_source)} chars"
                )
                warnings.append(warning)
                runs.append(
                    CleaningRun(
                        rule=spec,
                        status="skipped-safety",
                        operation_ids=(),
                        chars_removed=0,
                        bytes_removed=0,
                        warnings=tuple([*run_warnings, warning]),
                    )
                )
                records.append(
                    _transform_record(
                        source_id=working.source_id,
                        rule=spec,
                        block_index=-1,
                        operations=[],
                        before=before_source,
                        after=before_source,
                        rule_index=rule_index,
                        warned=True,
                    )
                )
                continue

            for index in sorted(candidates, reverse=True):
                block = working.children[index]
                block_index = block.block_index if block.block_index != -1 else index
                before = block_text(block)
                expected = _block_identity(block)
                location = source_locations.get(block_index)
                operation = _make_operation(
                    kind="remove-block",
                    sequence=len(operations) + len(run_operations),
                    source_id=working.source_id,
                    rule=rule.name,
                    block_index=block_index,
                    path=("children", index),
                    start=0,
                    end=len(expected),
                    expected=expected,
                    replacement="",
                    source_start=location[0] if location is not None else None,
                    source_end=location[1] if location is not None else None,
                    source_text_sha256=location[2] if location is not None else None,
                )
                _apply_operation(working, operation)
                run_operations.append(operation)
                run_records.append(
                    _transform_record(
                        source_id=working.source_id,
                        rule=spec,
                        block_index=block_index,
                        operations=[operation],
                        before=before,
                        after="",
                        rule_index=rule_index,
                    )
                )
        else:
            proposals = []
            for projection in _all_block_projections(working):
                result = rule.apply(projection.text)
                if _apply_edits(projection.text, result.edits) != result.text:
                    raise RuleError(
                        f"rule '{rule.name}' edits do not reproduce its output"
                    )
                safe_edits: list[Edit] = []
                for edit in result.edits:
                    try:
                        _compile_projected_edits(projection, [edit])
                    except _StructureBoundaryError as exc:
                        warning = (
                            f"rule '{rule.name}' skipped edit in block "
                            f"{projection.block_index}: {exc}"
                        )
                        warnings.append(warning)
                        run_warnings.append(warning)
                    else:
                        safe_edits.append(edit)
                if safe_edits:
                    values, _ = _compile_projected_edits(projection, safe_edits)
                    after = _apply_edits(projection.text, safe_edits)
                    proposals.append((projection, values, after))

            after_source_size = len(before_source)
            for projection, _, after in proposals:
                after_source_size += len(after) - len(projection.text)
            removed = max(0, len(before_source) - after_source_size)
            warned = bool(before_source) and removed > max_remove_frac * len(before_source)
            if warned:
                warning = (
                    f"rule '{rule.name}' skipped: would remove "
                    f"{removed}/{len(before_source)} chars"
                )
                warnings.append(warning)
                runs.append(
                    CleaningRun(
                        rule=spec,
                        status="skipped-safety",
                        operation_ids=(),
                        chars_removed=0,
                        bytes_removed=0,
                        warnings=tuple([*run_warnings, warning]),
                    )
                )
                records.append(
                    _transform_record(
                        source_id=working.source_id,
                        rule=spec,
                        block_index=-1,
                        operations=[],
                        before=before_source,
                        after=before_source,
                        rule_index=rule_index,
                        warned=True,
                    )
                )
                continue

            for projection, values, after in proposals:
                leaf_operations: list[CleaningOperation] = []
                for leaf in projection.leaves:
                    replacement = values[leaf.path]
                    if replacement == leaf.value:
                        continue
                    location = source_locations.get(projection.block_index)
                    operation = _make_operation(
                        kind="replace-text",
                        sequence=len(operations) + len(run_operations),
                        source_id=working.source_id,
                        rule=rule.name,
                        block_index=projection.block_index,
                        path=leaf.path,
                        start=0,
                        end=len(leaf.value),
                        expected=leaf.value,
                        replacement=replacement,
                        source_start=location[0] if location is not None else None,
                        source_end=location[1] if location is not None else None,
                        source_text_sha256=location[2] if location is not None else None,
                    )
                    _apply_operation(working, operation)
                    run_operations.append(operation)
                    leaf_operations.append(operation)
                if leaf_operations:
                    run_records.append(
                        _transform_record(
                            source_id=working.source_id,
                            rule=spec,
                            block_index=projection.block_index,
                            operations=leaf_operations,
                            before=projection.text,
                            after=after,
                            rule_index=rule_index,
                        )
                    )

        after_source = _cleaning_text(working)
        operations.extend(run_operations)
        records.extend(run_records)
        runs.append(
            CleaningRun(
                rule=spec,
                status=(
                    "applied"
                    if run_operations
                    else "rejected-structure"
                    if run_warnings
                    else "no-change"
                ),
                operation_ids=tuple(operation.id for operation in run_operations),
                chars_removed=max(0, len(before_source) - len(after_source)),
                bytes_removed=max(
                    0,
                    len(before_source.encode("utf-8"))
                    - len(after_source.encode("utf-8")),
                ),
                warnings=tuple(run_warnings),
            )
        )

    plan = CleaningPlan(
        schema_version=CLEANING_PLAN_SCHEMA,
        id="",
        source_id=document.source_id,
        base_input_sha256=base_input_sha256,
        base_document_sha256=base_digest,
        output_document_sha256=document_digest(working),
        max_remove_ppm=round(max_remove_frac * 1_000_000),
        rules=specs,
        runs=tuple(runs),
        operations=tuple(operations),
        transform_record_ids=tuple(record.id for record in records),
    )
    if base_input_sha256 and any(
        operation.source_start is None
        or operation.source_end is None
        or operation.source_text_sha256 is None
        for operation in plan.operations
    ):
        raise RuleError("durable cleaning operations require immutable source locations")
    plan = replace(plan, id=_plan_id(plan))
    return CleaningPreview(
        plan=plan,
        document=working,
        records=tuple(records),
        warnings=tuple(warnings),
    )


def expected_transform_records(
    document: Document,
    plan: CleaningPlan,
) -> tuple[TransformRecord, ...]:
    """Reconstruct the only transform audit log valid for ``plan``.

    The plan is executable authority. Transform records are a redundant audit
    projection, so their complete metadata must be derived from plan replay
    rather than trusted merely because their IDs are self-consistent.
    """
    replay_cleaning_plan(document, plan)
    operations_by_id = {operation.id: operation for operation in plan.operations}
    audit = copy.deepcopy(document)
    records: list[TransformRecord] = []

    def projection_text(block_index: int) -> str:
        matches = [
            projection.text
            for projection in _all_block_projections(audit)
            if projection.block_index == block_index
        ]
        if len(matches) != 1:
            raise CleaningPlanError(
                f"cleaning audit cannot resolve block {block_index} exactly once"
            )
        return matches[0]

    for rule_index, (spec, run) in enumerate(
        zip(plan.rules, plan.runs, strict=True)
    ):
        run_operations = [operations_by_id[item] for item in run.operation_ids]
        if run.status == "skipped-safety":
            before = _cleaning_text(audit)
            records.append(
                _transform_record(
                    source_id=plan.source_id,
                    rule=spec,
                    block_index=-1,
                    operations=[],
                    before=before,
                    after=before,
                    rule_index=rule_index,
                    warned=True,
                )
            )
            continue

        if spec.scope == "source-structure":
            if any(operation.kind != "remove-block" for operation in run_operations):
                raise CleaningPlanError(
                    f"structural rule {spec.name!r} contains a text operation"
                )
            for operation in run_operations:
                block = _get_path(audit, operation.path)
                before = block_text(block)
                _apply_operation(audit, operation)
                records.append(
                    _transform_record(
                        source_id=plan.source_id,
                        rule=spec,
                        block_index=operation.block_index,
                        operations=[operation],
                        before=before,
                        after="",
                        rule_index=rule_index,
                    )
                )
            continue

        if any(operation.kind != "replace-text" for operation in run_operations):
            raise CleaningPlanError(
                f"text rule {spec.name!r} contains a structural operation"
            )
        groups: list[list[CleaningOperation]] = []
        for operation in run_operations:
            if not groups or groups[-1][0].block_index != operation.block_index:
                if any(
                    group[0].block_index == operation.block_index
                    for group in groups
                ):
                    raise CleaningPlanError(
                        "cleaning operations revisit a block out of order"
                    )
                groups.append([])
            groups[-1].append(operation)
        for group in groups:
            block_index = group[0].block_index
            before = projection_text(block_index)
            for operation in group:
                _apply_operation(audit, operation)
            after = projection_text(block_index)
            records.append(
                _transform_record(
                    source_id=plan.source_id,
                    rule=spec,
                    block_index=block_index,
                    operations=group,
                    before=before,
                    after=after,
                    rule_index=rule_index,
                )
            )

    expected_ids = tuple(record.id for record in records)
    if expected_ids != plan.transform_record_ids:
        raise CleaningPlanError(
            "cleaning plan transform record identities do not match replay"
        )
    if document_digest(audit) != plan.output_document_sha256:
        raise CleaningPlanError(
            "transform audit replay does not reach the cleaning plan output"
        )
    return tuple(records)


def _validate_plan_relations(document: Document, plan: CleaningPlan) -> None:
    if len(plan.rules) != len(plan.runs):
        raise CleaningPlanError("cleaning plan rule and run counts differ")
    if plan.max_remove_ppm < 0 or plan.max_remove_ppm > 1_000_000:
        raise CleaningPlanError("cleaning plan removal limit is invalid")
    operation_ids = [operation.id for operation in plan.operations]
    if len(operation_ids) != len(set(operation_ids)):
        raise CleaningPlanError("cleaning plan contains duplicate operation identities")
    if len(plan.transform_record_ids) != len(set(plan.transform_record_ids)):
        raise CleaningPlanError(
            "cleaning plan contains duplicate transform record identities"
        )
    try:
        for record_id in plan.transform_record_ids:
            validate_id(record_id, kind="trn")
    except ValueError as exc:
        raise CleaningPlanError(
            "cleaning plan contains an invalid transform record identity"
        ) from exc
    referenced: list[str] = []
    operations_by_id = {operation.id: operation for operation in plan.operations}
    for spec, run in zip(plan.rules, plan.runs, strict=True):
        if run.rule != spec:
            raise CleaningPlanError("cleaning plan run does not match its rule")
        for operation_id in run.operation_ids:
            operation = operations_by_id.get(operation_id)
            if operation is None:
                raise CleaningPlanError(
                    f"cleaning run references unknown operation {operation_id!r}"
                )
            if operation.rule != spec.name:
                raise CleaningPlanError(
                    f"operation {operation_id!r} is attributed to the wrong rule"
                )
            referenced.append(operation_id)
    if referenced != operation_ids:
        raise CleaningPlanError(
            "cleaning runs do not partition operations in execution order"
        )

    audit = copy.deepcopy(document)
    for run in plan.runs:
        run_operations = [operations_by_id[item] for item in run.operation_ids]
        before = _cleaning_text(audit)
        for operation in run_operations:
            _apply_operation(audit, operation)
        after = _cleaning_text(audit)
        expected_chars = max(0, len(before) - len(after))
        expected_bytes = max(
            0,
            len(before.encode("utf-8")) - len(after.encode("utf-8")),
        )
        if run.chars_removed != expected_chars or run.bytes_removed != expected_bytes:
            raise CleaningPlanError(
                f"cleaning run {run.rule.name!r} audit counts do not match replay"
            )
        if run_operations:
            expected_status = "applied"
        elif not run.warnings:
            expected_status = "no-change"
        elif any("skipped: would remove" in warning for warning in run.warnings):
            expected_status = "skipped-safety"
        else:
            expected_status = "rejected-structure"
        if run.status != expected_status:
            raise CleaningPlanError(
                f"cleaning run {run.rule.name!r} status does not match replay"
            )

    locations = _source_locations(document)
    for operation in plan.operations:
        expected = locations.get(operation.block_index)
        actual = (
            operation.source_start,
            operation.source_end,
            operation.source_text_sha256,
        )
        if expected is not None and actual != expected:
            raise CleaningPlanError(
                f"operation {operation.id!r} source evidence mismatch"
            )
        if expected is None and any(item is not None for item in actual):
            raise CleaningPlanError(
                f"operation {operation.id!r} invents an unavailable source range"
            )
        if plan.base_input_sha256 and any(item is None for item in actual):
            raise CleaningPlanError(
                f"operation {operation.id!r} lacks a durable source location"
            )


def replay_cleaning_plan(document: Document, plan: CleaningPlan) -> Document:
    if plan.schema_version != CLEANING_PLAN_SCHEMA:
        raise CleaningPlanError(
            f"unsupported cleaning plan schema {plan.schema_version!r}"
        )
    if plan.id != _plan_id(replace(plan, id="")):
        raise CleaningPlanError("cleaning plan digest mismatch")
    if document.source_id != plan.source_id:
        raise CleaningPlanError(
            f"cleaning plan targets source {plan.source_id!r}, not {document.source_id!r}"
        )
    if document_digest(document) != plan.base_document_sha256:
        raise CleaningPlanError("cleaning plan base document digest mismatch")
    _validate_plan_relations(document, plan)

    output = copy.deepcopy(document)
    expected_sequence = list(range(len(plan.operations)))
    if [operation.sequence for operation in plan.operations] != expected_sequence:
        raise CleaningPlanError("cleaning plan operation sequence is not contiguous")
    for operation in plan.operations:
        _apply_operation(output, operation)
    if document_digest(output) != plan.output_document_sha256:
        raise CleaningPlanError("cleaning plan output document digest mismatch")
    return output


def cleaning_plan_to_dict(plan: CleaningPlan) -> dict[str, Any]:
    return json.loads(_canonical_json(asdict(plan)))


def cleaning_plan_from_dict(value: dict[str, Any]) -> CleaningPlan:
    try:
        expected_top = {
            "schema_version",
            "id",
            "source_id",
            "base_input_sha256",
            "base_document_sha256",
            "output_document_sha256",
            "max_remove_ppm",
            "rules",
            "runs",
            "operations",
            "transform_record_ids",
        }
        if set(value) != expected_top:
            raise CleaningPlanError(
                "cleaning plan keys do not match the v1 schema"
            )
        rule_keys = {"name", "version", "scope", "params"}
        run_keys = {
            "rule",
            "status",
            "operation_ids",
            "chars_removed",
            "bytes_removed",
            "warnings",
        }
        operation_keys = {
            "id",
            "kind",
            "sequence",
            "source_id",
            "rule",
            "block_index",
            "path",
            "start",
            "end",
            "expected",
            "replacement",
            "expected_sha256",
            "source_start",
            "source_end",
            "source_text_sha256",
        }
        if any(set(rule) != rule_keys for rule in value["rules"]):
            raise CleaningPlanError("cleaning rule keys do not match the v1 schema")
        if any(set(run) != run_keys or set(run["rule"]) != rule_keys for run in value["runs"]):
            raise CleaningPlanError("cleaning run keys do not match the v1 schema")
        if any(set(operation) != operation_keys for operation in value["operations"]):
            raise CleaningPlanError(
                "cleaning operation keys do not match the v1 schema"
            )
        if value["schema_version"] != CLEANING_PLAN_SCHEMA:
            raise CleaningPlanError("unsupported cleaning plan schema")
        if not isinstance(value["id"], str):
            raise CleaningPlanError("cleaning plan id must be a string")
        validate_id(value["id"], kind="cln")
        if not isinstance(value["source_id"], str) or not value["source_id"]:
            raise CleaningPlanError("cleaning plan source id must be a non-empty string")
        if not isinstance(value["base_input_sha256"], str):
            raise CleaningPlanError("cleaning plan base input digest must be a string")
        if value["base_input_sha256"]:
            validate_sha256(value["base_input_sha256"])
            validate_id(value["source_id"], kind="src")
        validate_sha256(value["base_document_sha256"])
        validate_sha256(value["output_document_sha256"])
        if (
            not isinstance(value["max_remove_ppm"], int)
            or isinstance(value["max_remove_ppm"], bool)
            or not 0 <= value["max_remove_ppm"] <= 1_000_000
        ):
            raise CleaningPlanError("cleaning plan removal limit is invalid")
        if not isinstance(value["rules"], list) or not isinstance(value["runs"], list):
            raise CleaningPlanError("cleaning plan rules and runs must be arrays")
        if not isinstance(value["operations"], list):
            raise CleaningPlanError("cleaning plan operations must be an array")
        if (
            not isinstance(value["transform_record_ids"], list)
            or not all(
                isinstance(item, str) for item in value["transform_record_ids"]
            )
        ):
            raise CleaningPlanError(
                "cleaning plan transform record ids must be strings"
            )
        for record_id in value["transform_record_ids"]:
            validate_id(record_id, kind="trn")
        for rule in value["rules"]:
            _validate_rule_value(rule)
        for run in value["runs"]:
            _validate_rule_value(run["rule"])
            if run["status"] not in {
                "applied",
                "no-change",
                "skipped-safety",
                "rejected-structure",
            }:
                raise CleaningPlanError("cleaning run status is invalid")
            if (
                not isinstance(run["operation_ids"], list)
                or not all(isinstance(item, str) for item in run["operation_ids"])
            ):
                raise CleaningPlanError("cleaning run operation ids must be strings")
            for operation_id in run["operation_ids"]:
                validate_id(operation_id, kind="op")
            if any(
                not isinstance(run[field], int)
                or isinstance(run[field], bool)
                or run[field] < 0
                for field in ("chars_removed", "bytes_removed")
            ):
                raise CleaningPlanError("cleaning run counts must be non-negative integers")
            if (
                not isinstance(run["warnings"], list)
                or not all(isinstance(item, str) for item in run["warnings"])
            ):
                raise CleaningPlanError("cleaning run warnings must be strings")
        for operation in value["operations"]:
            _validate_operation_value(operation)
        rules = tuple(RuleSpec(**rule) for rule in value["rules"])
        runs = tuple(
            CleaningRun(
                rule=RuleSpec(**run["rule"]),
                status=run["status"],
                operation_ids=tuple(run["operation_ids"]),
                chars_removed=run["chars_removed"],
                bytes_removed=run["bytes_removed"],
                warnings=tuple(run["warnings"]),
            )
            for run in value["runs"]
        )
        operations = tuple(
            CleaningOperation(
                **{
                    **operation,
                    "path": tuple(operation["path"]),
                }
            )
            for operation in value["operations"]
        )
        plan = CleaningPlan(
            schema_version=value["schema_version"],
            id=value["id"],
            source_id=value["source_id"],
            base_input_sha256=value["base_input_sha256"],
            base_document_sha256=value["base_document_sha256"],
            output_document_sha256=value["output_document_sha256"],
            max_remove_ppm=value["max_remove_ppm"],
            rules=rules,
            runs=runs,
            operations=operations,
            transform_record_ids=tuple(value["transform_record_ids"]),
        )
        for operation in plan.operations:
            if operation.id != _operation_id(replace(operation, id="")):
                raise CleaningPlanError(
                    f"operation {operation.id!r} digest mismatch"
                )
        if plan.id != _plan_id(replace(plan, id="")):
            raise CleaningPlanError("cleaning plan digest mismatch")
        return plan
    except CleaningPlanError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise CleaningPlanError(f"invalid cleaning plan: {exc}") from exc


def _validate_rule_value(value: dict[str, Any]) -> None:
    if not isinstance(value["name"], str) or not value["name"]:
        raise CleaningPlanError("cleaning rule name must be a non-empty string")
    if (
        not isinstance(value["version"], int)
        or isinstance(value["version"], bool)
        or value["version"] < 1
    ):
        raise CleaningPlanError("cleaning rule version must be a positive integer")
    if value["scope"] not in {"source-structure", "text-leaf"}:
        raise CleaningPlanError("cleaning rule scope is invalid")
    if not isinstance(value["params"], dict):
        raise CleaningPlanError("cleaning rule parameters must be an object")
    lossless_json_bytes(value["params"])


def _validate_operation_value(value: dict[str, Any]) -> None:
    validate_id(value["id"], kind="op")
    if value["kind"] not in {"replace-text", "remove-block"}:
        raise CleaningPlanError("cleaning operation kind is invalid")
    for field in ("sequence", "block_index", "start", "end"):
        if not isinstance(value[field], int) or isinstance(value[field], bool):
            raise CleaningPlanError(f"cleaning operation {field} must be an integer")
    if value["sequence"] < 0 or value["start"] < 0 or value["end"] < value["start"]:
        raise CleaningPlanError("cleaning operation range or sequence is invalid")
    if not isinstance(value["source_id"], str) or not isinstance(value["rule"], str):
        raise CleaningPlanError("cleaning operation source and rule must be strings")
    if (
        not isinstance(value["path"], list)
        or not value["path"]
        or any(
            isinstance(item, bool) or not isinstance(item, (str, int))
            for item in value["path"]
        )
    ):
        raise CleaningPlanError("cleaning operation path is invalid")
    if not isinstance(value["expected"], str) or not isinstance(value["replacement"], str):
        raise CleaningPlanError("cleaning operation text fields must be strings")
    validate_sha256(value["expected_sha256"])
    source_values = (
        value["source_start"],
        value["source_end"],
        value["source_text_sha256"],
    )
    if all(item is None for item in source_values):
        return
    if (
        not isinstance(source_values[0], int)
        or isinstance(source_values[0], bool)
        or not isinstance(source_values[1], int)
        or isinstance(source_values[1], bool)
        or source_values[0] < 0
        or source_values[1] < source_values[0]
        or not isinstance(source_values[2], str)
    ):
        raise CleaningPlanError("cleaning operation source range is invalid")
    validate_sha256(source_values[2])
