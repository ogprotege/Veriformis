"""Source registration: every ingested file gets a hash-pinned identity."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from veriformis.contracts import CANONICAL_STREAM_CONTRACT_VERSION
from veriformis.diagnostics import ParseReport, make_parse_report
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    derive_source_id,
    normalize_logical_path,
    sha256_digest,
)


@dataclass(frozen=True)
class SourceRef:
    id: str
    path: str
    sha256: str
    size: int
    parser: str
    extracted_text: str  # in-session only; spans index into this stream
    logical_path: str = ""
    parser_version: str = "1"
    canonical_stream_contract_version: int = CANONICAL_STREAM_CONTRACT_VERSION
    stream_sha256: str = ""
    artifact_id: str = ""


@dataclass(frozen=True)
class ParseResult:
    document: "object"  # veriformis.ir.Document (avoid import cycle at type level)
    source: SourceRef
    diagnostics: ParseReport


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_source(
    path: str | Path,
    parser: str,
    extracted_text: str,
    *,
    logical_path: str,
    parser_version: str = "1",
    canonical_stream_contract_version: int = CANONICAL_STREAM_CONTRACT_VERSION,
    raw_bytes: bytes | None = None,
) -> SourceRef:
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    digest = hashlib.sha256(captured).hexdigest()
    locator = normalize_logical_path(logical_path)
    source_id = derive_source_id(locator, digest)
    stream_digest = sha256_digest(extracted_text)
    config_digest = canonical_digest(
        {
            "parser": parser,
            "parser_version": parser_version,
            "canonical_stream_contract_version": canonical_stream_contract_version,
        }
    )
    return SourceRef(
        id=source_id,
        path=str(p),
        sha256=digest,
        size=len(captured),
        parser=parser,
        extracted_text=extracted_text,
        logical_path=locator,
        parser_version=parser_version,
        canonical_stream_contract_version=canonical_stream_contract_version,
        stream_sha256=stream_digest,
        artifact_id=derive_artifact_id(
            kind="canonical-source-text",
            content_sha256=stream_digest,
            source_ids=(source_id,),
            producer_id=f"veriformis.parser.{parser}",
            producer_version=parser_version,
            config_digest=config_digest,
        ),
    )


def empty_parse_report(source: SourceRef) -> ParseReport:
    return make_parse_report(
        source_id=source.id,
        parser_name=source.parser,
        parser_version=source.parser_version,
    )
