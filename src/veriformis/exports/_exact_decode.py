"""Decode exact export payloads before asserting source membership.

The decoder consumes emitted bytes, never the renderer's input rows. Profile
prompt assembly uses the source instruction length only to recover the known
field boundary; it is not a standalone import or a trainer round-trip claim.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from veriformis.datasets import ProductRow, RowSet, row_provenance_from_json_bytes
from veriformis.errors import ExportVerificationError
from veriformis.exports._implementation import _RenderedDerivative
from veriformis.exports._json import canonical_export_object_from_bytes
from veriformis.exports.models import ExportPlan
from veriformis.identity import lossless_json_bytes


def _jsonl(data: bytes) -> tuple[dict[str, Any], ...]:
    if not data:
        return ()
    if not data.endswith(b"\n"):
        raise ExportVerificationError("emitted JSONL requires a final LF")
    return tuple(
        canonical_export_object_from_bytes(line, label="emitted JSONL row")
        for line in data[:-1].split(b"\n")
    )


def _provenance(value: Mapping[str, Any]):
    raw = lossless_json_bytes(value)
    if value.get("schema_version") == "veriformis.imported-row-provenance/v1":
        from veriformis.mapping.finish import ImportedRowProvenance

        return ImportedRowProvenance.model_validate_json(raw)
    return row_provenance_from_json_bytes(raw)


def _inverse_payload(
    value: dict[str, Any], source: ProductRow, mapping: Any | None,
) -> dict[str, Any]:
    if mapping is None:
        return value
    if tuple(sorted(value)) != mapping.destination_keys:
        raise ExportVerificationError("decoded profile keys differ from the admission pin")
    kind = mapping.mapping_kind
    if kind == "identity":
        return value
    if kind == "assemble-prompt":
        prompt = value["prompt"]
        if not isinstance(prompt, str):
            raise ExportVerificationError("decoded profile prompt must be text")
        boundary = len(source.payload["instruction"])
        if source.payload["input"]:
            if prompt[boundary:boundary + 1] != "\n":
                raise ExportVerificationError("decoded profile prompt lost its field boundary")
            context = prompt[boundary + 1:]
        else:
            if len(prompt) != boundary:
                raise ExportVerificationError("decoded profile prompt changed its empty input")
            context = ""
        return {"instruction": prompt[:boundary], "input": context, "output": value["completion"]}
    if kind == "remap" and source.row_schema == "prompt_completion":
        if value["input"] != "":
            raise ExportVerificationError("decoded profile added an input field value")
        return {"prompt": value["instruction"], "completion": value["output"]}
    if kind == "remap" and source.row_schema == "messages":
        turns = value["conversations"]
        if (
            not isinstance(turns, list) or len(turns) != 2
            or any(not isinstance(turn, dict) or set(turn) != {"from", "value"} for turn in turns)
            or [turn["from"] for turn in turns] != ["human", "gpt"]
        ):
            raise ExportVerificationError("decoded profile conversation changed roles or shape")
        return {"messages": [
            {"role": "user", "content": turns[0]["value"]},
            {"role": "assistant", "content": turns[1]["value"]},
        ]}
    raise ExportVerificationError("profile has no independent payload decoder")


def decode_exact_derivative(
    plan: ExportPlan,
    source: RowSet,
    files: tuple[tuple[str, bytes], ...],
    *,
    mapping: Any | None = None,
) -> _RenderedDerivative:
    """Recover fresh candidate rows and available provenance from output bytes."""
    by_path = dict(files)
    if len(by_path) != len(files):
        raise ExportVerificationError("emitted export repeats a file path")
    paths = {
        item.role: item.path for item in plan.file_plans
        if item.role in {"dataset", "training-partition", "evaluation-partition", "row-provenance"}
    }
    try:
        container = plan.container_profile.container_id
        if container == "json":
            from veriformis.exports.canonical_json import CanonicalJsonDataset, CanonicalJsonProvenance

            dataset = CanonicalJsonDataset.from_json_bytes(by_path[paths["dataset"]])
            metadata = CanonicalJsonProvenance.from_json_bytes(by_path[paths["row-provenance"]])
            dataset.validate_provenance(metadata)
            train, evaluation = dataset.splits.train, dataset.splits.evaluation
            provenance = metadata.rows
        else:
            if container == "constrained-csv":
                from veriformis.exports.constrained_csv import ConstrainedCsvPartition

                def decode(data: bytes):
                    return ConstrainedCsvPartition.from_csv_bytes(data, row_schema=source.row_schema).payloads
            elif container == "split-jsonl-directory":
                decode = _jsonl
            else:
                raise ExportVerificationError("container has no independent exact decoder")
            train = decode(by_path[paths["training-partition"]])
            evaluation = (
                decode(by_path[paths["evaluation-partition"]])
                if "evaluation-partition" in paths else ()
            )
            # A configured split-JSONL pack may omit provenance. In that case
            # source identities remain the trusted alignment, not emitted data.
            provenance = (
                tuple(_provenance(value) for value in _jsonl(by_path[paths["row-provenance"]]))
                if "row-provenance" in paths
                else tuple(_provenance(item.model_dump(mode="json")) for item in source.provenance)
            )
        if len(train) != len(source.train_rows) or len(evaluation) != len(source.evaluation_rows):
            raise ExportVerificationError("decoded export partition counts differ from the source")
        if len(provenance) != len(train) + len(evaluation):
            raise ExportVerificationError("decoded export provenance count differs from its rows")
        rows = []
        for ordinal, (payload, original, binding) in enumerate(zip(
            (*train, *evaluation), (*source.train_rows, *source.evaluation_rows), provenance, strict=True,
        )):
            partition = "train" if ordinal < len(train) else "evaluation"
            local_ordinal = ordinal if partition == "train" else ordinal - len(train)
            if binding.partition != partition or binding.ordinal != local_ordinal:
                raise ExportVerificationError("decoded export provenance is not partition-aligned")
            candidate = ProductRow.create(
                record_id=binding.record_id,
                row_schema=source.row_schema,
                payload=_inverse_payload(dict(payload), original, mapping),
            )
            if candidate.row_id != binding.row_id or candidate.payload_sha256 != binding.payload_sha256:
                raise ExportVerificationError("decoded export payload differs from its provenance")
            rows.append(candidate)
    except ExportVerificationError:
        raise
    except (KeyError, TypeError, ValueError, UnicodeError) as exc:
        raise ExportVerificationError(f"cannot decode exact export: {exc}") from exc
    return _RenderedDerivative(
        files=files,
        train_rows=tuple(rows[:len(train)]),
        evaluation_rows=tuple(rows[len(train):]),
        provenance=tuple(provenance),
    )
