from __future__ import annotations

import json
from copy import deepcopy
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from pydantic import ValidationError

from veriformis.chunkers.base import Chunk
from veriformis.chunkers.strategies import chunk_paragraph, chunk_structure
from veriformis.construction import (
    ConstructionInputs,
    ConstructionPass,
    ConstructionResult,
    DatasetRecipe,
    IRArtifactInput,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
)
from veriformis.datasets.curation import curate_dataset
from veriformis.datasets.models import (
    CurationPolicy,
    CurationResult,
)
from veriformis.datasets.plan import FinishedDatasetPlan
from veriformis.datasets.serialization import (
    ProductRow,
    RowProvenance,
    RowSet,
    SerializationPlan,
    product_row_from_dict,
    product_row_from_json_bytes,
    product_row_to_dict,
    row_provenance_from_json_bytes,
    row_provenance_to_dict,
    row_set_from_dict,
    row_set_from_json_bytes,
    row_set_to_dict,
    serialization_plan_from_dict,
    serialization_plan_from_json_bytes,
    serialization_plan_to_dict,
    serialize_dataset,
)
from veriformis.datasets.splitting import (
    SplitPolicy,
    SplitResult,
    split_dataset,
)
from veriformis.errors import DuplicateIdentityError, SerializationError
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
)
from veriformis.ir import (
    Block,
    Document,
    Heading,
    Link,
    Paragraph,
    Text,
    attach_canonical_provenance,
)
from veriformis.ir.serde import document_to_dict
from veriformis.rules.cleaning import plan_cleaning
from veriformis.rules.derivations import build_block_derivations
from veriformis.rules.engine import RegexRule, TransformRecord
from veriformis.sources import SourceRef, register_source


@dataclass(frozen=True)
class SourceBundle:
    source: SourceRef
    document: Document
    chunks: tuple[Chunk, ...]
    artifact: IRArtifactInput


