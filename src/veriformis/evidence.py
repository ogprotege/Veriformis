"""Immutable source ranges and replayable text evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Mapping, TYPE_CHECKING

from veriformis.errors import EvidenceError
from veriformis.identity import (
    canonical_digest, derive_id, sha256_digest, validate_id, validate_sha256,
)

if TYPE_CHECKING:
    from veriformis.sources import SourceRef


SOURCE_EVIDENCE_SCHEMA_VERSION = "veriformis.source-evidence/v1"


@dataclass(frozen=True)
class SourceRange:
    source_id: str
    artifact_id: str
    region_id: str
    start: int
    end: int
    text_sha256: str
    range_kind: Literal["text", "anchor"] = "text"


@dataclass(frozen=True)
class EvidenceEdit:
    start: int
    end: int
    expected: str
    replacement: str


@dataclass(frozen=True)
class DerivationStep:
    derivation_id: str
    kind: Literal["edits", "slice", "join"]
    input_sha256: str
    output_sha256: str
    edits: tuple[EvidenceEdit, ...] = ()
    start: int | None = None
    end: int | None = None
    separator: str | None = None
    component_lengths: tuple[int, ...] = ()
    context_digest: str = ""


@dataclass(frozen=True)
class EvidenceComponent:
    source_range: SourceRange
    derivations: tuple[DerivationStep, ...] = ()


@dataclass(frozen=True)
class SourceEvidence:
    schema_version: str
    evidence_id: str
    source_id: str
    components: tuple[EvidenceComponent, ...]
    join_derivation: DerivationStep | None
    derivations: tuple[DerivationStep, ...]
    output_sha256: str
    context_digest: str


def source_range(
    source: SourceRef,
    start: int,
    end: int,
    *,
    region_id: str = "body",
) -> SourceRange:
    stream = source.extracted_text
    if not (0 <= start <= end <= len(stream)):
        raise EvidenceError("source range is out of bounds")
    _validate_region_id(region_id)
    kind: Literal["text", "anchor"] = "text" if start < end else "anchor"
    return SourceRange(
        source_id=source.id,
        artifact_id=source.artifact_id,
        region_id=region_id,
        start=start,
        end=end,
        text_sha256=sha256_digest(stream[start:end]),
        range_kind=kind,
    )


def edits_derivation(
    input_text: str,
    edits: tuple[EvidenceEdit, ...] | list[EvidenceEdit],
    *,
    context: dict,
) -> DerivationStep:
    normalized = tuple(edits)
    output = _apply_edits(input_text, normalized)
    payload = {
        "kind": "edits",
        "input_sha256": sha256_digest(input_text),
        "output_sha256": sha256_digest(output),
        "edits": [asdict(edit) for edit in normalized],
        "context_digest": canonical_digest(context),
    }
    return DerivationStep(
        derivation_id=derive_id("drv", payload),
        kind="edits",
        input_sha256=payload["input_sha256"],
        output_sha256=payload["output_sha256"],
        edits=normalized,
        context_digest=payload["context_digest"],
    )


def slice_derivation(input_text: str, start: int, end: int, *, context: dict) -> DerivationStep:
    if not (0 <= start <= end <= len(input_text)):
        raise EvidenceError("derived slice is out of bounds")
    output = input_text[start:end]
    payload = {
        "kind": "slice",
        "input_sha256": sha256_digest(input_text),
        "output_sha256": sha256_digest(output),
        "start": start,
        "end": end,
        "context_digest": canonical_digest(context),
    }
    return DerivationStep(
        derivation_id=derive_id("drv", payload),
        kind="slice",
        input_sha256=payload["input_sha256"],
        output_sha256=payload["output_sha256"],
        start=start,
        end=end,
        context_digest=payload["context_digest"],
    )


def join_derivation(parts: list[str], separator: str, *, context: dict) -> DerivationStep:
    raw = "".join(parts)
    output = separator.join(parts)
    payload = {
        "kind": "join",
        "input_sha256": sha256_digest(raw),
        "output_sha256": sha256_digest(output),
        "separator": separator,
        "component_lengths": [len(part) for part in parts],
        "context_digest": canonical_digest(context),
    }
    return DerivationStep(
        derivation_id=derive_id("drv", payload),
        kind="join",
        input_sha256=payload["input_sha256"],
        output_sha256=payload["output_sha256"],
        separator=separator,
        component_lengths=tuple(payload["component_lengths"]),
        context_digest=payload["context_digest"],
    )


def make_evidence(
    *,
    source_id: str,
    components: list[EvidenceComponent] | tuple[EvidenceComponent, ...],
    output_text: str,
    join: DerivationStep | None = None,
    derivations: tuple[DerivationStep, ...] = (),
    context: dict,
) -> SourceEvidence:
    normalized = tuple(components)
    if not normalized:
        raise EvidenceError("source evidence requires at least one component")
    if any(component.source_range.source_id != source_id for component in normalized):
        raise EvidenceError("evidence crosses source identities")
    if len(normalized) > 1 and join is None:
        raise EvidenceError("multiple evidence components require a join derivation")
    if len(normalized) == 1 and join is not None:
        raise EvidenceError("one evidence component cannot have a join derivation")
    payload = {
        "schema_version": SOURCE_EVIDENCE_SCHEMA_VERSION,
        "source_id": source_id,
        "components": [asdict(component) for component in normalized],
        "join_derivation": asdict(join) if join else None,
        "derivations": [asdict(step) for step in derivations],
        "output_sha256": sha256_digest(output_text),
        "context_digest": canonical_digest(context),
    }
    evidence = SourceEvidence(
        schema_version=payload["schema_version"],
        evidence_id=derive_id("evd", payload),
        source_id=source_id,
        components=normalized,
        join_derivation=join,
        derivations=derivations,
        output_sha256=payload["output_sha256"],
        context_digest=payload["context_digest"],
    )
    _validate_evidence_shape(evidence, strict_source_ids=True)
    _verify_evidence_identity(evidence)
    return evidence


def resolve_evidence(evidence: SourceEvidence, sources: Mapping[str, SourceRef]) -> str:
    _validate_evidence_shape(evidence, strict_source_ids=True)
    values: list[str] = []
    for component in evidence.components:
        item = component.source_range
        source = sources.get(item.source_id)
        if source is None:
            raise EvidenceError(f"unregistered source {item.source_id!r}")
        if item.source_id != evidence.source_id:
            raise EvidenceError("evidence crosses source identities")
        if source.artifact_id != item.artifact_id:
            raise EvidenceError("source artifact identity mismatch")
        if sha256_digest(source.extracted_text) != source.stream_sha256:
            raise EvidenceError("source artifact content digest mismatch")
        if not (0 <= item.start <= item.end <= len(source.extracted_text)):
            raise EvidenceError("source range is out of bounds")
        value = source.extracted_text[item.start:item.end]
        if sha256_digest(value) != item.text_sha256:
            raise EvidenceError("source range digest mismatch")
        value = replay_derivations(value, component.derivations)
        values.append(value)

    if evidence.join_derivation is not None:
        value = _apply_join(values, evidence.join_derivation)
    elif len(values) == 1:
        value = values[0]
    else:
        raise EvidenceError("multiple components require a join derivation")

    value = replay_derivations(value, evidence.derivations)
    if sha256_digest(value) != evidence.output_sha256:
        raise EvidenceError("evidence output digest mismatch")
    _verify_evidence_identity(evidence)
    return value


def _verify_evidence_identity(evidence: SourceEvidence) -> None:
    if evidence.schema_version != SOURCE_EVIDENCE_SCHEMA_VERSION:
        raise EvidenceError(f"unsupported source evidence schema {evidence.schema_version!r}")
    expected_id = derive_id(
        "evd",
        {
            "schema_version": evidence.schema_version,
            "source_id": evidence.source_id,
            "components": [asdict(component) for component in evidence.components],
            "join_derivation": asdict(evidence.join_derivation) if evidence.join_derivation else None,
            "derivations": [asdict(step) for step in evidence.derivations],
            "output_sha256": evidence.output_sha256,
            "context_digest": evidence.context_digest,
        },
    )
    if expected_id != evidence.evidence_id:
        raise EvidenceError("evidence identity mismatch")


def replay_derivations(value: str, steps: tuple[DerivationStep, ...]) -> str:
    for step in steps:
        value = _apply_step(value, step)
    return value


def _apply_step(value: str, step: DerivationStep) -> str:
    _validate_derivation_shape(step)
    _verify_derivation_identity(step)
    if sha256_digest(value) != step.input_sha256:
        raise EvidenceError(f"derivation {step.derivation_id} input digest mismatch")
    if step.kind == "edits":
        output = _apply_edits(value, step.edits)
    elif step.kind == "slice":
        if step.start is None or step.end is None or not (0 <= step.start <= step.end <= len(value)):
            raise EvidenceError(f"derivation {step.derivation_id} has invalid slice")
        output = value[step.start:step.end]
    else:
        raise EvidenceError(f"derivation {step.derivation_id} is invalid in this position")
    if sha256_digest(output) != step.output_sha256:
        raise EvidenceError(f"derivation {step.derivation_id} output digest mismatch")
    return output


def _apply_join(values: list[str], step: DerivationStep) -> str:
    _validate_derivation_shape(step)
    _verify_derivation_identity(step)
    if step.kind != "join" or step.separator is None:
        raise EvidenceError("invalid join derivation")
    if tuple(len(value) for value in values) != step.component_lengths:
        raise EvidenceError("join component lengths mismatch")
    raw = "".join(values)
    if sha256_digest(raw) != step.input_sha256:
        raise EvidenceError("join input digest mismatch")
    output = step.separator.join(values)
    if sha256_digest(output) != step.output_sha256:
        raise EvidenceError("join output digest mismatch")
    return output


def _verify_derivation_identity(step: DerivationStep) -> None:
    payload = {
        "kind": step.kind,
        "input_sha256": step.input_sha256,
        "output_sha256": step.output_sha256,
        "context_digest": step.context_digest,
    }
    if step.kind == "edits":
        payload["edits"] = [asdict(edit) for edit in step.edits]
    elif step.kind == "slice":
        payload["start"] = step.start
        payload["end"] = step.end
    elif step.kind == "join":
        payload["separator"] = step.separator
        payload["component_lengths"] = list(step.component_lengths)
    if derive_id("drv", payload) != step.derivation_id:
        raise EvidenceError("derivation identity mismatch")


def _apply_edits(value: str, edits: tuple[EvidenceEdit, ...]) -> str:
    previous_end = -1
    for edit in sorted(edits, key=lambda item: (item.start, item.end)):
        if edit.start < previous_end or not (0 <= edit.start <= edit.end <= len(value)):
            raise EvidenceError("derivation edits overlap or are out of bounds")
        if value[edit.start:edit.end] != edit.expected:
            raise EvidenceError("derivation edit precondition mismatch")
        previous_end = edit.end
    output = value
    for edit in sorted(edits, key=lambda item: (item.start, item.end), reverse=True):
        output = output[:edit.start] + edit.replacement + output[edit.end:]
    return output


def evidence_digest(evidence: SourceEvidence) -> str:
    return canonical_digest(asdict(evidence))


def derivation_to_dict(step: DerivationStep) -> dict:
    """Serialize one derivation after validating its content-addressed ID."""
    _validate_derivation_shape(step)
    _verify_derivation_identity(step)
    return asdict(step)


def derivation_from_dict(value: dict) -> DerivationStep:
    """Load a derivation from the exact v1 persisted schema."""
    expected = {
        "derivation_id", "kind", "input_sha256", "output_sha256", "edits",
        "start", "end", "separator", "component_lengths", "context_digest",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise EvidenceError("derivation keys do not match the v1 schema")
    edits_value = value["edits"]
    if not isinstance(edits_value, (list, tuple)):
        raise EvidenceError("derivation edits must be a list")
    edits = []
    for item in edits_value:
        if not isinstance(item, dict) \
                or set(item) != {"start", "end", "expected", "replacement"}:
            raise EvidenceError("evidence edit keys do not match the v1 schema")
        edits.append(EvidenceEdit(**item))
    lengths_value = value["component_lengths"]
    if not isinstance(lengths_value, (list, tuple)):
        raise EvidenceError("derivation component_lengths must be a list")
    data = dict(value)
    data["edits"] = tuple(edits)
    data["component_lengths"] = tuple(lengths_value)
    try:
        step = DerivationStep(**data)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid derivation: {exc}") from exc
    _validate_derivation_shape(step)
    _verify_derivation_identity(step)
    return step


def source_evidence_to_dict(evidence: SourceEvidence) -> dict:
    _validate_evidence_shape(evidence, strict_source_ids=True)
    _verify_evidence_identity(evidence)
    return asdict(evidence)


def source_evidence_from_dict(value: dict) -> SourceEvidence:
    """Load strict nested evidence emitted by ``dataclasses.asdict``."""
    expected = {
        "schema_version", "evidence_id", "source_id", "components",
        "join_derivation", "derivations", "output_sha256", "context_digest",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise EvidenceError("source evidence keys do not match the v1 schema")
    if value["schema_version"] != SOURCE_EVIDENCE_SCHEMA_VERSION:
        raise EvidenceError(f"unsupported source evidence schema {value['schema_version']!r}")
    components_value = value["components"]
    if not isinstance(components_value, (list, tuple)):
        raise EvidenceError("source evidence components must be a list")
    if not components_value:
        raise EvidenceError("source evidence requires at least one component")
    components_list = []
    range_fields = {
        "source_id", "artifact_id", "region_id", "start", "end",
        "text_sha256", "range_kind",
    }
    for item in components_value:
        if not isinstance(item, dict) or set(item) != {"source_range", "derivations"}:
            raise EvidenceError("evidence component keys do not match the v1 schema")
        range_value = item["source_range"]
        if not isinstance(range_value, dict) or set(range_value) != range_fields:
            raise EvidenceError("source range keys do not match the v1 schema")
        derivations_value = item["derivations"]
        if not isinstance(derivations_value, (list, tuple)):
            raise EvidenceError("component derivations must be a list")
        try:
            source_item = SourceRange(**range_value)
            component = EvidenceComponent(
                source_range=source_item,
                derivations=tuple(derivation_from_dict(step) for step in derivations_value),
            )
        except (TypeError, ValueError) as exc:
            raise EvidenceError(f"invalid evidence component: {exc}") from exc
        components_list.append(component)
    components = tuple(components_list)
    join_value = value["join_derivation"]
    if join_value is not None and not isinstance(join_value, dict):
        raise EvidenceError("join_derivation must be an object or null")
    derivations_value = value["derivations"]
    if not isinstance(derivations_value, (list, tuple)):
        raise EvidenceError("evidence derivations must be a list")
    try:
        evidence = SourceEvidence(
            schema_version=value["schema_version"],
            evidence_id=value["evidence_id"],
            source_id=value["source_id"],
            components=components,
            join_derivation=(
                derivation_from_dict(join_value) if join_value is not None else None
            ),
            derivations=tuple(derivation_from_dict(step) for step in derivations_value),
            output_sha256=value["output_sha256"],
            context_digest=value["context_digest"],
        )
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid source evidence: {exc}") from exc
    _validate_evidence_shape(evidence, strict_source_ids=True)
    _verify_evidence_identity(evidence)
    return evidence


def _validate_derivation_shape(step: DerivationStep) -> None:
    if not isinstance(step, DerivationStep):
        raise EvidenceError("derivation must use the v1 derivation model")
    _require_id(step.derivation_id, "drv", "derivation_id")
    _require_digest(step.input_sha256, "derivation input_sha256")
    _require_digest(step.output_sha256, "derivation output_sha256")
    _require_digest(step.context_digest, "derivation context_digest")
    if not isinstance(step.edits, tuple) or not isinstance(step.component_lengths, tuple):
        raise EvidenceError("derivation sequence fields must be tuples")
    if step.kind == "edits":
        if step.start is not None or step.end is not None or step.separator is not None \
                or step.component_lengths:
            raise EvidenceError("edit derivation contains fields for another derivation kind")
        previous_end = -1
        for edit in step.edits:
            if not isinstance(edit, EvidenceEdit):
                raise EvidenceError("edit derivation contains an invalid edit")
            if type(edit.start) is not int or type(edit.end) is not int \
                    or not (0 <= edit.start <= edit.end) or edit.start < previous_end:
                raise EvidenceError("derivation edits overlap, are unordered, or have invalid ranges")
            if not isinstance(edit.expected, str) or not isinstance(edit.replacement, str):
                raise EvidenceError("derivation edit text must be strings")
            previous_end = edit.end
    elif step.kind == "slice":
        if step.edits or step.start is None or step.end is None or step.separator is not None \
                or step.component_lengths:
            raise EvidenceError("slice derivation has an invalid shape")
        if type(step.start) is not int or type(step.end) is not int \
                or not (0 <= step.start <= step.end):
            raise EvidenceError("slice derivation has an invalid range")
    elif step.kind == "join":
        if step.edits or step.start is not None or step.end is not None or step.separator is None:
            raise EvidenceError("join derivation has an invalid shape")
        if not isinstance(step.separator, str) \
                or not step.component_lengths \
                or not all(type(length) is int and length >= 0 for length in step.component_lengths):
            raise EvidenceError("join derivation has invalid component metadata")
    else:
        raise EvidenceError(f"unsupported derivation kind: {step.kind!r}")


def _validate_evidence_shape(
    evidence: SourceEvidence,
    *,
    strict_source_ids: bool,
) -> None:
    if not isinstance(evidence, SourceEvidence):
        raise EvidenceError("source evidence must use the v1 evidence model")
    if evidence.schema_version != SOURCE_EVIDENCE_SCHEMA_VERSION:
        raise EvidenceError(f"unsupported source evidence schema {evidence.schema_version!r}")
    _require_id(evidence.evidence_id, "evd", "evidence_id")
    if strict_source_ids:
        _require_id(evidence.source_id, "src", "evidence source_id")
    elif not isinstance(evidence.source_id, str) or not evidence.source_id:
        raise EvidenceError("evidence source_id must be a non-empty string")
    _require_digest(evidence.output_sha256, "evidence output_sha256")
    _require_digest(evidence.context_digest, "evidence context_digest")
    if not isinstance(evidence.components, tuple) or not evidence.components:
        raise EvidenceError("source evidence requires at least one component")

    artifacts: set[str] = set()
    regions: set[str] = set()
    for component in evidence.components:
        if not isinstance(component, EvidenceComponent):
            raise EvidenceError("source evidence contains an invalid component")
        _validate_source_range(
            component.source_range,
            evidence_source_id=evidence.source_id,
            strict_source_ids=strict_source_ids,
        )
        artifacts.add(component.source_range.artifact_id)
        regions.add(component.source_range.region_id)
        if not isinstance(component.derivations, tuple):
            raise EvidenceError("component derivations must be a tuple")
        for step in component.derivations:
            _validate_derivation_shape(step)
            if step.kind == "join":
                raise EvidenceError("component derivations cannot contain a join")
            _verify_derivation_identity(step)
    if len(artifacts) != 1:
        raise EvidenceError("evidence components reference different source artifacts")
    if len(regions) != 1:
        raise EvidenceError("evidence components cross canonical source regions")

    if evidence.join_derivation is None:
        if len(evidence.components) != 1:
            raise EvidenceError("multiple components require a join derivation")
    else:
        if len(evidence.components) == 1:
            raise EvidenceError("one component cannot have a join derivation")
        _validate_derivation_shape(evidence.join_derivation)
        if evidence.join_derivation.kind != "join":
            raise EvidenceError("join_derivation must have kind 'join'")
        if len(evidence.join_derivation.component_lengths) != len(evidence.components):
            raise EvidenceError("join component count does not match evidence components")
        _verify_derivation_identity(evidence.join_derivation)

    if not isinstance(evidence.derivations, tuple):
        raise EvidenceError("evidence derivations must be a tuple")
    for step in evidence.derivations:
        _validate_derivation_shape(step)
        if step.kind == "join":
            raise EvidenceError("final evidence derivations cannot contain a join")
        _verify_derivation_identity(step)


def _validate_source_range(
    item: SourceRange,
    *,
    evidence_source_id: str,
    strict_source_ids: bool,
) -> None:
    if not isinstance(item, SourceRange):
        raise EvidenceError("evidence component has an invalid source range")
    if strict_source_ids:
        _require_id(item.source_id, "src", "source range source_id")
        _require_id(item.artifact_id, "art", "source range artifact_id")
    else:
        if not isinstance(item.source_id, str) or not item.source_id:
            raise EvidenceError("source range source_id must be a non-empty string")
        if not isinstance(item.artifact_id, str) or not item.artifact_id:
            raise EvidenceError("source range artifact_id must be a non-empty string")
    if item.source_id != evidence_source_id:
        raise EvidenceError("evidence crosses source identities")
    _validate_region_id(item.region_id)
    if type(item.start) is not int or type(item.end) is not int \
            or not (0 <= item.start <= item.end):
        raise EvidenceError("source range offsets are invalid")
    if item.range_kind not in ("text", "anchor"):
        raise EvidenceError(f"unsupported source range kind {item.range_kind!r}")
    if item.range_kind == "text" and item.start == item.end:
        raise EvidenceError("text source ranges must not be empty")
    if item.range_kind == "anchor" and item.start != item.end:
        raise EvidenceError("anchor source ranges must be empty")
    _require_digest(item.text_sha256, "source range text_sha256")
    if item.range_kind == "anchor" and item.text_sha256 != sha256_digest(""):
        raise EvidenceError("anchor source range digest must represent empty text")


def _require_id(value: str, kind: str, field_name: str) -> None:
    try:
        validate_id(value, kind=kind)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid {field_name}: {exc}") from exc


def _require_digest(value: str, field_name: str) -> None:
    try:
        validate_sha256(value)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid {field_name}: {exc}") from exc


def _validate_region_id(value: str) -> None:
    if value == "body":
        return
    if not isinstance(value, str):
        raise EvidenceError("source range region_id must be a string")
    prefix, separator, note_id = value.partition(":")
    if separator != ":" or prefix not in ("footnote", "endnote") or not note_id:
        raise EvidenceError(f"unsupported source range region_id {value!r}")
    if any(ord(character) < 32 or ord(character) == 127 for character in note_id):
        raise EvidenceError("source range note region contains control characters")
