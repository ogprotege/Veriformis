"""Shared workspace fixtures, separate from collected tests."""

from unittest.mock import patch
from veriformis.contracts import (
    CONSTRUCTION_STAGE_SCHEMA_ID,
    CURATION_STAGE_SCHEMA_ID,
    FORMAT_STAGE_SCHEMA_ID,
    SEAL_STAGE_SCHEMA_ID,
    SPLIT_STAGE_SCHEMA_ID,
    VALIDATION_STAGE_SCHEMA_ID,
)
from veriformis.diagnostics import parse_report_to_dict
from veriformis.identity import (
    derive_id,
    lossless_json_bytes,
)
from veriformis.ir import document_to_dict
from veriformis.parsers.text import parse_text
from veriformis.workspace import (
    STAGES,
    SourceDescriptor,
)

_V3_STAGE_OUTPUTS = {
    "parse": {"registry": "source-registry"},
    "clean": {"transforms": "transform-records"},
    "chunk": {"chunks": "chunks"},
    "construct": {
        "recipe": "dataset-recipe",
        "result": "construction-result",
    },
    "curate": {
        "plan": "finished-dataset-plan",
        "result": "curation-result",
    },
    "split": {"result": "split-result"},
    "format": {
        "row-set": "formatted-row-set",
        "train": "training-partition",
        "evaluation": "evaluation-partition",
        "provenance": "row-provenance",
    },
    "validate": {
        "snapshot": "dataset-snapshot",
        "report": "dataset-validation-report",
    },
    "seal": {
        "manifest": "finished-bundle-manifest",
        "attestation": "finished-bundle-attestation",
    },
}

_V3_FINISHED_STAGE_SCHEMAS = {
    "curate": CURATION_STAGE_SCHEMA_ID,
    "split": SPLIT_STAGE_SCHEMA_ID,
    "format": FORMAT_STAGE_SCHEMA_ID,
    "validate": VALIDATION_STAGE_SCHEMA_ID,
    "seal": SEAL_STAGE_SCHEMA_ID,
}

def _synthetic_commit(transaction, **kwargs):
    """Bypass domain replay only; retain revision, output, and lineage checks."""
    with patch.object(transaction, "_validate_stage_semantics", return_value=None):
        return transaction.commit(**kwargs)

def _finished_plan_id(workspace):
    revision = workspace.head(verify_objects=False)
    curate = revision.stages["curate"]
    if curate.status == "complete":
        return curate.config["plan_id"]
    construct = revision.stages["construct"]
    assert construct.status == "complete"
    return derive_id(
        "fdp",
        {
            "schema_version": "veriformis.synthetic-finished-plan/v1",
            "recipe_id": construct.config["recipe_id"],
        },
    )

def _default_stage_config(workspace, stage, text=None):
    if stage == "parse":
        return {"sources": []}
    if stage == "clean":
        return {
            "rules": ["lowercase"]
            if text is not None
            else ["page-numbers", "whitespace"],
            "custom": None,
            "max_remove_ppm": 300_000,
        }
    if stage == "chunk":
        return {"strategy": "paragraph", "size": 1000, "overlap": 100}
    if stage == "construct":
        selected_source_ids = tuple(
            sorted(workspace.head(verify_objects=False).sources)
        )
        assert selected_source_ids, "synthetic construct requires a captured source"
        recipe_id = derive_id(
            "rcp",
            {
                "schema_version": "veriformis.synthetic-recipe/v1",
                "selected_source_ids": selected_source_ids,
            },
        )
        return {
            "schema_version": CONSTRUCTION_STAGE_SCHEMA_ID,
            "recipe_id": recipe_id,
            "selected_source_ids": list(selected_source_ids),
        }
    if stage in _V3_FINISHED_STAGE_SCHEMAS:
        return {
            "schema_version": _V3_FINISHED_STAGE_SCHEMAS[stage],
            "plan_id": _finished_plan_id(workspace),
        }
    raise AssertionError(f"unsupported synthetic stage {stage}")