def source_bundle(
    tmp_path: Path,
    *,
    logical_path: str,
    blocks: Sequence[Block],
    strategy: str = "paragraph",
    size: int = 1_000,
) -> SourceBundle:
    document = Document(children=list(blocks))
    stream = attach_canonical_provenance(document)
    source = register_source(
        tmp_path / logical_path,
        "fixture",
        stream,
        logical_path=logical_path,
        raw_bytes=stream.encode("utf-8"),
    )
    document.source_id = source.id
    chunker = chunk_structure if strategy == "structure" else chunk_paragraph
    chunks = chunker(
        document.children,
        max_size=size,
        source=source,
        transformed=set(),
        block_derivations={},
        region_id="body",
    )
    document_json = lossless_json_bytes(document_to_dict(document))
    artifact_config_digest = canonical_digest({"fixture": logical_path})
    artifact_id = derive_artifact_id(
        kind="cleaned-document-ir",
        content_sha256=sha256_digest(document_json),
        source_ids=(source.id,),
        producer_id="veriformis.test.serialization",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.serialization",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    return SourceBundle(source, document, tuple(chunks), artifact)


def cleaned_source_bundle(
    tmp_path: Path,
    *,
    logical_path: str,
    text: str,
) -> tuple[SourceBundle, tuple[TransformRecord, ...]]:
    original = Document(children=[Paragraph(children=[Text(text)])])
    stream = attach_canonical_provenance(original)
    source = register_source(
        tmp_path / logical_path,
        "fixture",
        stream,
        logical_path=logical_path,
        raw_bytes=stream.encode("utf-8"),
    )
    original.source_id = source.id
    preview = plan_cleaning(
        original,
        [RegexRule("collapse-space", r" {2,}", " ", flags=0)],
    )
    derivations = build_block_derivations(
        source,
        preview.document,
        cleaning_plan_id=preview.plan.id,
    )
    transformed = {
        record.block_index
        for record in preview.records
        if record.edits and not record.warned
    }
    chunks = chunk_paragraph(
        preview.document.children,
        max_size=1_000,
        source=source,
        transformed=transformed,
        block_derivations=derivations,
        region_id="body",
    )
    document_json = lossless_json_bytes(document_to_dict(preview.document))
    artifact_config_digest = canonical_digest({"cleaning_plan_id": preview.plan.id})
    artifact_id = derive_artifact_id(
        kind="cleaned-document-ir",
        content_sha256=sha256_digest(document_json),
        source_ids=(source.id,),
        producer_id="veriformis.test.serialization-cleaning",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    artifact = IRArtifactInput.create(
        source_id=source.id,
        artifact_id=artifact_id,
        artifact_kind="cleaned-document-ir",
        document_json=document_json,
        producer_id="veriformis.test.serialization-cleaning",
        producer_version="1",
        config_digest=artifact_config_digest,
    )
    bundle = SourceBundle(source, preview.document, tuple(chunks), artifact)
    return bundle, tuple(preview.records)


def recipe_for(
    sources: Sequence[SourceRef],
    objective_kind: str,
    *,
    strategy: str = "paragraph",
) -> DatasetRecipe:
    objective = TrainingObjective.create(objective_kind)
    construction_pass = ConstructionPass.create(
        sequence=1,
        objective_kind=objective_kind,
    )
    return DatasetRecipe.create(
        objective=objective,
        source_ids=tuple(source.id for source in sources),
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy=strategy,
            size=1_000,
            overlap=100,
        ),
        passes=(construction_pass,),
        target_row_schema=(
            "text" if objective_kind == "full_text" else "prompt_completion"
        ),
    )


def inputs_for(
    bundles: Sequence[SourceBundle],
    *,
    transforms: Sequence[TransformRecord] = (),
) -> ConstructionInputs:
    return ConstructionInputs.create(
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        sources=tuple(bundle.source for bundle in bundles),
        chunks=tuple(chunk for bundle in bundles for chunk in bundle.chunks),
        transforms=transforms,
        ir_artifacts=tuple(bundle.artifact for bundle in bundles),
    )


@dataclass(frozen=True)
class SerializationCase:
    finished_plan: FinishedDatasetPlan
    recipe: DatasetRecipe
    construction: ConstructionResult
    curation: CurationResult
    split: SplitResult

    @property
    def plan_id(self) -> str:
        return self.finished_plan.plan_id

    @property
    def serialization_plan(self) -> SerializationPlan:
        return self.finished_plan.serialization_plan


def _recipe_with_row_schema(base: DatasetRecipe, row_schema: str) -> DatasetRecipe:
    return DatasetRecipe.create(
        objective=base.objective,
        source_ids=base.source_ids,
        cleaning_config_digest=base.cleaning_config_digest,
        segmentation=base.segmentation,
        passes=base.passes,
        target_row_schema=row_schema,
        review_policy=base.review_policy,
    )


def _case(
    tmp_path: Path,
    *,
    objective_kind: str,
    row_schema: str,
) -> SerializationCase:
    transforms = ()
    if objective_kind == "full_text":
        bundles = (
            source_bundle(
                tmp_path,
                logical_path="full-alpha.txt",
                blocks=[Paragraph(children=[Text("  Alpha exact text.  ")])],
            ),
            source_bundle(
                tmp_path,
                logical_path="full-beta.txt",
                blocks=[
                    Paragraph(
                        children=[
                            Text("Beta Caf\N{LATIN SMALL LETTER E WITH ACUTE} text.")
                        ]
                    )
                ],
            ),
        )
        base = recipe_for(tuple(item.source for item in bundles), objective_kind)
    elif objective_kind == "continuation":
        bundles = (
            source_bundle(
                tmp_path,
                logical_path="continuation-alpha.txt",
                blocks=[Paragraph(children=[Text("abcdeFGHIJ")])],
            ),
            source_bundle(
                tmp_path,
                logical_path="continuation-beta.txt",
                blocks=[Paragraph(children=[Text("klmnoPQRST")])],
            ),
        )
        base = recipe_for(tuple(item.source for item in bundles), objective_kind)
    elif objective_kind == "section_reconstruction":
        bundles = (
            source_bundle(
                tmp_path,
                logical_path="section-alpha.md",
                blocks=[
                    Heading(level=1, children=[Text("Alpha heading")]),
                    Paragraph(children=[Text("  Alpha section exact.  ")]),
                ],
                strategy="structure",
            ),
            source_bundle(
                tmp_path,
                logical_path="section-beta.md",
                blocks=[
                    Heading(level=1, children=[Text("Beta heading")]),
                    Paragraph(children=[Text("Beta section exact.")]),
                ],
                strategy="structure",
            ),
        )
        base = recipe_for(
            tuple(item.source for item in bundles),
            objective_kind,
            strategy="structure",
        )
    elif objective_kind == "before_after_transformation":
        alpha, alpha_transforms = cleaned_source_bundle(
            tmp_path,
            logical_path="before-after-alpha.txt",
            text="Alpha   exact transformation.",
        )
        beta, beta_transforms = cleaned_source_bundle(
            tmp_path,
            logical_path="before-after-beta.txt",
            text="Beta   exact transformation.",
        )
        bundles = (alpha, beta)
        transforms = (*alpha_transforms, *beta_transforms)
        base = recipe_for(tuple(item.source for item in bundles), objective_kind)
    elif objective_kind == "structured_field":
        bundles = (
            source_bundle(
                tmp_path,
                logical_path="structured-alpha.md",
                blocks=[
                    Paragraph(
                        children=[
                            Text("Alpha source "),
                            Link(
                                children=[Text("link")],
                                href="https://example.test/alpha",
                                title=None,
                            ),
                        ]
                    )
                ],
            ),
            source_bundle(
                tmp_path,
                logical_path="structured-beta.md",
                blocks=[
                    Paragraph(
                        children=[
                            Text("Beta source "),
                            Link(
                                children=[Text("link")],
                                href="https://example.test/beta",
                                title=None,
                            ),
                        ]
                    )
                ],
            ),
        )
        base = recipe_for(tuple(item.source for item in bundles), objective_kind)
    else:  # pragma: no cover - the matrix is closed above
        raise AssertionError(f"unsupported fixture objective {objective_kind!r}")

    recipe = _recipe_with_row_schema(base, row_schema)
    inputs = inputs_for(bundles, transforms=transforms)
    construction = construct_dataset(recipe, inputs)
    assert len(construction.records) == 2
    curation_policy = CurationPolicy.create(minimum_target_characters=1)
    split_policy = SplitPolicy.create(
        evaluation_ratio_ppm=500_000,
        evaluation_required=True,
        seed="serialization-test-v1",
    )
    serialization_plan = SerializationPlan.create(
        row_schema=row_schema,
        instruction_text=(
            "  Preserve the exact source-derived relation.  "
            if row_schema == "instruction_output"
            else None
        ),
    )
    finished_plan = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=curation_policy,
        split_policy=split_policy,
        serialization_plan=serialization_plan,
    )
    curation = curate_dataset(
        finished_plan,
        recipe,
        inputs,
        construction,
    )
    assert len(curation.included_record_ids) == 2
    split = split_dataset(
        finished_plan,
        construction,
        curation,
        {bundle.source.id: bundle.source.sha256 for bundle in bundles},
    )
    return SerializationCase(
        finished_plan=finished_plan,
        recipe=recipe,
        construction=construction,
        curation=curation,
        split=split,
    )


