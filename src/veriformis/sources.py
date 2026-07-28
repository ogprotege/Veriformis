"""Source registration: every ingested file gets a hash-pinned identity."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceRef:
    id: str
    path: str
    sha256: str
    size: int
    parser: str
    extracted_text: str  # in-session only; spans index into this stream


@dataclass
class ParseResult:
    document: "object"  # veriformis.ir.Document (avoid import cycle at type level)
    source: SourceRef


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_source(path: str | Path, parser: str, extracted_text: str) -> SourceRef:
    p = Path(path)
    digest = sha256_file(p)
    return SourceRef(
        id=f"src-{digest[:12]}",
        path=str(p),
        sha256=digest,
        size=p.stat().st_size,
        parser=parser,
        extracted_text=extracted_text,
    )
