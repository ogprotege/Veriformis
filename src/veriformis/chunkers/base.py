# src/veriformis/chunkers/base.py
"""Chunk model + shared helpers."""
from __future__ import annotations

import math
from dataclasses import dataclass

from veriformis.ir import Block, Heading, Span, block_text


@dataclass
class Chunk:
    id: str
    source_id: str
    block_index: int
    span: Span | None
    heading_path: list[str]
    text: str
    tokens_est: int
    transformed: bool = False


def est_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def heading_paths(blocks: list[Block]) -> list[list[str]]:
    """Heading path in effect at each block index (headings included, path = self)."""
    stack: list[tuple[int, str]] = []
    paths: list[list[str]] = []
    for block in blocks:
        if isinstance(block, Heading):
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block_text(block)))
        paths.append([title for _, title in stack])
    return paths


def make_chunk(
    seq: int, blocks: list[Block], text: str, *, source_id: str,
    heading_path: list[str], span: Span | None, transformed_blocks: set[int],
) -> Chunk:
    return Chunk(
        id=f"chk-{seq:04d}",
        source_id=source_id,
        block_index=blocks[0].block_index if blocks else -1,
        span=span,
        heading_path=heading_path,
        text=text,
        tokens_est=est_tokens(text),
        transformed=any(b.block_index in transformed_blocks for b in blocks),
    )


def flatten(blocks: list[Block]) -> str:
    """The canonical extracted stream (must equal parser-built streams)."""
    return "\n\n".join(block_text(b) for b in blocks)