COMPATIBLE_OBJECTIVE_ROWS = (
    ("full_text", "text"),
    ("continuation", "prompt_completion"),
    ("continuation", "instruction_output"),
    ("continuation", "messages"),
    ("section_reconstruction", "prompt_completion"),
    ("section_reconstruction", "instruction_output"),
    ("section_reconstruction", "messages"),
    ("before_after_transformation", "prompt_completion"),
    ("before_after_transformation", "instruction_output"),
    ("before_after_transformation", "messages"),
    ("structured_field", "prompt_completion"),
    ("structured_field", "instruction_output"),
    ("structured_field", "messages"),
)


@pytest.mark.parametrize(("objective_kind", "row_schema"), COMPATIBLE_OBJECTIVE_ROWS)
def test_every_objective_lowers_to_every_compatible_exact_row_schema(
    tmp_path: Path,
    objective_kind: str,
    row_schema: str,
) -> None:
    case = _case(
        tmp_path,
        objective_kind=objective_kind,
        row_schema=row_schema,
    )

    output = serialize_dataset(
        case.finished_plan,
        case.recipe,
        case.construction,
        case.curation,
        case.split,
    )

    rows = (*output.row_set.train_rows, *output.row_set.evaluation_rows)
    records = {record.record_id: record for record in case.construction.records}
    assert {row.record_id for row in rows} == set(case.curation.included_record_ids)
    assert len(rows) == len(case.curation.included_record_ids) == 2
    for row in rows:
        fields = {field.name: field.value for field in records[row.record_id].fields}
        if objective_kind == "full_text":
            assert row.payload == {"text": fields["text"]}
        else:
            context_name, target_name = {
                "continuation": ("prompt", "completion"),
                "section_reconstruction": ("heading", "section"),
                "before_after_transformation": ("before", "after"),
                "structured_field": ("input", "fields"),
            }[objective_kind]
            context = fields[context_name]
            target = fields[target_name]
            if row_schema == "prompt_completion":
                assert row.payload == {"prompt": context, "completion": target}
            elif row_schema == "instruction_output":
                assert row.payload == {
                    "instruction": case.serialization_plan.instruction_text,
                    "input": context,
                    "output": target,
                }
            else:
                assert row.payload == {
                    "messages": [
                        {"role": "user", "content": context},
                        {"role": "assistant", "content": target},
                    ]
                }

    assert output.row_set.train_row_count == 1
    assert output.row_set.evaluation_row_count == 1
    assert output.row_set.total_row_count == 2
    assert output.row_set.train_jsonl_byte_size == len(output.train_jsonl)
    assert output.row_set.evaluation_jsonl_byte_size == len(output.evaluation_jsonl)
    assert output.row_set.provenance_jsonl_byte_size == len(output.provenance_jsonl)


