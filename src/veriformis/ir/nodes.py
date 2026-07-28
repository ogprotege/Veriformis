"""Canonical document IR. Every block may carry provenance (Span + block_index)
pointing into the source's extracted-text stream."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union


@dataclass
class Span:
    start: int
    end: int
    page: int | None = None


# ---- inline nodes ----
@dataclass
class Text:
    value: str


@dataclass
class Bold:
    children: list[Inline] = field(default_factory=list)


@dataclass
class Italic:
    children: list[Inline] = field(default_factory=list)


@dataclass
class Strikethrough:
    children: list[Inline] = field(default_factory=list)


@dataclass
class Superscript:
    children: list[Inline] = field(default_factory=list)


@dataclass
class Subscript:
    children: list[Inline] = field(default_factory=list)


@dataclass
class Code:
    value: str


@dataclass
class Link:
    children: list[Inline] = field(default_factory=list)
    href: str = ""
    title: str | None = None


@dataclass
class Image:
    alt: str = ""
    src: str = ""
    title: str | None = None
    span: Span | None = None
    block_index: int = -1


@dataclass
class LineBreak:
    pass


@dataclass
class FootnoteRef:
    id: str


@dataclass
class EndnoteRef:
    id: str


@dataclass
class Math:
    source: str
    display: bool = False
    span: Span | None = None
    block_index: int = -1


@dataclass
class Citation:
    key: str
    locator: str | None = None


Inline = Union[
    Text, Bold, Italic, Strikethrough, Superscript, Subscript, Code,
    Link, Image, LineBreak, FootnoteRef, EndnoteRef, Math, Citation,
]


# ---- block nodes ----
@dataclass
class Heading:
    level: int
    children: list[Inline] = field(default_factory=list)
    span: Span | None = None
    block_index: int = -1


@dataclass
class Paragraph:
    children: list[Inline] = field(default_factory=list)
    span: Span | None = None
    block_index: int = -1


@dataclass
class CodeBlock:
    text: str
    language: str | None = None
    span: Span | None = None
    block_index: int = -1


@dataclass
class Blockquote:
    children: list[Block] = field(default_factory=list)
    span: Span | None = None
    block_index: int = -1


@dataclass
class HorizontalRule:
    span: Span | None = None
    block_index: int = -1


@dataclass
class ListItem:
    children: list[Block] = field(default_factory=list)
    checked: bool | None = None


@dataclass
class ListBlock:
    ordered: bool
    items: list[ListItem] = field(default_factory=list)
    span: Span | None = None
    block_index: int = -1


@dataclass
class Cell:
    children: list[Inline] = field(default_factory=list)


Alignment = Literal["left", "center", "right", None]


@dataclass
class Table:
    headers: list[Cell] = field(default_factory=list)
    rows: list[list[Cell]] = field(default_factory=list)
    alignments: list[Alignment] = field(default_factory=list)
    span: Span | None = None
    block_index: int = -1


Block = Union[
    Heading, Paragraph, CodeBlock, Blockquote, HorizontalRule,
    ListBlock, Table, Image, Math,
]


@dataclass
class Footnote:
    id: str
    children: list[Block] = field(default_factory=list)


@dataclass
class Endnote:
    id: str
    children: list[Block] = field(default_factory=list)


@dataclass
class Document:
    children: list[Block] = field(default_factory=list)
    footnotes: dict[str, Footnote] = field(default_factory=dict)
    endnotes: dict[str, Endnote] = field(default_factory=dict)
    source_id: str = ""


def _inline_text(node: Inline) -> str:
    if isinstance(node, (Text, Code)):
        return node.value
    if isinstance(node, (Bold, Italic, Strikethrough, Superscript, Subscript, Link)):
        return "".join(_inline_text(c) for c in node.children)
    if isinstance(node, Math):
        return node.source
    if isinstance(node, LineBreak):
        return "\n"
    return ""  # Image, FootnoteRef, EndnoteRef, Citation contribute no text


def block_text(block: Block) -> str:
    """Plain-text content of a block."""
    if isinstance(block, CodeBlock):
        return block.text
    if isinstance(block, Math):
        return block.source
    if isinstance(block, Image):
        return block.alt
    if isinstance(block, (Heading, Paragraph)):
        return "".join(_inline_text(c) for c in block.children)
    if isinstance(block, Blockquote):
        return "\n\n".join(block_text(b) for b in block.children)
    if isinstance(block, ListBlock):
        return "\n".join(block_text(i) for i in block.items)
    if isinstance(block, ListItem):
        return "\n\n".join(block_text(b) for b in block.children)
    if isinstance(block, Table):
        rows = [["".join(_inline_text(c) for c in cell.children) for cell in row] for row in block.rows]
        header = ["".join(_inline_text(c) for c in cell.children) for cell in block.headers]
        return "\n".join("\t".join(r) for r in ([header] if header else []) + rows)
    return ""


def set_block_text(block: Block, text: str) -> Block:
    """Return a copy of `block` whose content is replaced by plain `text`.
    Provenance (span, block_index) is preserved. Rich inline structure of an
    edited block is intentionally flattened — the transform log records why."""
    if isinstance(block, CodeBlock):
        return CodeBlock(text=text, language=block.language, span=block.span, block_index=block.block_index)
    if isinstance(block, Heading):
        return Heading(level=block.level, children=[Text(text)], span=block.span, block_index=block.block_index)
    # Paragraph and any other block flatten to Paragraph
    return Paragraph(children=[Text(text)], span=block.span, block_index=block.block_index)
