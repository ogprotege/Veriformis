"""Independent verification for deterministic finished bundles."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Literal

from veriformis.bundle.finished import (
    ATTESTATION_NAME,
    MANIFEST_NAME,
    BundleAttestation,
    BundleFile,
    BundleVerificationError,
    EVALUATION_PATH,
    FinishedBundleError,
    FinishedBundleManifest,
    PROVENANCE_PATH,
    TRAIN_PATH,
    VALIDATION_PATH,
    VerificationResult,
    _canonical_json_object_from_bytes,
    _portable_path_key,
    _require_passing_validation_report,
    _uses_jsonl_contract,
    _validate_path_syntax,
)
from veriformis.errors import VeriformisError
from veriformis.datasets.serialization import RowSet
from veriformis.datasets.validation import DatasetValidationReport
from veriformis.identity import (
    canonical_digest,
    lossless_json_bytes,
    sha256_digest,
    validate_sha256,
)

_MAX_METADATA_BYTES = 16 * 1024 * 1024
_MAX_JSONL_RECORD_BYTES = 64 * 1024 * 1024
_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_FILE_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)

_EntryFacts = tuple[int, int, int, int, int, int, int]


@dataclass(frozen=True, slots=True)
class VerifiedFinishedBundle:
    """Immutable semantic state reconstructed during one verified bundle read."""

    bundle_path: Path
    manifest: FinishedBundleManifest
    validation_report: DatasetValidationReport
    row_set: RowSet
    verification: VerificationResult


def _stable_entry_facts(status: os.stat_result) -> _EntryFacts:
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
        status.st_nlink,
    )


def _open_root(path: Path) -> int:
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise BundleVerificationError(
            f"cannot inspect finished bundle root {path}: {exc}"
        ) from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise BundleVerificationError(
            "finished bundle root must be a real directory, not a symlink"
        )
    try:
        descriptor = os.open(path, _DIRECTORY_FLAGS)
    except OSError as exc:
        raise BundleVerificationError(
            f"cannot open finished bundle root {path}: {exc}"
        ) from exc
    after = os.fstat(descriptor)
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        os.close(descriptor)
        raise BundleVerificationError("finished bundle root changed while opening")
    return descriptor


def _register_portable_path(
    paths: dict[str, str],
    relative_path: str,
) -> None:
    try:
        _validate_path_syntax(relative_path)
    except ValueError as exc:
        raise BundleVerificationError(
            f"unsafe path in finished bundle: {relative_path!r}: {exc}"
        ) from exc
    key = _portable_path_key(relative_path)
    previous = paths.get(key)
    if previous is not None and previous != relative_path:
        raise BundleVerificationError(
            f"finished bundle paths collide by case or Unicode: "
            f"{previous!r} and {relative_path!r}"
        )
    paths[key] = relative_path


def _collect_tree(
    root_descriptor: int,
) -> tuple[dict[str, _EntryFacts], dict[str, _EntryFacts]]:
    files: dict[str, _EntryFacts] = {}
    directories: dict[str, _EntryFacts] = {}
    portable_paths: dict[str, str] = {}
    file_inodes: dict[tuple[int, int], str] = {}

    def visit(directory_descriptor: int, prefix: str) -> None:
        try:
            names = sorted(os.listdir(directory_descriptor))
        except OSError as exc:
            raise BundleVerificationError(
                f"cannot enumerate finished bundle directory {prefix or '.'}: {exc}"
            ) from exc
        for name in names:
            relative_path = f"{prefix}/{name}" if prefix else name
            _register_portable_path(portable_paths, relative_path)
            try:
                status = os.stat(
                    name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            except OSError as exc:
                raise BundleVerificationError(
                    f"cannot inspect bundle entry {relative_path!r}: {exc}"
                ) from exc
            if stat.S_ISLNK(status.st_mode):
                raise BundleVerificationError(
                    f"finished bundle cannot contain symlink {relative_path!r}"
                )
            if stat.S_ISDIR(status.st_mode):
                directories[relative_path] = _stable_entry_facts(status)
                try:
                    child_descriptor = os.open(
                        name,
                        _DIRECTORY_FLAGS,
                        dir_fd=directory_descriptor,
                    )
                except OSError as exc:
                    raise BundleVerificationError(
                        f"cannot safely open bundle directory {relative_path!r}: {exc}"
                    ) from exc
                try:
                    opened = os.fstat(child_descriptor)
                    if (status.st_dev, status.st_ino) != (
                        opened.st_dev,
                        opened.st_ino,
                    ):
                        raise BundleVerificationError(
                            f"bundle directory {relative_path!r} changed while opening"
                        )
                    visit(child_descriptor, relative_path)
                finally:
                    os.close(child_descriptor)
                continue
            if stat.S_ISREG(status.st_mode):
                if status.st_nlink != 1:
                    raise BundleVerificationError(
                        f"finished bundle cannot contain hard-linked file "
                        f"{relative_path!r}"
                    )
                inode = (status.st_dev, status.st_ino)
                previous = file_inodes.get(inode)
                if previous is not None:
                    raise BundleVerificationError(
                        f"finished bundle files share one inode: "
                        f"{previous!r} and {relative_path!r}"
                    )
                file_inodes[inode] = relative_path
                files[relative_path] = _stable_entry_facts(status)
                continue
            raise BundleVerificationError(
                f"finished bundle contains special file {relative_path!r}"
            )

    visit(root_descriptor, "")
    return files, directories


def _open_regular_file(
    root_descriptor: int,
    relative_path: str,
    *,
    expected_facts: _EntryFacts,
) -> int:
    parts = relative_path.split("/")
    current = os.dup(root_descriptor)
    try:
        for part in parts[:-1]:
            child = os.open(part, _DIRECTORY_FLAGS, dir_fd=current)
            os.close(current)
            current = child
        descriptor = os.open(parts[-1], _FILE_FLAGS, dir_fd=current)
    except OSError as exc:
        raise BundleVerificationError(
            f"cannot safely open bundle file {relative_path!r}: {exc}"
        ) from exc
    finally:
        os.close(current)
    status = os.fstat(descriptor)
    if not stat.S_ISREG(status.st_mode):
        os.close(descriptor)
        raise BundleVerificationError(
            f"finished bundle entry {relative_path!r} is not a regular file"
        )
    if status.st_nlink != 1:
        os.close(descriptor)
        raise BundleVerificationError(
            f"finished bundle cannot contain hard-linked file {relative_path!r}"
        )
    if _stable_entry_facts(status) != expected_facts:
        os.close(descriptor)
        raise BundleVerificationError(
            f"bundle file changed between enumeration and open: {relative_path!r}"
        )
    return descriptor


def _read_metadata(
    root_descriptor: int,
    relative_path: str,
    *,
    expected_facts: _EntryFacts,
) -> bytes:
    descriptor = _open_regular_file(
        root_descriptor,
        relative_path,
        expected_facts=expected_facts,
    )
    try:
        before = os.fstat(descriptor)
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read(_MAX_METADATA_BYTES + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if _stable_entry_facts(before) != _stable_entry_facts(after):
        raise BundleVerificationError(
            f"bundle metadata changed during verification: {relative_path!r}"
        )
    if len(data) > _MAX_METADATA_BYTES:
        raise BundleVerificationError(f"{relative_path} exceeds the metadata limit")
    return data


def _expected_directories(files: tuple[BundleFile, ...]) -> set[str]:
    directories: set[str] = set()
    for file in files:
        parts = file.path.split("/")
        for index in range(1, len(parts)):
            directories.add("/".join(parts[:index]))
    return directories


def _verify_payload(
    root_descriptor: int,
    file: BundleFile,
    *,
    expected_facts: _EntryFacts,
) -> None:
    descriptor = _open_regular_file(
        root_descriptor,
        file.path,
        expected_facts=expected_facts,
    )
    try:
        before = os.fstat(descriptor)
        if before.st_size != file.size:
            raise BundleVerificationError(
                f"bundle file size mismatch for {file.path!r}"
            )

        digest = hashlib.sha256()
        observed_records: int | None = None
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            if _uses_jsonl_contract(
                path=file.path,
                media_type=file.media_type,
                record_count=file.record_count,
            ):
                observed_records = 0
                while True:
                    line = handle.readline(_MAX_JSONL_RECORD_BYTES + 1)
                    if not line:
                        break
                    if len(line) > _MAX_JSONL_RECORD_BYTES:
                        raise BundleVerificationError(
                            f"JSONL record exceeds limit in {file.path!r}"
                        )
                    digest.update(line)
                    if not line.endswith(b"\n"):
                        raise BundleVerificationError(
                            f"JSONL payload {file.path!r} must end every record with LF"
                        )
                    record = line[:-1]
                    if not record:
                        raise BundleVerificationError(
                            f"JSONL payload {file.path!r} contains a blank record"
                        )
                    _canonical_json_object_from_bytes(
                        record,
                        label=f"{file.path} record {observed_records + 1}",
                    )
                    observed_records += 1
            else:
                while True:
                    block = handle.read(1024 * 1024)
                    if not block:
                        break
                    digest.update(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)

    if _stable_entry_facts(before) != _stable_entry_facts(after):
        raise BundleVerificationError(
            f"bundle file changed during verification: {file.path!r}"
        )
    if digest.hexdigest() != file.sha256:
        raise BundleVerificationError(f"bundle file digest mismatch for {file.path!r}")
    if observed_records is not None and observed_records != file.record_count:
        raise BundleVerificationError(
            f"bundle record count mismatch for {file.path!r}: "
            f"declared {file.record_count}, found {observed_records}"
        )


def _verify_attestation_binding(
    *,
    manifest: FinishedBundleManifest,
    manifest_sha256: str,
    attestation: BundleAttestation,
) -> None:
    expected = {
        "bundle_id": manifest.bundle_id,
        "dataset_snapshot_id": manifest.dataset_snapshot_id,
        "validation_report_id": manifest.validation_report_id,
        "manifest_sha256": manifest_sha256,
        "content_root_sha256": manifest.content_root_sha256,
    }
    actual = {
        "bundle_id": attestation.bundle_id,
        "dataset_snapshot_id": attestation.dataset_snapshot_id,
        "validation_report_id": attestation.validation_report_id,
        "manifest_sha256": attestation.manifest_sha256,
        "content_root_sha256": attestation.content_root_sha256,
    }
    if actual != expected:
        raise BundleVerificationError(
            "bundle attestation does not bind the exact manifest and content root"
        )


def _read_jsonl_object(
    handle: BinaryIO,
    *,
    path: str,
    ordinal: int,
) -> dict[str, Any] | None:
    line = handle.readline(_MAX_JSONL_RECORD_BYTES + 1)
    if not line:
        return None
    if len(line) > _MAX_JSONL_RECORD_BYTES:
        raise BundleVerificationError(f"JSONL record exceeds limit in {path!r}")
    if not line.endswith(b"\n"):
        raise BundleVerificationError(
            f"JSONL payload {path!r} must end every record with LF"
        )
    if line == b"\n":
        raise BundleVerificationError(f"JSONL payload {path!r} contains a blank record")
    return _canonical_json_object_from_bytes(
        line[:-1],
        label=f"{path} record {ordinal + 1}",
    )


def _row_contract(
    payload: dict[str, Any],
    provenance: Any,
) -> tuple[Any, str, str]:
    from veriformis.construction import TrainingObjective
    from veriformis.datasets.serialization import ProductRow, SerializationPlan

    field_names = tuple(field.name for field in provenance.record_fields)
    objective_by_fields = {
        ("text",): "full_text",
        ("prompt", "completion"): "continuation",
        ("heading", "section"): "section_reconstruction",
        ("before", "after"): "before_after_transformation",
        ("input", "fields"): "structured_field",
    }
    objective_kind = objective_by_fields.get(field_names)
    if objective_kind is None:
        raise BundleVerificationError(
            "row provenance fields do not name one exact v1 objective"
        )
    objective = TrainingObjective.create(objective_kind)
    if provenance.objective_id != objective.objective_id:
        raise BundleVerificationError(
            "row provenance objective does not match its record fields"
        )

    values = {field.name: field.value for field in provenance.record_fields}
    keys = set(payload)
    instruction_text: str | None = None
    if keys == {"text"}:
        row_schema = "text"
        expected_payload = {"text": values.get("text")}
    elif keys == {"prompt", "completion"}:
        row_schema = "prompt_completion"
        context_name, target_name = field_names
        expected_payload = {
            "prompt": values[context_name],
            "completion": values[target_name],
        }
    elif keys == {"instruction", "input", "output"}:
        row_schema = "instruction_output"
        context_name, target_name = field_names
        instruction_text = payload.get("instruction")
        expected_payload = {
            "instruction": instruction_text,
            "input": values[context_name],
            "output": values[target_name],
        }
    elif keys == {"messages"}:
        row_schema = "messages"
        context_name, target_name = field_names
        expected_payload = {
            "messages": [
                {"role": "user", "content": values[context_name]},
                {"role": "assistant", "content": values[target_name]},
            ]
        }
    else:
        raise BundleVerificationError(
            "dataset payload does not match one exact v1 row schema"
        )
    if objective_kind == "full_text" and row_schema != "text":
        raise BundleVerificationError("full_text provenance requires a text row")
    if objective_kind != "full_text" and row_schema == "text":
        raise BundleVerificationError(
            "supervised provenance cannot bind a full-text row"
        )
    if payload != expected_payload:
        raise BundleVerificationError(
            "dataset payload does not match its exact provenance field values"
        )

    try:
        serialization_plan = SerializationPlan.create(
            row_schema=row_schema,
            instruction_text=instruction_text,
        )
        row = ProductRow.create(
            record_id=provenance.record_id,
            row_schema=row_schema,
            payload=payload,
        )
    except (RecursionError, TypeError, UnicodeError, ValueError, VeriformisError) as exc:
        raise BundleVerificationError(f"invalid product row contract: {exc}") from exc
    if provenance.serialization_plan_id != serialization_plan.serialization_plan_id:
        raise BundleVerificationError(
            "row provenance serialization plan does not match its payload"
        )
    return row, row_schema, objective_kind


IMPORTED_BUNDLE_ROW_SET_SCHEMA = "veriformis.imported-bundle-row-set/v1"


@dataclass(frozen=True, slots=True)
class ImportedBundleRowSet:
    """Product rows reconstructed from an imported finished bundle."""

    row_schema: str
    train_rows: tuple[Any, ...]
    evaluation_rows: tuple[Any, ...]
    provenance: tuple[Any, ...]
    row_set_id: str
    split_result_id: str
    plan_id: str
    recipe_id: str
    mapping_result_id: str
    construction_result_id: str
    curation_result_id: str
    serialization_plan_id: str
    train_jsonl_sha256: str
    train_jsonl_byte_size: int
    evaluation_jsonl_sha256: str
    evaluation_jsonl_byte_size: int
    provenance_jsonl_sha256: str
    provenance_jsonl_byte_size: int
    train_row_count: int
    evaluation_row_count: int
    total_row_count: int

    def model_dump(self, *, mode: str = "json") -> dict[str, Any]:
        return {
            "schema_version": IMPORTED_BUNDLE_ROW_SET_SCHEMA,
            "row_schema": self.row_schema,
            "train_rows": [row.model_dump(mode=mode) for row in self.train_rows],
            "evaluation_rows": [
                row.model_dump(mode=mode) for row in self.evaluation_rows
            ],
            "provenance": [item.model_dump(mode=mode) for item in self.provenance],
            "row_set_id": self.row_set_id,
            "split_result_id": self.split_result_id,
            "plan_id": self.plan_id,
            "recipe_id": self.recipe_id,
            "mapping_result_id": self.mapping_result_id,
            "construction_result_id": self.construction_result_id,
            "curation_result_id": self.curation_result_id,
            "serialization_plan_id": self.serialization_plan_id,
            "train_jsonl_sha256": self.train_jsonl_sha256,
            "train_jsonl_byte_size": self.train_jsonl_byte_size,
            "evaluation_jsonl_sha256": self.evaluation_jsonl_sha256,
            "evaluation_jsonl_byte_size": self.evaluation_jsonl_byte_size,
            "provenance_jsonl_sha256": self.provenance_jsonl_sha256,
            "provenance_jsonl_byte_size": self.provenance_jsonl_byte_size,
            "train_row_count": self.train_row_count,
            "evaluation_row_count": self.evaluation_row_count,
            "total_row_count": self.total_row_count,
        }

    @classmethod
    def from_dump(cls, payload: dict[str, Any]) -> ImportedBundleRowSet:
        from veriformis.datasets.serialization import ProductRow
        from veriformis.mapping.finish import ImportedRowProvenance

        if payload.get("schema_version") != IMPORTED_BUNDLE_ROW_SET_SCHEMA:
            raise ValueError("imported bundle row set schema mismatch")
        return cls(
            row_schema=payload["row_schema"],
            train_rows=tuple(
                ProductRow.model_validate(item) for item in payload["train_rows"]
            ),
            evaluation_rows=tuple(
                ProductRow.model_validate(item) for item in payload["evaluation_rows"]
            ),
            provenance=tuple(
                ImportedRowProvenance.model_validate(item)
                for item in payload["provenance"]
            ),
            row_set_id=payload["row_set_id"],
            split_result_id=payload["split_result_id"],
            plan_id=payload["plan_id"],
            recipe_id=payload["recipe_id"],
            mapping_result_id=payload["mapping_result_id"],
            construction_result_id=payload["construction_result_id"],
            curation_result_id=payload["curation_result_id"],
            serialization_plan_id=payload["serialization_plan_id"],
            train_jsonl_sha256=payload["train_jsonl_sha256"],
            train_jsonl_byte_size=payload["train_jsonl_byte_size"],
            evaluation_jsonl_sha256=payload["evaluation_jsonl_sha256"],
            evaluation_jsonl_byte_size=payload["evaluation_jsonl_byte_size"],
            provenance_jsonl_sha256=payload["provenance_jsonl_sha256"],
            provenance_jsonl_byte_size=payload["provenance_jsonl_byte_size"],
            train_row_count=payload["train_row_count"],
            evaluation_row_count=payload["evaluation_row_count"],
            total_row_count=payload["total_row_count"],
        )


def _verify_imported_row_provenance_alignment(
    root_descriptor: int,
    *,
    file_facts: dict[str, _EntryFacts],
    files_by_path: dict[str, BundleFile],
    snapshot: Any,
) -> ImportedBundleRowSet:
    """Align imported payloads with mapping provenance; never invent chunks."""
    from veriformis.datasets.serialization import ProductRow
    from veriformis.mapping.finish import ImportedRowProvenance

    descriptors: dict[str, int] = {}
    handles: dict[str, BinaryIO] = {}
    try:
        for path in (TRAIN_PATH, EVALUATION_PATH, PROVENANCE_PATH):
            descriptors[path] = _open_regular_file(
                root_descriptor,
                path,
                expected_facts=file_facts[path],
            )
        handles = {
            path: os.fdopen(descriptor, "rb", closefd=False)
            for path, descriptor in descriptors.items()
        }
        train_rows: list[ProductRow] = []
        evaluation_rows: list[ProductRow] = []
        provenance_values: list[ImportedRowProvenance] = []
        seen_record_ids: set[str] = set()
        expected_row_schema: str | None = None
        provenance_ordinal = 0
        for partition, payload_path in (
            ("train", TRAIN_PATH),
            ("evaluation", EVALUATION_PATH),
        ):
            declared_count = files_by_path[payload_path].record_count
            if declared_count is None:
                raise BundleVerificationError(
                    f"missing record count for {payload_path!r}"
                )
            previous_record_id: str | None = None
            for ordinal in range(declared_count):
                payload = _read_jsonl_object(
                    handles[payload_path],
                    path=payload_path,
                    ordinal=ordinal,
                )
                raw_provenance = _read_jsonl_object(
                    handles[PROVENANCE_PATH],
                    path=PROVENANCE_PATH,
                    ordinal=provenance_ordinal,
                )
                if payload is None or raw_provenance is None:
                    raise BundleVerificationError(
                        "dataset payload and provenance counts do not align"
                    )
                try:
                    provenance = ImportedRowProvenance.model_validate(raw_provenance)
                    keys = set(payload)
                    if keys == {"text"}:
                        row_schema = "text"
                    elif keys == {"prompt", "completion"}:
                        row_schema = "prompt_completion"
                    elif keys == {"instruction", "input", "output"}:
                        row_schema = "instruction_output"
                    elif keys == {"messages"}:
                        row_schema = "messages"
                    elif keys == {"annotator", "context", "label"}:
                        row_schema = "label-classification"
                    else:
                        raise BundleVerificationError(
                            "imported payload does not match a v1 row schema"
                        )
                    row = ProductRow.create(
                        record_id=provenance.record_id,
                        row_schema=row_schema,  # type: ignore[arg-type]
                        payload=payload,
                    )
                except (
                    RecursionError,
                    TypeError,
                    UnicodeError,
                    ValueError,
                    VeriformisError,
                ) as exc:
                    raise BundleVerificationError(
                        f"invalid imported row provenance contract: {exc}"
                    ) from exc
                if expected_row_schema is None:
                    expected_row_schema = row.row_schema
                elif row.row_schema != expected_row_schema:
                    raise BundleVerificationError(
                        "finished dataset mixes multiple row schemas"
                    )
                if (
                    provenance.plan_id != snapshot.plan_id
                    or provenance.recipe_id != snapshot.recipe_id
                    or provenance.mapping_result_id != snapshot.mapping_result_id
                    or provenance.curation_result_id != snapshot.curation_result_id
                    or provenance.split_result_id != snapshot.split_result_id
                    or provenance.row_id != row.row_id
                    or provenance.payload_sha256 != row.payload_sha256
                    or provenance.partition != partition
                    or provenance.ordinal != ordinal
                ):
                    raise BundleVerificationError(
                        "imported row provenance is not aligned with its payload"
                    )
                if not set(provenance.source_ids) <= set(snapshot.source_ids):
                    raise BundleVerificationError(
                        "imported provenance names a source outside the snapshot"
                    )
                if provenance.record_id in seen_record_ids:
                    raise BundleVerificationError(
                        "finished dataset contains duplicate imported records"
                    )
                seen_record_ids.add(provenance.record_id)
                if previous_record_id is not None and (
                    provenance.record_id <= previous_record_id
                ):
                    raise BundleVerificationError(
                        "partition records are not in canonical record-id order"
                    )
                previous_record_id = provenance.record_id
                if partition == "train":
                    train_rows.append(row)
                else:
                    evaluation_rows.append(row)
                provenance_values.append(provenance)
                provenance_ordinal += 1
            if (
                _read_jsonl_object(
                    handles[payload_path],
                    path=payload_path,
                    ordinal=declared_count,
                )
                is not None
            ):
                raise BundleVerificationError(
                    f"dataset payload {payload_path!r} exceeds its declared count"
                )
        if (
            _read_jsonl_object(
                handles[PROVENANCE_PATH],
                path=PROVENANCE_PATH,
                ordinal=provenance_ordinal,
            )
            is not None
        ):
            raise BundleVerificationError(
                "row provenance exceeds the combined dataset payload count"
            )
        if expected_row_schema is None:
            raise BundleVerificationError("finished dataset contains no product rows")
        if (
            len(train_rows) != snapshot.file_bindings[0].record_count
            or len(evaluation_rows) != snapshot.file_bindings[1].record_count
            or len(provenance_values) != snapshot.file_bindings[2].record_count
        ):
            raise BundleVerificationError(
                "imported payload counts differ from the snapshot"
            )
        if snapshot.row_set_id.split("-v")[0] != "rws":
            raise BundleVerificationError("imported snapshot row-set identity is invalid")
        for path, descriptor in descriptors.items():
            if _stable_entry_facts(os.fstat(descriptor)) != file_facts[path]:
                raise BundleVerificationError(
                    f"bundle file changed during row alignment: {path!r}"
                )
        first = provenance_values[0]
        train_binding, evaluation_binding, provenance_binding = snapshot.file_bindings
        return ImportedBundleRowSet(
            row_schema=expected_row_schema,
            train_rows=tuple(train_rows),
            evaluation_rows=tuple(evaluation_rows),
            provenance=tuple(provenance_values),
            row_set_id=snapshot.row_set_id,
            split_result_id=snapshot.split_result_id,
            plan_id=snapshot.plan_id,
            recipe_id=snapshot.recipe_id,
            mapping_result_id=snapshot.mapping_result_id,
            construction_result_id=snapshot.mapping_result_id,
            curation_result_id=snapshot.curation_result_id,
            serialization_plan_id=first.serialization_plan_id,
            train_jsonl_sha256=train_binding.sha256,
            train_jsonl_byte_size=train_binding.byte_size,
            evaluation_jsonl_sha256=evaluation_binding.sha256,
            evaluation_jsonl_byte_size=evaluation_binding.byte_size,
            provenance_jsonl_sha256=provenance_binding.sha256,
            provenance_jsonl_byte_size=provenance_binding.byte_size,
            train_row_count=len(train_rows),
            evaluation_row_count=len(evaluation_rows),
            total_row_count=len(train_rows) + len(evaluation_rows),
        )
    finally:
        for handle in handles.values():
            handle.close()
        for descriptor in descriptors.values():
            os.close(descriptor)


def _verify_row_provenance_alignment(
    root_descriptor: int,
    *,
    file_facts: dict[str, _EntryFacts],
    files_by_path: dict[str, BundleFile],
    snapshot: Any,
) -> RowSet:
    from veriformis.datasets.curation import OBJECTIVE_FIELD_ROLES
    from veriformis.datasets.models import CurationDecision
    from veriformis.datasets.serialization import (
        RowSet,
        row_provenance_from_json_bytes,
    )

    descriptors: dict[str, int] = {}
    handles: dict[str, BinaryIO] = {}
    try:
        for path in (TRAIN_PATH, EVALUATION_PATH, PROVENANCE_PATH):
            descriptors[path] = _open_regular_file(
                root_descriptor,
                path,
                expected_facts=file_facts[path],
            )
        handles = {
            path: os.fdopen(descriptor, "rb", closefd=False)
            for path, descriptor in descriptors.items()
        }
        seen_record_ids: set[str] = set()
        seen_row_ids: set[str] = set()
        seen_provenance_ids: set[str] = set()
        seen_assignment_ids: set[str] = set()
        seen_promotion_decision_ids: set[str] = set()
        seen_curation_decision_ids: set[str] = set()
        seen_record_fingerprints: set[str] = set()
        emitted_source_ids: set[str] = set()
        partition_by_source_id: dict[str, str] = {}
        partition_by_leakage_group_id: dict[str, str] = {}
        leakage_group_by_source_id: dict[str, str] = {}
        target_by_conflict_key: dict[
            tuple[str, tuple[str, ...], tuple[tuple[str, str], ...]],
            tuple[tuple[str, str], ...],
        ] = {}
        train_rows: list[Any] = []
        evaluation_rows: list[Any] = []
        provenance_values: list[Any] = []
        expected_row_schema: str | None = None
        expected_objective_id: str | None = None
        expected_serialization_plan_id: str | None = None
        provenance_ordinal = 0
        for partition, payload_path in (
            ("train", TRAIN_PATH),
            ("evaluation", EVALUATION_PATH),
        ):
            declared_count = files_by_path[payload_path].record_count
            if declared_count is None:
                raise BundleVerificationError(
                    f"missing record count for {payload_path!r}"
                )
            previous_record_id: str | None = None
            for ordinal in range(declared_count):
                payload = _read_jsonl_object(
                    handles[payload_path],
                    path=payload_path,
                    ordinal=ordinal,
                )
                raw_provenance = _read_jsonl_object(
                    handles[PROVENANCE_PATH],
                    path=PROVENANCE_PATH,
                    ordinal=provenance_ordinal,
                )
                if payload is None or raw_provenance is None:
                    raise BundleVerificationError(
                        "dataset payload and provenance counts do not align"
                    )
                try:
                    provenance = row_provenance_from_json_bytes(
                        lossless_json_bytes(raw_provenance)
                    )
                except (
                    RecursionError,
                    TypeError,
                    UnicodeError,
                    ValueError,
                    VeriformisError,
                ) as exc:
                    raise BundleVerificationError(
                        f"invalid row provenance contract: {exc}"
                    ) from exc
                row, row_schema, objective_kind = _row_contract(payload, provenance)
                if expected_row_schema is None:
                    expected_row_schema = row_schema
                elif row_schema != expected_row_schema:
                    raise BundleVerificationError(
                        "finished dataset mixes multiple row schemas"
                    )
                if expected_objective_id is None:
                    expected_objective_id = provenance.objective_id
                elif provenance.objective_id != expected_objective_id:
                    raise BundleVerificationError(
                        "finished dataset mixes multiple training objectives"
                    )
                if expected_serialization_plan_id is None:
                    expected_serialization_plan_id = provenance.serialization_plan_id
                elif provenance.serialization_plan_id != expected_serialization_plan_id:
                    raise BundleVerificationError(
                        "finished dataset mixes multiple serialization plans"
                    )
                if (
                    provenance.plan_id != snapshot.plan_id
                    or provenance.recipe_id != snapshot.recipe_id
                    or provenance.construction_result_id
                    != snapshot.construction_result_id
                    or provenance.curation_result_id != snapshot.curation_result_id
                    or provenance.split_result_id != snapshot.split_result_id
                ):
                    raise BundleVerificationError(
                        "row provenance identities differ from validation snapshot"
                    )
                if not set(provenance.source_ids) <= set(snapshot.source_ids):
                    raise BundleVerificationError(
                        "row provenance names a source outside the dataset snapshot"
                    )
                expected_curation_decision = CurationDecision.create(
                    record_id=provenance.record_id,
                    status="included",
                    reason_code="quality-passed",
                )
                if (
                    provenance.curation_decision_id
                    != expected_curation_decision.decision_id
                ):
                    raise BundleVerificationError(
                        "row provenance does not bind its included curation decision"
                    )
                record_fingerprint = canonical_digest(
                    {
                        "schema_version": "veriformis.exact-record-fingerprint/v1",
                        "objective_id": provenance.objective_id,
                        "fields": tuple(
                            {"name": field.name, "value": field.value}
                            for field in provenance.record_fields
                        ),
                    }
                )
                if record_fingerprint in seen_record_fingerprints:
                    raise BundleVerificationError(
                        "finished dataset contains an exact duplicate record"
                    )
                seen_record_fingerprints.add(record_fingerprint)
                field_values = {
                    field.name: field.value for field in provenance.record_fields
                }
                context_names, target_names = OBJECTIVE_FIELD_ROLES[objective_kind]
                conflict_key = (
                    provenance.objective_id,
                    provenance.source_ids,
                    tuple((name, field_values[name]) for name in context_names),
                )
                target = tuple((name, field_values[name]) for name in target_names)
                previous_target = target_by_conflict_key.setdefault(
                    conflict_key,
                    target,
                )
                if previous_target != target:
                    raise BundleVerificationError(
                        "finished dataset contains a conflicting target class"
                    )
                previous_group_partition = partition_by_leakage_group_id.setdefault(
                    provenance.leakage_group_id,
                    partition,
                )
                if previous_group_partition != partition:
                    raise BundleVerificationError(
                        "one leakage group appears in multiple partitions"
                    )
                for source_id in provenance.source_ids:
                    emitted_source_ids.add(source_id)
                    previous_source_partition = partition_by_source_id.setdefault(
                        source_id,
                        partition,
                    )
                    if previous_source_partition != partition:
                        raise BundleVerificationError(
                            "one source appears in multiple partitions"
                        )
                    previous_source_group = leakage_group_by_source_id.setdefault(
                        source_id,
                        provenance.leakage_group_id,
                    )
                    if previous_source_group != provenance.leakage_group_id:
                        raise BundleVerificationError(
                            "one source appears in multiple leakage groups"
                        )
                if (
                    provenance.partition != partition
                    or provenance.ordinal != ordinal
                    or provenance.row_id != row.row_id
                    or provenance.payload_sha256 != row.payload_sha256
                ):
                    raise BundleVerificationError(
                        "row provenance is not aligned with its payload line"
                    )
                if previous_record_id is not None and (
                    provenance.record_id <= previous_record_id
                ):
                    raise BundleVerificationError(
                        "partition records are not in canonical record-id order"
                    )
                previous_record_id = provenance.record_id
                for value, seen, label in (
                    (provenance.record_id, seen_record_ids, "record"),
                    (provenance.row_id, seen_row_ids, "row"),
                    (provenance.provenance_id, seen_provenance_ids, "provenance"),
                    (provenance.assignment_id, seen_assignment_ids, "assignment"),
                    (
                        provenance.promotion_decision_id,
                        seen_promotion_decision_ids,
                        "promotion decision",
                    ),
                    (
                        provenance.curation_decision_id,
                        seen_curation_decision_ids,
                        "curation decision",
                    ),
                ):
                    if value in seen:
                        raise BundleVerificationError(
                            f"finished dataset contains duplicate {label} identity"
                        )
                    seen.add(value)
                if partition == "train":
                    train_rows.append(row)
                else:
                    evaluation_rows.append(row)
                provenance_values.append(provenance)
                provenance_ordinal += 1

            if (
                _read_jsonl_object(
                    handles[payload_path],
                    path=payload_path,
                    ordinal=declared_count,
                )
                is not None
            ):
                raise BundleVerificationError(
                    f"dataset payload {payload_path!r} exceeds its declared count"
                )
        if (
            _read_jsonl_object(
                handles[PROVENANCE_PATH],
                path=PROVENANCE_PATH,
                ordinal=provenance_ordinal,
            )
            is not None
        ):
            raise BundleVerificationError(
                "row provenance exceeds the combined dataset payload count"
            )
        if emitted_source_ids != set(snapshot.source_ids):
            raise BundleVerificationError(
                "dataset rows do not cover the exact snapshot source scope"
            )
        if expected_row_schema is None or expected_serialization_plan_id is None:
            raise BundleVerificationError("finished dataset contains no product rows")
        try:
            row_set = RowSet.create(
                plan_id=snapshot.plan_id,
                serialization_plan_id=expected_serialization_plan_id,
                recipe_id=snapshot.recipe_id,
                construction_result_id=snapshot.construction_result_id,
                curation_result_id=snapshot.curation_result_id,
                split_result_id=snapshot.split_result_id,
                row_schema=expected_row_schema,
                train_rows=train_rows,
                evaluation_rows=evaluation_rows,
                provenance=provenance_values,
            )
        except (
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ) as exc:
            raise BundleVerificationError(
                f"cannot reconstruct the exact dataset row set: {exc}"
            ) from exc
        if row_set.row_set_id != snapshot.row_set_id:
            raise BundleVerificationError(
                "reconstructed row-set identity differs from the validation snapshot"
            )
        row_set_bytes = lossless_json_bytes(row_set.model_dump(mode="json"))
        row_set_binding = next(
            binding
            for binding in snapshot.artifact_bindings
            if binding.role == "row-set"
        )
        if row_set_binding.sha256 != sha256_digest(
            row_set_bytes
        ) or row_set_binding.byte_size != len(row_set_bytes):
            raise BundleVerificationError(
                "reconstructed row-set bytes differ from the snapshot artifact binding"
            )
        for path, descriptor in descriptors.items():
            if _stable_entry_facts(os.fstat(descriptor)) != file_facts[path]:
                raise BundleVerificationError(
                    f"bundle file changed during row alignment: {path!r}"
                )
        return row_set
    finally:
        for handle in handles.values():
            handle.close()
        for descriptor in descriptors.values():
            os.close(descriptor)


def _inspect_finished_bundle(
    bundle_dir: str | os.PathLike[str],
    *,
    expected_manifest_sha256: str | None,
) -> VerifiedFinishedBundle:
    if expected_manifest_sha256 is not None:
        try:
            validate_sha256(expected_manifest_sha256)
        except (TypeError, ValueError) as exc:
            raise BundleVerificationError(
                f"invalid expected manifest SHA-256: {exc}"
            ) from exc

    root = Path(os.path.abspath(os.fspath(bundle_dir)))
    root_descriptor = _open_root(root)
    try:
        actual_files, actual_directories = _collect_tree(root_descriptor)
        actual_file_paths = set(actual_files)
        actual_directory_paths = set(actual_directories)
        required_metadata = {MANIFEST_NAME, ATTESTATION_NAME}
        missing_metadata = required_metadata - actual_file_paths
        if missing_metadata:
            raise BundleVerificationError(
                f"finished bundle is missing metadata files: "
                f"{sorted(missing_metadata)!r}"
            )

        manifest_bytes = _read_metadata(
            root_descriptor,
            MANIFEST_NAME,
            expected_facts=actual_files[MANIFEST_NAME],
        )
        manifest_sha256 = sha256_digest(manifest_bytes)
        if (
            expected_manifest_sha256 is not None
            and manifest_sha256 != expected_manifest_sha256
        ):
            raise BundleVerificationError(
                "finished bundle manifest does not match the expected external digest"
            )
        try:
            manifest = FinishedBundleManifest.from_json_bytes(manifest_bytes)
        except FinishedBundleError as exc:
            raise BundleVerificationError(f"invalid finished manifest: {exc}") from exc

        expected_files = required_metadata | {file.path for file in manifest.files}
        expected_directories = _expected_directories(manifest.files)
        if actual_file_paths != expected_files:
            missing = sorted(expected_files - actual_file_paths)
            extra = sorted(actual_file_paths - expected_files)
            raise BundleVerificationError(
                f"finished bundle file set is not closed; "
                f"missing={missing!r}, extra={extra!r}"
            )
        if actual_directory_paths != expected_directories:
            missing = sorted(expected_directories - actual_directory_paths)
            extra = sorted(actual_directory_paths - expected_directories)
            raise BundleVerificationError(
                f"finished bundle directory set is not closed; "
                f"missing={missing!r}, extra={extra!r}"
            )

        attestation_bytes = _read_metadata(
            root_descriptor,
            ATTESTATION_NAME,
            expected_facts=actual_files[ATTESTATION_NAME],
        )
        try:
            attestation = BundleAttestation.from_json_bytes(attestation_bytes)
        except FinishedBundleError as exc:
            raise BundleVerificationError(f"invalid bundle attestation: {exc}") from exc
        _verify_attestation_binding(
            manifest=manifest,
            manifest_sha256=manifest_sha256,
            attestation=attestation,
        )

        for file in manifest.files:
            _verify_payload(
                root_descriptor,
                file,
                expected_facts=actual_files[file.path],
            )

        validation_bytes = _read_metadata(
            root_descriptor,
            VALIDATION_PATH,
            expected_facts=actual_files[VALIDATION_PATH],
        )
        validation_report = _require_passing_validation_report(
            validation_bytes,
            dataset_snapshot_id=manifest.dataset_snapshot_id,
            validation_report_id=manifest.validation_report_id,
            payload_bindings={
                file.path: (
                    file.sha256,
                    file.size,
                    file.record_count,
                    file.role,
                    file.media_type,
                )
                for file in manifest.files
                if file.path in {TRAIN_PATH, EVALUATION_PATH, PROVENANCE_PATH}
                and file.record_count is not None
            },
            error_type=BundleVerificationError,
        )
        snapshot = validation_report.snapshot
        if getattr(snapshot, "schema_version", None) == (
            "veriformis.imported-dataset-snapshot/v1"
        ):
            row_set = _verify_imported_row_provenance_alignment(
                root_descriptor,
                file_facts=actual_files,
                files_by_path={file.path: file for file in manifest.files},
                snapshot=snapshot,
            )
        else:
            row_set = _verify_row_provenance_alignment(
                root_descriptor,
                file_facts=actual_files,
                files_by_path={file.path: file for file in manifest.files},
                snapshot=snapshot,
            )

        final_files, final_directories = _collect_tree(root_descriptor)
        if final_files != actual_files or final_directories != actual_directories:
            raise BundleVerificationError(
                "finished bundle tree changed during verification"
            )
        if (
            _read_metadata(
                root_descriptor,
                MANIFEST_NAME,
                expected_facts=actual_files[MANIFEST_NAME],
            )
            != manifest_bytes
        ):
            raise BundleVerificationError(
                "finished bundle manifest changed during verification"
            )
        if (
            _read_metadata(
                root_descriptor,
                ATTESTATION_NAME,
                expected_facts=actual_files[ATTESTATION_NAME],
            )
            != attestation_bytes
        ):
            raise BundleVerificationError(
                "bundle attestation changed during verification"
            )

        trust_grade: Literal["self_consistent", "external_digest"] = (
            "external_digest"
            if expected_manifest_sha256 is not None
            else "self_consistent"
        )
        verification = VerificationResult.create(
            bundle_id=manifest.bundle_id,
            dataset_snapshot_id=manifest.dataset_snapshot_id,
            validation_report_id=manifest.validation_report_id,
            manifest_sha256=manifest_sha256,
            content_root_sha256=manifest.content_root_sha256,
            trust_grade=trust_grade,
            payload_file_count=len(manifest.files),
            declared_record_count=sum(
                file.record_count or 0
                for file in manifest.files
                if file.path in {TRAIN_PATH, EVALUATION_PATH}
            ),
        )
        return VerifiedFinishedBundle(
            bundle_path=root,
            manifest=manifest,
            validation_report=validation_report,
            row_set=row_set,
            verification=verification,
        )
    finally:
        os.close(root_descriptor)


def inspect_finished_bundle(
    bundle_dir: str | os.PathLike[str],
    *,
    expected_manifest_sha256: str | None = None,
) -> VerifiedFinishedBundle:
    """Verify and reconstruct one bundle in the same descriptor-anchored pass."""
    try:
        return _inspect_finished_bundle(
            bundle_dir,
            expected_manifest_sha256=expected_manifest_sha256,
        )
    except BundleVerificationError:
        raise
    except (OSError, RecursionError, TypeError, UnicodeError, ValueError) as exc:
        raise BundleVerificationError(
            f"finished bundle inspection failed: {exc}"
        ) from exc


def verify_finished_bundle(
    bundle_dir: str | os.PathLike[str],
    *,
    expected_manifest_sha256: str | None = None,
) -> VerificationResult:
    """Verify an exact closed bundle or raise :class:`BundleVerificationError`.

    Without an external manifest digest, success proves only internal
    self-consistency.  Supplying the expected SHA-256 upgrades the returned
    trust grade because it anchors the canonical manifest outside the bundle.
    """
    try:
        return _inspect_finished_bundle(
            bundle_dir,
            expected_manifest_sha256=expected_manifest_sha256,
        ).verification
    except BundleVerificationError:
        raise
    except (OSError, RecursionError, TypeError, UnicodeError, ValueError) as exc:
        raise BundleVerificationError(
            f"finished bundle verification failed: {exc}"
        ) from exc


__all__ = [
    "VerifiedFinishedBundle",
    "inspect_finished_bundle",
    "verify_finished_bundle",
]