def _jsonl_objects(data: bytes) -> list[dict]:
    if not data:
        return []
    assert data.endswith(b"\n")
    lines = data.splitlines(keepends=True)
    values = [json.loads(line) for line in lines]
    assert all(
        lossless_json_bytes(value) + b"\n" == line for value, line in zip(values, lines)
    )
    return values


def test_payload_jsonl_is_canonical_payload_only_and_provenance_is_aligned(
    tmp_path: Path,
) -> None:
    case = _case(
        tmp_path,
        objective_kind="structured_field",
        row_schema="messages",
    )
    output = serialize_dataset(
        case.finished_plan,
        case.recipe,
        case.construction,
        case.curation,
        case.split,
    )

    train_payloads = _jsonl_objects(output.train_jsonl)
    evaluation_payloads = _jsonl_objects(output.evaluation_jsonl)
    provenance_values = _jsonl_objects(output.provenance_jsonl)

    assert all(
        set(payload) == {"messages"}
        for payload in [*train_payloads, *evaluation_payloads]
    )
    assert not any(
        {"record_id", "partition", "provenance", "row_id"} & set(payload)
        for payload in [*train_payloads, *evaluation_payloads]
    )
    assert len(provenance_values) == 2
    assert [(item["partition"], item["ordinal"]) for item in provenance_values] == [
        ("train", 0),
        ("evaluation", 0),
    ]
    assert [item["row_id"] for item in provenance_values] == [
        item.row_id
        for item in (
            *output.row_set.train_rows,
            *output.row_set.evaluation_rows,
        )
    ]
    expected_keys = set(RowProvenance.model_fields)
    assert all(set(item) == expected_keys for item in provenance_values)
    records_by_id = {record.record_id: record for record in case.construction.records}
    for item in output.row_set.provenance:
        assert item.plan_id == case.plan_id
        assert item.construction_result_id == case.construction.result_id
        assert item.curation_result_id == case.curation.result_id
        assert item.split_result_id == case.split.result_id
        assert item.record_fields == records_by_id[item.record_id].fields


