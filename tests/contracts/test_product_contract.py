import hashlib
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from docx import Document as DocxBuilder
from veriformis.contracts import (
    CANONICAL_STREAM_CONTRACT_ID,
    CANONICAL_STREAM_CONTRACT_VERSION,
    DETERMINISM_PROFILE,
    DETERMINISTIC_V1_OBJECTIVE_KINDS,
    GROUP1_ACCEPTANCE_CONTRACT_ID,
    GROUP1_ACCEPTANCE_CONTRACT_VERSION,
    GROUP1_ERROR_CODES,
    M1_1_ACCEPTANCE_OBJECTIVE_KINDS,
    M1_SOURCE_KINDS,
    PRODUCT_CONTRACT_ID,
    PRODUCT_CONTRACT_VERSION,
    V1_ROW_SCHEMA_KINDS,
    VERIFORMIS_OWNED_STAGES,
)
from veriformis.errors import (
    CleaningPlanError,
    DuplicateIdentityError,
    EvidenceError,
    StaleStageError,
    UnsupportedWorkspaceVersionError,
    WorkspaceCorruptError,
    WorkspaceLockedError,
    WorkspaceRevisionConflict,
)
from veriformis.parsers.markdown import parse_md_file
from veriformis.parsers.docx import parse_docx_file
from veriformis.parsers.text import parse_text


FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "acceptance" / "v1"


def _json(relative: str) -> dict:
    return json.loads((FIXTURE_ROOT / relative).read_text(encoding="utf-8"))


def _manifest_json(name: str) -> dict:
    manifest = _json("acceptance.json")
    relative = Path(manifest[name])
    assert not relative.is_absolute() and ".." not in relative.parts
    return _json(relative.as_posix())


def _generated_docx_bytes() -> bytes:
    raw = BytesIO()
    builder = DocxBuilder()
    builder.add_heading("Generated DOCX", level=1)
    builder.add_paragraph("Body with café text.")
    builder.save(raw)

    normalized = BytesIO()
    with ZipFile(BytesIO(raw.getvalue()), "r") as source, ZipFile(
        normalized,
        "w",
        compression=ZIP_DEFLATED,
        compresslevel=9,
    ) as output:
        for name in sorted(source.namelist()):
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0
            output.writestr(
                info,
                source.read(name),
                compress_type=ZIP_DEFLATED,
                compresslevel=9,
            )
    return normalized.getvalue()


def test_public_contract_constants_are_exact():
    assert PRODUCT_CONTRACT_ID == "veriformis.product"
    assert PRODUCT_CONTRACT_VERSION == 1
    assert GROUP1_ACCEPTANCE_CONTRACT_ID == "veriformis.acceptance.group1"
    assert GROUP1_ACCEPTANCE_CONTRACT_VERSION == 1
    assert CANONICAL_STREAM_CONTRACT_ID == "veriformis.canonical-stream"
    assert CANONICAL_STREAM_CONTRACT_VERSION == 1
    assert DETERMINISM_PROFILE == "offline-deterministic-v1"
    assert M1_SOURCE_KINDS == ("text", "code", "markdown", "docx")
    assert DETERMINISTIC_V1_OBJECTIVE_KINDS == (
        "full_text",
        "continuation",
        "section_reconstruction",
        "before_after_transformation",
        "structured_field",
    )
    assert V1_ROW_SCHEMA_KINDS == (
        "text",
        "prompt_completion",
        "instruction_output",
        "messages",
    )
    assert VERIFORMIS_OWNED_STAGES == (
        "raw_capture",
        "canonical_recovery",
        "cleaning",
        "construction",
        "curation",
        "balancing_and_splitting",
        "formatting",
        "validation",
        "seal",
    )
    assert GROUP1_ERROR_CODES == (
        "workspace-revision-conflict",
        "workspace-corrupt",
        "workspace-locked",
        "stale-stage",
        "duplicate-identity",
        "unsupported-workspace-version",
        "source-evidence-invalid",
        "cleaning-plan-invalid",
    )
    assert tuple(
        error.code
        for error in (
            WorkspaceRevisionConflict,
            WorkspaceCorruptError,
            WorkspaceLockedError,
            StaleStageError,
            DuplicateIdentityError,
            UnsupportedWorkspaceVersionError,
            EvidenceError,
            CleaningPlanError,
        )
    ) == GROUP1_ERROR_CODES


def test_acceptance_manifest_matches_public_contract():
    manifest = _json("acceptance.json")
    assert manifest["schema_version"] == 1
    assert manifest["contract_id"] == GROUP1_ACCEPTANCE_CONTRACT_ID
    assert manifest["contract_version"] == GROUP1_ACCEPTANCE_CONTRACT_VERSION
    assert manifest["product_contract_id"] == PRODUCT_CONTRACT_ID
    assert manifest["product_contract_version"] == PRODUCT_CONTRACT_VERSION
    assert manifest["canonical_stream_contract_id"] == CANONICAL_STREAM_CONTRACT_ID
    assert manifest["canonical_stream_contract_version"] == CANONICAL_STREAM_CONTRACT_VERSION
    assert manifest["determinism_profile"] == DETERMINISM_PROFILE
    assert tuple(manifest["source_kinds"]) == M1_SOURCE_KINDS
    assert tuple(manifest["objective_kinds"]) == DETERMINISTIC_V1_OBJECTIVE_KINDS
    assert tuple(manifest["row_schema_kinds"]) == V1_ROW_SCHEMA_KINDS
    assert tuple(manifest["owned_stages"]) == VERIFORMIS_OWNED_STAGES


