# src/veriformis/bundle/writer.py
"""Bundle writing and sealing. Fail-closed: a failed gate means no bundle."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import veriformis
from veriformis.bundle.manifest import (
    ChunkEntry, DatasetInfo, Manifest, SourceEntry, SpanEntry, TransformEntry, ValidationEntry,
)
from veriformis.errors import GateFailure


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bundle(
    out_dir,
    *,
    records: list[dict],
    chunks,
    sources,
    transforms,
    validations,
    format: str,
    template: str | None,
) -> Path:
    failed = [v for v in validations if not v.passed]
    if failed:
        raise GateFailure(
            "bundle refused: failed gates: " + ", ".join(v.gate for v in failed)
        )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)

    dataset_path = out / "dataset.jsonl"
    with dataset_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = Manifest(
        bundle_id=uuid.uuid4().hex,
        created_at=datetime.now(UTC).isoformat(),
        veriformis_version=veriformis.__version__,
        sources=[
            SourceEntry(id=s.id, path=s.path, sha256=s.sha256, size=s.size, parser=s.parser)
            for s in sources
        ],
        transforms=[
            TransformEntry(
                rule=t.rule, params=t.params, block_index=t.block_index,
                edits=t.edits, bytes_removed=t.bytes_removed, warned=t.warned,
            )
            for t in transforms
        ],
        chunks=[
            ChunkEntry(
                id=c.id, source_id=c.source_id, block_index=c.block_index,
                span=SpanEntry(start=c.span.start, end=c.span.end, page=c.span.page) if c.span else None,
                heading_path=c.heading_path, tokens_est=c.tokens_est, transformed=c.transformed,
            )
            for c in chunks
        ],
        dataset=DatasetInfo(
            format=format,
            template=template,
            record_count=len(records),
            total_chars=sum(len(r.get("text") or r.get("output", "")) for r in records),
            total_tokens_est=sum(c.tokens_est for c in chunks),
        ),
        validations=[
            ValidationEntry(gate=v.gate, passed=v.passed, messages=v.messages)
            for v in validations
        ],
        files={"dataset.jsonl": _sha256(dataset_path)},
    )
    manifest_path = out / "manifest.json"
    manifest.files["manifest.json"] = "pending"  # placeholder replaced below
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    manifest.files["manifest.json"] = _sha256(manifest_path)
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return out


def verify_bundle(bundle_dir) -> bool:
    out = Path(bundle_dir)
    manifest = Manifest.model_validate_json((out / "manifest.json").read_text(encoding="utf-8"))
    for rel, digest in manifest.files.items():
        path = out / rel
        if not path.exists():
            return False
        if rel == "manifest.json":
            continue  # self-hash is informational only
        if _sha256(path) != digest:
            return False
    return True