def test_serialization_is_repeatedly_deterministic_and_split_input_order_is_canonical(
    tmp_path: Path,
) -> None:
    case = _case(
        tmp_path,
        objective_kind="continuation",
        row_schema="prompt_completion",
    )
    recreated_split = SplitResult.create(
        plan_id=case.split.plan_id,
        policy_id=case.split.policy_id,
        construction_result_id=case.split.construction_result_id,
        curation_result_id=case.split.curation_result_id,
        input_record_ids=tuple(reversed(case.split.input_record_ids)),
        groups=tuple(reversed(case.split.groups)),
        assignments=tuple(reversed(case.split.assignments)),
        requested_evaluation_record_count=(
            case.split.requested_evaluation_record_count
        ),
    )
    assert recreated_split == case.split

    first = serialize_dataset(
        case.finished_plan,
        case.recipe,
        case.construction,
        case.curation,
        case.split,
    )
    second = serialize_dataset(
        case.finished_plan,
        case.recipe,
        case.construction,
        case.curation,
        recreated_split,
    )

    assert second == first
    assert tuple(row.record_id for row in first.row_set.train_rows) == tuple(
        sorted(row.record_id for row in first.row_set.train_rows)
    )
    assert tuple(row.record_id for row in first.row_set.evaluation_rows) == tuple(
        sorted(row.record_id for row in first.row_set.evaluation_rows)
    )


def test_excluded_exact_duplicate_never_becomes_a_row(tmp_path: Path) -> None:
    bundles = tuple(
        source_bundle(
            tmp_path,
            logical_path=f"dedup-{index}.txt",
            blocks=[Paragraph(children=[Text(text)])],
        )
        for index, text in enumerate(("duplicate", "duplicate", "distinct"))
    )
    recipe = recipe_for(tuple(bundle.source for bundle in bundles), "full_text")
    inputs = inputs_for(bundles)
    construction = construct_dataset(recipe, inputs)
    policy = CurationPolicy.create(minimum_target_characters=1)
    split_policy = SplitPolicy.create(
        evaluation_ratio_ppm=500_000,
        evaluation_required=True,
        seed="dedup-test-v1",
    )
    serialization_plan = SerializationPlan.create(row_schema="text")
    finished_plan = FinishedDatasetPlan.create(
        recipe_id=recipe.recipe_id,
        construction_result_id=construction.result_id,
        curation_policy=policy,
        split_policy=split_policy,
        serialization_plan=serialization_plan,
    )
    curation = curate_dataset(finished_plan, recipe, inputs, construction)
    assert len(curation.included_record_ids) == 2
    excluded_ids = {
        decision.record_id
        for decision in curation.decisions
        if decision.status != "included"
    }
    split = split_dataset(
        finished_plan,
        construction,
        curation,
        {bundle.source.id: bundle.source.sha256 for bundle in bundles},
    )

    output = serialize_dataset(
        finished_plan,
        recipe,
        construction,
        curation,
        split,
    )

    emitted_ids = {
        row.record_id
        for row in (*output.row_set.train_rows, *output.row_set.evaluation_rows)
    }
    assert emitted_ids == set(curation.included_record_ids)
    assert emitted_ids.isdisjoint(excluded_ids)


def test_plan_schema_and_instruction_contracts_are_closed(tmp_path: Path) -> None:
    prompt = SerializationPlan.create(row_schema="prompt_completion")
    instruction = SerializationPlan.create(
        row_schema="instruction_output",
        instruction_text="Exact instruction",
    )
    assert prompt.instruction_text is None
    assert instruction.instruction_text == "Exact instruction"

    with pytest.raises(ValidationError, match="requires instruction_text"):
        SerializationPlan.create(row_schema="instruction_output")
    with pytest.raises(ValidationError, match="must be null"):
        SerializationPlan.create(
            row_schema="messages",
            instruction_text="invented prefix",
        )

    case = _case(
        tmp_path,
        objective_kind="continuation",
        row_schema="messages",
    )
    wrong_schema = SerializationPlan.create(row_schema="prompt_completion")
    wrong_finished_plan = FinishedDatasetPlan.create(
        recipe_id=case.finished_plan.recipe_id,
        construction_result_id=case.finished_plan.construction_result_id,
        curation_policy=case.finished_plan.curation_policy,
        split_policy=case.finished_plan.split_policy,
        serialization_plan=wrong_schema,
    )
    with pytest.raises(SerializationError, match="differs from.*recipe"):
        serialize_dataset(
            wrong_finished_plan,
            case.recipe,
            case.construction,
            case.curation,
            case.split,
        )


