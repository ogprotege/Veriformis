# src/veriformis/cli.py
"""veriformis CLI: stage commands over a workspace directory.
(`veriformis run pipeline.yaml` is milestone M2 — intentionally absent.)"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import typer

import veriformis
from veriformis.chunkers.base import Chunk
from veriformis.chunkers.strategies import (
    chunk_fixed, chunk_paragraph, chunk_sentence, chunk_sliding, chunk_structure,
)
from veriformis.errors import UnsupportedInputError, VeriformisError
from veriformis.ir import Span, document_from_dict, document_to_dict
from veriformis.parsers.docx import parse_docx_file
from veriformis.parsers.markdown import parse_md_file
from veriformis.parsers.text import parse_text
from veriformis.rules.engine import TransformRecord, clean_document
from veriformis.rules.library import RULES, custom_regex, default_rules
from veriformis.serializers.chat import serialize_chat
from veriformis.serializers.formats import serialize_completion, serialize_instruction
from veriformis.sources import SourceRef
from veriformis.validate.gates import RECORD_SCHEMAS, run_gates

app = typer.Typer(help="Veriformis — local-first dataset compiler.")

_CODE_EXTS = {".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs", ".rb", ".sh"}
_STRATEGIES = {
    "paragraph": chunk_paragraph,
    "fixed": chunk_fixed,
    "sliding": chunk_sliding,
    "sentence": chunk_sentence,
    "structure": chunk_structure,
}


def _parse_one(path: Path):
    ext = path.suffix.lower()
    if ext == ".txt":
        return parse_text(path)
    if ext in (".md", ".markdown"):
        return parse_md_file(path)
    if ext == ".docx":
        return parse_docx_file(path)
    if ext in _CODE_EXTS:
        return parse_text(path, language=ext.lstrip("."))
    raise UnsupportedInputError(f"unsupported input type: {path.name}")


def _load_workspace(ws: Path):
    registry = {s["id"]: s for s in json.loads((ws / "registry.json").read_text())}
    docs = {}
    for ir_path in sorted(ws.glob("*.ir.json")):
        doc = document_from_dict(json.loads(ir_path.read_text()))
        docs[ir_path.name[: -len(".ir.json")]] = doc
    sources = {}
    for sid, entry in registry.items():
        stem = Path(entry["path"]).stem
        extracted = (ws / f"{stem}.extracted.txt").read_text(encoding="utf-8")
        sources[sid] = SourceRef(extracted_text=extracted, **entry)
    return docs, sources


@app.command()
def parse(paths: list[Path], out: Path = typer.Option(..., "-o")) -> None:
    """Ingest raw files into a workspace."""
    out.mkdir(parents=True, exist_ok=True)
    registry = []
    try:
        for path in paths:
            result = _parse_one(path)
            stem = path.stem
            (out / f"{stem}.ir.json").write_text(json.dumps(document_to_dict(result.document)))
            (out / f"{stem}.extracted.txt").write_text(result.source.extracted_text, encoding="utf-8")
            entry = asdict(result.source)
            del entry["extracted_text"]
            registry.append(entry)
    except VeriformisError as exc:
        typer.echo(f"error[{exc.code}]: {exc.message}", err=True)
        raise typer.Exit(code=2) from exc
    (out / "registry.json").write_text(json.dumps(registry, indent=2))
    typer.echo(f"parsed {len(registry)} source(s) into {out}")


@app.command()
def clean(
    workspace: Path,
    rules: str = typer.Option("", "--rules"),
    custom: str = typer.Option("", "--custom"),
) -> None:
    """Apply cleaning rules to every document in the workspace."""
    selected = default_rules() if not rules and not custom else []
    if rules:
        for name in rules.split(","):
            if name not in RULES:
                typer.echo(f"unknown rule: {name} (have: {sorted(RULES)})", err=True)
                raise typer.Exit(code=2)
            selected.append(RULES[name]())
    if custom:
        selected.append(custom_regex(custom))
    docs, _ = _load_workspace(workspace)
    transforms = []
    for stem, doc in docs.items():
        cleaned, records, warnings = clean_document(doc, selected)
        for warning in warnings:
            typer.echo(f"warning: {warning}", err=True)
        (workspace / f"{stem}.ir.json").write_text(json.dumps(document_to_dict(cleaned)))
        transforms.extend(asdict(r) for r in records)
    (workspace / "transforms.json").write_text(json.dumps(transforms, indent=2))
    typer.echo(f"cleaned {len(docs)} document(s); {len(transforms)} transform record(s)")


@app.command()
def chunk(
    workspace: Path,
    strategy: str = typer.Option("paragraph", "--strategy"),
    size: int = typer.Option(1000, "--size"),
    overlap: int = typer.Option(100, "--overlap"),
) -> None:
    """Chunk workspace documents with the chosen strategy."""
    if strategy not in _STRATEGIES:
        typer.echo(f"unknown strategy: {strategy} (have: {sorted(_STRATEGIES)})", err=True)
        raise typer.Exit(code=2)
    docs, _ = _load_workspace(workspace)
    transformed: set[int] = set()
    t_path = workspace / "transforms.json"
    if t_path.exists():
        transformed = {t["block_index"] for t in json.loads(t_path.read_text())}
    chunks: list[dict] = []
    fn = _STRATEGIES[strategy]
    for doc in docs.values():
        made = fn(doc.children, max_size=size, source_id=doc.source_id, transformed=transformed) \
            if strategy in ("paragraph", "sentence", "structure") \
            else fn(doc.children, size=size, overlap=overlap, source_id=doc.source_id, transformed=transformed)
        chunks.extend(asdict(c) for c in made)
    (workspace / "chunks.json").write_text(json.dumps(chunks, indent=2))
    typer.echo(f"wrote {len(chunks)} chunk(s)")


@app.command(name="format")
def format_cmd(
    workspace: Path,
    format: str = typer.Option(..., "--format"),
    template: str = typer.Option("llama3", "--template"),
    instruction: str = typer.Option("", "--instruction"),
    with_heading_path: bool = typer.Option(False, "--with-heading-path"),
) -> None:
    """Serialize chunks into training records (records.jsonl)."""
    raw = json.loads((workspace / "chunks.json").read_text())
    chunks = [
        Chunk(
            id=c["id"], source_id=c["source_id"], block_index=c["block_index"],
            span=Span(**c["span"]) if c["span"] else None,
            heading_path=c["heading_path"], text=c["text"],
            tokens_est=c["tokens_est"], transformed=c["transformed"],
        )
        for c in raw
    ]
    if format == "completion":
        records = serialize_completion(chunks, include_heading_path=with_heading_path)
    elif format == "instruction":
        if not instruction:
            typer.echo("--instruction is required for instruction format", err=True)
            raise typer.Exit(code=2)
        records = serialize_instruction(chunks, instruction=instruction)
    elif format == "chat":
        records = serialize_chat(
            [{"user": "Summarize the following.", "assistant": c.text} for c in chunks],
            template=template,
        )
    else:
        typer.echo(f"unknown format: {format}", err=True)
        raise typer.Exit(code=2)
    with (workspace / "records.jsonl").open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    meta = {"format": format, "template": template if format == "chat" else None}
    (workspace / "records.meta.json").write_text(json.dumps(meta))
    typer.echo(f"wrote {len(records)} record(s)")


@app.command()
def validate(workspace: Path, format: str = typer.Option(..., "--format")) -> None:
    """Run validation gates; exits 1 if any gate fails."""
    if format not in RECORD_SCHEMAS:
        typer.echo(f"unknown format: {format} (have: {sorted(RECORD_SCHEMAS)})", err=True)
        raise typer.Exit(code=2)
    _, sources = _load_workspace(workspace)
    raw = json.loads((workspace / "chunks.json").read_text())
    chunks = [
        Chunk(
            id=c["id"], source_id=c["source_id"], block_index=c["block_index"],
            span=Span(**c["span"]) if c["span"] else None,
            heading_path=c["heading_path"], text=c["text"],
            tokens_est=c["tokens_est"], transformed=c["transformed"],
        )
        for c in raw
    ]
    records = [json.loads(line) for line in (workspace / "records.jsonl").read_text().splitlines() if line.strip()]
    results = run_gates(records, format, chunks, sources)
    (workspace / "validations.json").write_text(json.dumps([asdict(r) for r in results], indent=2))
    for result in results:
        typer.echo(f"{result.gate}: {'PASS' if result.passed else 'FAIL'}")
    if not all(r.passed for r in results):
        raise typer.Exit(code=1)


@app.command()
def seal(workspace: Path, out: Path = typer.Option(..., "-o")) -> None:
    """Seal the workspace into a verified .vfbundle."""
    from veriformis.bundle.writer import write_bundle

    _, sources = _load_workspace(workspace)
    records = [json.loads(line) for line in (workspace / "records.jsonl").read_text().splitlines() if line.strip()]
    raw_chunks = json.loads((workspace / "chunks.json").read_text())
    chunks = [
        Chunk(
            id=c["id"], source_id=c["source_id"], block_index=c["block_index"],
            span=Span(**c["span"]) if c["span"] else None,
            heading_path=c["heading_path"], text=c["text"],
            tokens_est=c["tokens_est"], transformed=c["transformed"],
        )
        for c in raw_chunks
    ]
    transforms = [TransformRecord(**t) for t in json.loads((workspace / "transforms.json").read_text())] \
        if (workspace / "transforms.json").exists() else []
    from veriformis.validate.gates import GateResult

    validations = [GateResult(**v) for v in json.loads((workspace / "validations.json").read_text())]
    meta_path = workspace / "records.meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"format": "completion", "template": None}
    try:
        bundle = write_bundle(
            out, records=records, chunks=chunks, sources=list(sources.values()),
            transforms=transforms, validations=validations,
            format=meta["format"], template=meta.get("template"),
        )
    except VeriformisError as exc:
        typer.echo(f"error[{exc.code}]: {exc.message}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"sealed bundle: {bundle}")


@app.command()
def preview(path: Path, rules: str = typer.Option("", "--rules")) -> None:
    """Dry-run cleaning on one file; prints the log; writes nothing."""
    result = _parse_one(path)
    if rules:
        unknown = [n for n in rules.split(",") if n not in RULES]
        if unknown:
            typer.echo(f"unknown rule(s): {', '.join(unknown)} (have: {sorted(RULES)})", err=True)
            raise typer.Exit(code=2)
    selected = default_rules() if not rules else [RULES[n]() for n in rules.split(",")]
    text = result.source.extracted_text  # the whole file, not just the first block
    from veriformis.rules.engine import apply_rules

    cleaned, records, warnings = apply_rules(text, selected)
    for record in records:
        typer.echo(f"{record.rule}: {record.edits} edit(s), {record.bytes_removed} byte(s) removed")
    for warning in warnings:
        typer.echo(f"warning: {warning}")
    typer.echo("--- before ---")
    typer.echo(text[:400])
    typer.echo("--- after ---")
    typer.echo(cleaned[:400])


@app.command()
def version() -> None:
    typer.echo(veriformis.__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
