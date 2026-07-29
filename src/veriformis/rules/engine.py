"""Deterministic cleaning-rule engine. Every firing is logged; destructive
rules are refused, never silently applied."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Protocol

from veriformis.errors import RuleError
from veriformis.identity import (
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)
from veriformis.ir import Document


TRANSFORM_RECORD_SCHEMA_VERSION = "veriformis.transform-record/v1"


@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    replacement: str = ""


@dataclass(frozen=True)
class RuleResult:
    text: str
    edits: list[Edit] = field(default_factory=list)


class Rule(Protocol):
    name: str

    def apply(self, text: str) -> RuleResult: ...


@dataclass
class RegexRule:
    name: str
    pattern: str
    replacement: str = ""
    flags: int = re.IGNORECASE | re.MULTILINE
    params: dict = field(default_factory=dict)

    def apply(self, text: str) -> RuleResult:
        rx = re.compile(self.pattern, self.flags)
        edits = [
            Edit(m.start(), m.end(), m.expand(self.replacement))
            for m in rx.finditer(text)
        ]
        return RuleResult(text=rx.sub(self.replacement, text), edits=edits)


@dataclass(frozen=True)
class TransformRecord:
    rule: str
    params: dict
    block_index: int
    edits: int
    bytes_removed: int
    warned: bool = False
    id: str = ""
    source_id: str = ""
    chars_removed: int = 0
    operation_ids: tuple[str, ...] = ()
    input_sha256: str = ""
    output_sha256: str = ""
    rule_index: int = 0
    schema_version: str = TRANSFORM_RECORD_SCHEMA_VERSION


def _transform_record_identity_payload(record: TransformRecord) -> dict[str, Any]:
    payload = asdict(record)
    payload["id"] = ""
    return payload


def derive_transform_record_id(record: TransformRecord) -> str:
    """Derive the v1 identity from every persisted semantic field."""
    return derive_id("trn", _transform_record_identity_payload(record))


def validate_transform_record(record: TransformRecord) -> None:
    """Reject malformed, cross-version, or content-ID-mismatched records."""
    if record.schema_version != TRANSFORM_RECORD_SCHEMA_VERSION:
        raise RuleError(
            f"unsupported transform record schema {record.schema_version!r}"
        )
    if not isinstance(record.rule, str) or not record.rule:
        raise RuleError("transform rule must be a non-empty string")
    if not isinstance(record.params, dict):
        raise RuleError("transform params must be an object")
    try:
        # This also rejects non-string keys, non-finite floats, and values that
        # cannot participate in a deterministic content identity.
        lossless_json_bytes(record.params)
        validate_id(record.id, kind="trn")
        validate_id(record.source_id, kind="src")
        validate_sha256(record.input_sha256)
        validate_sha256(record.output_sha256)
    except (TypeError, ValueError) as exc:
        raise RuleError(f"invalid transform identity or digest: {exc}") from exc
    if type(record.block_index) is not int or record.block_index < -1:
        raise RuleError("transform block_index must be -1 or a non-negative integer")
    for name in ("edits", "bytes_removed", "chars_removed", "rule_index"):
        value = getattr(record, name)
        if type(value) is not int or value < 0:
            raise RuleError(f"transform {name} must be a non-negative integer")
    if type(record.warned) is not bool:
        raise RuleError("transform warned must be a boolean")
    if not isinstance(record.operation_ids, tuple):
        raise RuleError("transform operation_ids must be a tuple")
    try:
        for operation_id in record.operation_ids:
            validate_id(operation_id, kind="op")
    except (TypeError, ValueError) as exc:
        raise RuleError(f"invalid transform operation identity: {exc}") from exc
    if len(record.operation_ids) != len(set(record.operation_ids)):
        raise RuleError("transform operation identities contain duplicates")
    if len(record.operation_ids) != record.edits:
        raise RuleError("transform edit count does not match its operation identities")
    if record.warned and (record.edits or record.bytes_removed or record.chars_removed):
        raise RuleError("a skipped transform cannot report applied removals")
    if record.edits == 0 and record.input_sha256 != record.output_sha256:
        raise RuleError("a transform without edits cannot change its output digest")
    try:
        expected_id = derive_transform_record_id(record)
    except (TypeError, ValueError) as exc:
        raise RuleError(f"invalid transform identity payload: {exc}") from exc
    if record.id != expected_id:
        raise RuleError("transform record identity mismatch")


def transform_record_to_dict(record: TransformRecord) -> dict[str, Any]:
    """Serialize a transform using the exact v1 persisted schema."""
    validate_transform_record(record)
    value = asdict(record)
    value["operation_ids"] = list(record.operation_ids)
    return value


def transform_record_from_dict(value: dict[str, Any]) -> TransformRecord:
    """Load a transform using the exact v1 persisted schema."""
    expected = {
        "schema_version",
        "id",
        "source_id",
        "rule",
        "params",
        "block_index",
        "edits",
        "bytes_removed",
        "warned",
        "chars_removed",
        "operation_ids",
        "input_sha256",
        "output_sha256",
        "rule_index",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise RuleError("transform record keys do not match the v1 schema")
    if not isinstance(value["operation_ids"], list):
        raise RuleError("transform operation_ids must be a list")
    if not all(isinstance(item, str) for item in value["operation_ids"]):
        raise RuleError("transform operation_ids must contain strings")
    record = TransformRecord(
        schema_version=value["schema_version"],
        id=value["id"],
        source_id=value["source_id"],
        rule=value["rule"],
        params=value["params"],
        block_index=value["block_index"],
        edits=value["edits"],
        bytes_removed=value["bytes_removed"],
        warned=value["warned"],
        chars_removed=value["chars_removed"],
        operation_ids=tuple(value["operation_ids"]),
        input_sha256=value["input_sha256"],
        output_sha256=value["output_sha256"],
        rule_index=value["rule_index"],
    )
    validate_transform_record(record)
    return record


def apply_rules(
    text: str,
    rules: list[Rule],
    *,
    source_id: str,
    max_remove_frac: float = 0.3,
) -> tuple[str, list[TransformRecord], list[str]]:
    """Apply raw-text rules with an explicit durable source scope."""
    try:
        validate_id(source_id, kind="src")
    except ValueError as exc:
        raise RuleError("raw-text cleaning requires a valid source identity") from exc
    if not 0.0 <= max_remove_frac <= 1.0:
        raise RuleError("max_remove_frac must be between 0 and 1")
    records: list[TransformRecord] = []
    warnings: list[str] = []
    current = text
    for rule_index, rule in enumerate(rules):
        before = current
        result = rule.apply(before)
        candidate_removed = max(0, len(before) - len(result.text))
        warned = len(before) > 0 and candidate_removed > max_remove_frac * len(before)
        after = before if warned else result.text
        applied_edits = [] if warned else result.edits
        params = dict(getattr(rule, "params", {}))
        if isinstance(rule, RegexRule):
            params.update(
                {
                    "pattern": rule.pattern,
                    "replacement": rule.replacement,
                    "flags": rule.flags,
                }
            )
        operation_ids = tuple(
            derive_id(
                "op",
                {
                    "source_id": source_id,
                    "rule": rule.name,
                    "rule_index": rule_index,
                    "edit_index": edit_index,
                    "start": edit.start,
                    "end": edit.end,
                    "expected_sha256": sha256_digest(before[edit.start : edit.end]),
                    "replacement": edit.replacement,
                    "replacement_sha256": sha256_digest(edit.replacement),
                },
            )
            for edit_index, edit in enumerate(applied_edits)
        )
        record = TransformRecord(
            rule=rule.name,
            params=params,
            block_index=-1,
            edits=len(applied_edits),
            bytes_removed=max(
                0, len(before.encode("utf-8")) - len(after.encode("utf-8"))
            ),
            warned=warned,
            source_id=source_id,
            chars_removed=max(0, len(before) - len(after)),
            operation_ids=operation_ids,
            input_sha256=sha256_digest(before),
            output_sha256=sha256_digest(after),
            rule_index=rule_index,
        )
        records.append(replace(record, id=derive_transform_record_id(record)))
        if warned:
            warnings.append(
                f"rule '{rule.name}' skipped: would remove "
                f"{candidate_removed}/{len(before)} chars"
            )
        else:
            current = result.text
    return current, records, warnings


def clean_document(
    doc: Document, rules: list[Rule], *, max_remove_frac: float = 0.3
) -> tuple[Document, list[TransformRecord], list[str]]:
    """Plan and replay cleaning through the structure-preserving engine.

    This compatibility entry point intentionally delegates to the same plan
    used by preview and workspace application.
    """
    try:
        validate_id(doc.source_id, kind="src")
    except ValueError as exc:
        raise RuleError("document cleaning requires a valid source identity") from exc

    from veriformis.rules.cleaning import plan_cleaning

    preview = plan_cleaning(doc, rules, max_remove_frac=max_remove_frac)
    return preview.document, list(preview.records), list(preview.warnings)