def test_strict_models_round_trip_only_canonical_exact_json(tmp_path: Path) -> None:
    case = _case(
        tmp_path,
        objective_kind="continuation",
        row_schema="instruction_output",
    )
    output = serialize_dataset(
        case.finished_plan,
        case.recipe,
        case.construction,
        case.curation,
        case.split,
    )
    row = output.row_set.train_rows[0]
    provenance = output.row_set.provenance[0]

    values_and_loaders = (
        (
            serialization_plan_to_dict(case.serialization_plan),
            serialization_plan_from_json_bytes,
            case.serialization_plan,
        ),
        (product_row_to_dict(row), product_row_from_json_bytes, row),
        (
            row_provenance_to_dict(provenance),
            row_provenance_from_json_bytes,
            provenance,
        ),
        (row_set_to_dict(output.row_set), row_set_from_json_bytes, output.row_set),
    )
    for value, loader, expected in values_and_loaders:
        encoded = lossless_json_bytes(value)
        assert loader(encoded) == expected
        with pytest.raises(SerializationError, match="not canonical"):
            loader(encoded + b"\n")

    with pytest.raises(ValidationError, match="frozen"):
        case.serialization_plan.row_schema = "messages"
    value = serialization_plan_to_dict(case.serialization_plan)
    value["extra"] = "not allowed"
    with pytest.raises(SerializationError, match=r"extra=\['extra'\]"):
        serialization_plan_from_dict(value)


def test_nested_tamper_and_fabricated_values_fail_before_emission(
    tmp_path: Path,
) -> None:
    case = _case(
        tmp_path,
        objective_kind="continuation",
        row_schema="prompt_completion",
    )
    record = case.construction.records[0]
    unsafe_field = record.fields[0].model_copy(update={"value": "fabricated"})
    unsafe_record = record.model_copy(
        update={"fields": (unsafe_field, *record.fields[1:])}
    )
    unsafe_construction = case.construction.model_copy(
        update={"records": (unsafe_record, *case.construction.records[1:])}
    )
    with pytest.raises(SerializationError, match="invalid serialization input"):
        serialize_dataset(
            case.finished_plan,
            case.recipe,
            unsafe_construction,
            case.curation,
            case.split,
        )

    unsafe_plan = case.serialization_plan.model_copy(
        update={"serialization_plan_id": derive_id("srp", {})}
    )
    unsafe_finished_plan = case.finished_plan.model_copy(
        update={"serialization_plan": unsafe_plan}
    )
    with pytest.raises(SerializationError, match="identity mismatch"):
        serialize_dataset(
            unsafe_finished_plan,
            case.recipe,
            case.construction,
            case.curation,
            case.split,
        )

    unsafe_assignment = case.split.assignments[0].model_copy(
        update={"record_id": derive_id("rec", {"unknown": True})}
    )
    unsafe_split = case.split.model_copy(
        update={"assignments": (unsafe_assignment, *case.split.assignments[1:])}
    )
    with pytest.raises(SerializationError, match="invalid serialization input"):
        serialize_dataset(
            case.finished_plan,
            case.recipe,
            case.construction,
            case.curation,
            unsafe_split,
        )

    missing_assignment_split = case.split.model_copy(
        update={"assignments": case.split.assignments[:-1]}
    )
    with pytest.raises(SerializationError, match="invalid serialization input"):
        serialize_dataset(
            case.finished_plan,
            case.recipe,
            case.construction,
            case.curation,
            missing_assignment_split,
        )

    duplicate_assignment_split = case.split.model_copy(
        update={
            "assignments": (
                case.split.assignments[0],
                case.split.assignments[0],
            )
        }
    )
    with pytest.raises(DuplicateIdentityError, match="duplicate"):
        serialize_dataset(
            case.finished_plan,
            case.recipe,
            case.construction,
            case.curation,
            duplicate_assignment_split,
        )