def test_acceptance_sources_are_hash_pinned():
    inventory = _manifest_json("source_inventory")
    assert inventory["schema_version"] == 1
    for source in inventory["sources"]:
        relative = Path(source["path"])
        assert not relative.is_absolute()
        assert ".." not in relative.parts
        path = FIXTURE_ROOT / relative
        payload = path.read_bytes()
        assert len(payload) == source["size"]
        assert hashlib.sha256(payload).hexdigest() == source["sha256"]
        assert source["parser"] in {"text", "markdown", "docx"}


def test_acceptance_corpus_exercises_declared_source_boundaries():
    manifest = _json("acceptance.json")
    inventory = _manifest_json("source_inventory")
    stored_kinds = {source["source_kind"] for source in inventory["sources"]}
    generated_kinds = set(manifest["generated_source_kinds"])
    assert stored_kinds | generated_kinds == set(M1_SOURCE_KINDS)

    paths = [Path(source["path"]) for source in inventory["sources"]]
    source_paths = [path for path in paths if path.parent.name in {"markdown", "text"}]
    assert [path.stem for path in source_paths].count("source") == 2

    duplicate_hashes = [
        source["sha256"]
        for source in inventory["sources"]
        if "duplicate-" in source["path"]
    ]
    assert len(duplicate_hashes) == 2
    assert len(set(duplicate_hashes)) == 1
    assert manifest["generated_source_kinds"] == ["docx"]


def test_canonical_stream_golden_files_match_current_supported_parsers():
    inventory = _manifest_json("source_inventory")
    expected = _manifest_json("canonical_streams")
    assert expected["canonical_stream_contract_version"] == CANONICAL_STREAM_CONTRACT_VERSION

    for source in inventory["sources"]:
        path = FIXTURE_ROOT / source["path"]
        if source["parser"] == "markdown":
            result = parse_md_file(path, logical_path=source["path"])
        elif source["parser"] == "text" and source["source_kind"] == "code":
            result = parse_text(
                path,
                language=path.suffix.lstrip("."),
                logical_path=source["path"],
            )
        elif source["parser"] == "text":
            result = parse_text(path, logical_path=source["path"])
        else:
            raise AssertionError(f"unsupported fixture parser: {source['parser']}")
        golden = expected["streams"][source["path"]]
        assert result.source.extracted_text == golden["text"]
        digest = hashlib.sha256(result.source.extracted_text.encode("utf-8")).hexdigest()
        assert digest == golden["sha256"]


def test_generated_docx_is_byte_deterministic_and_hash_pinned():
    manifest = _json("acceptance.json")
    generated = manifest["generated_sources"]
    assert len(generated) == 1
    descriptor = generated[0]
    first = _generated_docx_bytes()
    second = _generated_docx_bytes()

    assert first == second
    assert len(first) == descriptor["size"]
    assert hashlib.sha256(first).hexdigest() == descriptor["sha256"]
    assert descriptor["parser"] == "docx"

    result = parse_docx_file(
        descriptor["path"],
        logical_path=descriptor["path"],
        raw_bytes=first,
    )
    golden = _manifest_json("canonical_streams")["streams"][descriptor["path"]]
    assert result.source.extracted_text == golden["text"]
    assert result.source.stream_sha256 == golden["sha256"]


def test_unsupported_acceptance_source_has_typed_located_loss_diagnostic():
    manifest = _json("acceptance.json")
    path = FIXTURE_ROOT / "raw/adversarial/unsupported.md"
    result = parse_md_file(path, logical_path=path.relative_to(FIXTURE_ROOT).as_posix())
    diagnostic = next(
        item
        for item in result.diagnostics.diagnostics
        if item.code == "markdown.html-block-omitted"
    )

    assert diagnostic.disposition == "omitted"
    assert diagnostic.loss_kind == "text"
    assert diagnostic.location.kind == "text"
    assert diagnostic.location.line_start == 1
    assert manifest["canonical_stream_contract_version"] == 1


def test_acceptance_manifest_pointers_and_required_digests_are_exact():
    manifest = _json("acceptance.json")
    for key in ("source_inventory", "canonical_streams"):
        relative = Path(manifest[key])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert (FIXTURE_ROOT / relative).is_file()
    assert manifest["required_reproducible_digests"] == [
        "source_inventory",
        "canonical_streams",
        "cleaning_plan",
        "candidate_records",
        "dataset_records",
        "split_assignment",
        "formatted_rows",
        "bundle_content",
    ]


def test_m1_1_requires_two_objectives_from_one_corpus():
    runs = _json("acceptance.json")["acceptance_runs"]
    assert {run["source_set"] for run in runs} == {"golden-corpus"}
    assert tuple(run["objective"] for run in runs) == M1_1_ACCEPTANCE_OBJECTIVE_KINDS
    assert tuple(run["row_schema"] for run in runs) == ("text", "prompt_completion")
