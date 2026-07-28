"""Chunk → training-record serializers."""
from __future__ import annotations

from veriformis.chunkers.base import Chunk


def serialize_completion(chunks: list[Chunk], *, include_heading_path: bool = False) -> list[dict]:
    records = []
    for chunk in chunks:
        text = chunk.text
        if include_heading_path and chunk.heading_path:
            text = " > ".join(chunk.heading_path) + "\n\n" + text
        records.append({"text": text})
    return records


def serialize_instruction(chunks: list[Chunk], *, instruction: str) -> list[dict]:
    return [
        {
            "instruction": instruction,
            "input": " > ".join(chunk.heading_path),
            "output": chunk.text,
        }
        for chunk in chunks
    ]