def test_row_set_rejects_fan_out_misalignment_and_payload_tamper(
    tmp_path: Path,
) -> None:
    case = _case(
        tmp_path,
        objective_kind="continuation",
        row_schema="prompt_completion",
    )
    output = serialize_dataset(
        case.finished_plan,
        case.recipe,
        case.construction,
        case.curation,
        case.split,
    )
    row_set = output.row_set

    with pytest.raises(DuplicateIdentityError, match="duplicate"):
        RowSet.create(
            plan_id=row_set.plan_id,
            serialization_plan_id=row_set.serialization_plan_id,
            recipe_id=row_set.recipe_id,
            construction_result_id=row_set.construction_result_id,
            curation_result_id=row_set.curation_result_id,
            split_result_id=row_set.split_result_id,
            row_schema=row_set.row_schema,
            train_rows=(*row_set.train_rows, row_set.train_rows[0]),
            evaluation_rows=row_set.evaluation_rows,
            provenance=row_set.provenance,
        )

    value = deepcopy(row_set_to_dict(row_set))
    value["train_rows"][0]["payload"]["completion"] = "fabricated"
    with pytest.raises(SerializationError):
        row_set_from_dict(value)

    value = deepcopy(product_row_to_dict(row_set.train_rows[0]))
    value["payload_sha256"] = "0" * 64
    with pytest.raises(SerializationError, match="payload digest mismatch"):
        product_row_from_dict(value)


def test_loader_rejects_duplicate_keys_and_identity_tamper(tmp_path: Path) -> None:
    case = _case(
        tmp_path,
        objective_kind="full_text",
        row_schema="text",
    )
    output = serialize_dataset(
        case.finished_plan,
        case.recipe,
        case.construction,
        case.curation,
        case.split,
    )
    row_bytes = lossless_json_bytes(product_row_to_dict(output.row_set.train_rows[0]))
    duplicate = row_bytes.replace(b"{", b'{"payload_sha256":"' + b"0" * 64 + b'",', 1)

    with pytest.raises(DuplicateIdentityError, match="duplicate key"):
        product_row_from_json_bytes(duplicate)

    value = row_set_to_dict(output.row_set)
    value["row_set_id"] = derive_id("rws", {"altered": True})
    with pytest.raises(SerializationError, match="identity mismatch"):
        row_set_from_dict(value)


def test_exact_model_fields_are_pinned() -> None:
    assert set(SerializationPlan.model_fields) == {
        "schema_version",
        "serialization_plan_id",
        "row_schema",
        "instruction_text",
    }
    assert set(ProductRow.model_fields) == {
        "schema_version",
        "row_id",
        "record_id",
        "row_schema",
        "payload",
        "payload_sha256",
    }
    assert {
        "record_id",
        "promotion_decision_id",
        "curation_decision_id",
        "leakage_group_id",
        "assignment_id",
        "source_ids",
        "chunk_ids",
        "transform_ids",
        "field_values_sha256",
        "field_evidence_sha256",
        "payload_sha256",
        "partition",
        "ordinal",
    } < set(RowProvenance.model_fields)
    assert {
        "train_rows",
        "evaluation_rows",
        "provenance",
        "train_jsonl_sha256",
        "evaluation_jsonl_sha256",
        "provenance_jsonl_sha256",
        "train_jsonl_byte_size",
        "evaluation_jsonl_byte_size",
        "provenance_jsonl_byte_size",
        "train_row_count",
        "evaluation_row_count",
        "total_row_count",
    } < set(RowSet.model_fields)
    assert SerializationError.code == "serialization-invalid"


def test_dict_helpers_recompute_every_identity(tmp_path: Path) -> None:
    case = _case(
        tmp_path,
        objective_kind="continuation",
        row_schema="messages",
    )
    output = serialize_dataset(
        case.finished_plan,
        case.recipe,
        case.construction,
        case.curation,
        case.split,
    )
    assert (
        serialization_plan_from_dict(
            serialization_plan_to_dict(case.serialization_plan)
        )
        == case.serialization_plan
    )
    assert (
        product_row_from_dict(product_row_to_dict(output.row_set.train_rows[0]))
        == output.row_set.train_rows[0]
    )
    assert row_set_from_dict(row_set_to_dict(output.row_set)) == output.row_set
    assert canonical_digest(row_set_to_dict(output.row_set))