def _commit_stage(
    workspace,
    stage,
    text=None,
    *,
    config=None,
    status="complete",
    lineage_forgery=None,
):
    payload = (text or stage).encode()
    stage_config = (
        _default_stage_config(workspace, stage, text) if config is None else config
    )
    with workspace.begin(stage) as transaction:
        if stage == "parse" and text is not None:
            source, outputs = _put_parsed_source(
                transaction,
                "source.txt",
                payload,
            )
            transaction.set_sources((source,))
            outputs["registry"] = _put_registry(transaction, (source,))
            return _synthetic_commit(
                transaction,
                outputs=outputs,
                config={"sources": ["source.txt"]},
                status=status,
            )
        schemas = dict(_V3_STAGE_OUTPUTS[stage])
        all_source_ids = tuple(sorted(transaction.sources))
        if stage == "clean":
            for source_id in all_source_ids:
                schemas.update(
                    {
                        f"source/{source_id}/document": "cleaned-document-ir",
                        f"source/{source_id}/cleaning-plan": "cleaning-plan",
                        f"source/{source_id}/block-derivations": ("block-derivations"),
                    }
                )
        if stage == "construct":
            stage_source_ids = tuple(stage_config["selected_source_ids"])
        elif stage in {"curate", "split", "format", "validate", "seal"}:
            stage_source_ids = tuple(
                transaction.base.stages["construct"].config["selected_source_ids"]
            )
        else:
            stage_source_ids = all_source_ids
        if stage == "parse":
            producer_id, artifact_config = (
                "veriformis.parse-stage",
                {"source_count": len(all_source_ids)},
            )
        elif stage == "clean":
            producer_id, artifact_config = "veriformis.cleaning", stage_config
        elif stage == "chunk":
            producer_id, artifact_config = (
                f"veriformis.chunker.{stage_config['strategy']}",
                stage_config,
            )
        else:
            producer_id, artifact_config = None, stage_config
        outputs = {}
        for name, kind in schemas.items():
            expected_producer = (
                producer_id
                if producer_id is not None
                else {
                    "construct": f"veriformis.construction.{name}",
                    "curate": f"veriformis.curation.{name}",
                    "split": f"veriformis.splitting.{name}",
                    "format": f"veriformis.dataset-serializer.{name}",
                    "validate": f"veriformis.dataset-validation.{name}",
                    "seal": f"veriformis.bundle.{name}",
                }[stage]
            )
            output_producer = expected_producer
            output_version = "1"
            output_config = artifact_config
            if lineage_forgery is not None and name == lineage_forgery[0]:
                forgery = lineage_forgery[1]
                if forgery == "producer":
                    output_producer = "forged.producer"
                elif forgery == "version":
                    output_version = "999"
                elif forgery == "config":
                    output_config = {**artifact_config, "forged": True}
                else:  # pragma: no cover - test helper contract
                    raise AssertionError(f"unknown lineage forgery {forgery}")
            outputs[name] = transaction.put_artifact(
                (
                    b"[]"
                    if (stage, name)
                    in {
                        ("parse", "registry"),
                        ("clean", "transforms"),
                        ("chunk", "chunks"),
                        ("format", "provenance"),
                    }
                    else payload + name.encode()
                ),
                kind=kind,
                media_type="application/octet-stream",
                source_ids=(
                    (name.split("/")[1],)
                    if name.startswith("source/")
                    else stage_source_ids
                ),
                producer_id=output_producer,
                producer_version=output_version,
                config=output_config,
            )
        return _synthetic_commit(
            transaction,
            outputs=outputs,
            config=stage_config,
            status=status,
        )

def _complete_pipeline(workspace):
    for stage in STAGES:
        _commit_stage(
            workspace,
            stage,
            "captured source" if stage == "parse" else None,
        )

def _put_parsed_source(transaction, logical_path, raw, *, original_path=None):
    parsed = parse_text(
        original_path or logical_path,
        logical_path=logical_path,
        raw_bytes=raw,
    )
    source_id = parsed.source.id
    parser_config = {
        "parser": parsed.source.parser,
        "parser_version": parsed.source.parser_version,
        "canonical_stream_contract_version": (
            parsed.source.canonical_stream_contract_version
        ),
    }
    artifacts = {
        "raw": transaction.put_artifact(
            raw,
            kind="raw-source",
            media_type="application/octet-stream",
            source_ids=(source_id,),
            producer_id="veriformis.source-capture",
            producer_version="1",
            config={"logical_path": logical_path},
        ),
        "canonical": transaction.put_artifact(
            parsed.source.extracted_text,
            kind="canonical-source-text",
            media_type="text/plain",
            source_ids=(source_id,),
            producer_id="veriformis.parser.text",
            producer_version=parsed.source.parser_version,
            config=parser_config,
        ),
        "document": transaction.put_artifact(
            lossless_json_bytes(document_to_dict(parsed.document)),
            kind="document-ir",
            media_type="application/json",
            source_ids=(source_id,),
            producer_id="veriformis.parser.text",
            producer_version=parsed.source.parser_version,
            config=parser_config,
        ),
        "diagnostics": transaction.put_artifact(
            lossless_json_bytes(parse_report_to_dict(parsed.diagnostics)),
            kind="parse-report",
            media_type="application/json",
            source_ids=(source_id,),
            producer_id="veriformis.parser.text",
            producer_version=parsed.source.parser_version,
            config=parser_config,
        ),
    }
    source = SourceDescriptor.create(
        logical_path=logical_path,
        original_path=original_path,
        sha256=parsed.source.sha256,
        size=len(raw),
        parser_id=parsed.source.parser,
        parser_version=parsed.source.parser_version,
        raw_artifact_id=artifacts["raw"].id,
        extracted_artifact_id=artifacts["canonical"].id,
        document_artifact_id=artifacts["document"].id,
    )
    outputs = {
        f"source/{source_id}/{role}": artifact for role, artifact in artifacts.items()
    }
    return source, outputs

def _put_registry(transaction, sources, *, payload=None):
    if payload is None:
        payload = lossless_json_bytes(
            [
                source.model_dump(mode="json", exclude={"original_path"})
                for source in sorted(sources, key=lambda item: item.id)
            ]
        )
    return transaction.put_artifact(
        payload,
        kind="source-registry",
        media_type="application/json",
        source_ids=tuple(source.id for source in sources),
        producer_id="veriformis.parse-stage",
        producer_version="1",
        config={"source_count": len(sources)},
    )
