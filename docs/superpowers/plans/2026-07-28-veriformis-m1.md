# Veriformis M1 — Core Engine + CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Veriformis core dataset-compilation engine (IR → parse → clean → chunk → serialize → validate → seal) plus a stage-command CLI, with a test suite that makes "lossless" a provable claim.

**Architecture:** One Python package (`src/` layout). A canonical document IR with char-level provenance; per-format parsers emit IR; deterministic cleaning rules log every mutation; chunkers carry provenance forward; serializers emit training JSONL (completion/instruction/chat via Jinja2 templates matching HF `chat_template` conventions); validation gates fail closed; the bundle sealer writes `dataset.jsonl` + `manifest.json` with SHA-256 hashes.

**Tech Stack:** Python ≥3.11, uv, setuptools src-layout, pydantic v2, typer, Jinja2, markdown-it-py + mdit-py-plugins, python-docx + lxml, pytest, ruff ==0.16.0.

## Global Constraints

- Python `>=3.11`; package `veriformis`; src layout; console script `veriformis = "veriformis.cli:main"`; version attr `veriformis.__version__`.
- Dependency floor pins: `markdown-it-py>=3.0`, `mdit-py-plugins>=0.4`, `python-docx>=1.1`, `lxml>=4.9`, `pydantic>=2.10,<3`, `typer>=0.12`, `jinja2>=3.1`; dev: `pytest>=8.0`, `ruff==0.16.0`.
- Ruff policy mirrors Aptus: `[tool.ruff] required-version = "==0.16.0"`, lint `select = ["E4","E7","E9","F"]`.
- **Privacy (absolute):** the owner's private MD↔DOCX conversion library must never be named or referred to anywhere in this repo — not in code, comments, docstrings, identifiers, env vars, docs, commit messages, or this plan's committed text. Tasks 4–5 vendor code from it; the local checkout path is supplied at execution time via the `PRIVATE_LIB` env var and is intentionally not recorded here. Vendored files must be scrubbed of all source-identifying strings (the source project's name, its `*.io` side-car XML namespace, its `*_IMAGE_CACHE` env var, its docstring self-references) and verified with grep.
- Deterministic only: no LLM calls, no network access anywhere in M1.
- English-language heuristics only; no OCR; scanned/no-text-layer inputs must fail closed (M2 PDF work — out of M1 scope).
- No PyMuPDF (AGPL) — M2 PDF parser must use pypdfium2 (not in M1 scope, noted to prevent accidental adoption).
- MIT license; conventional commits; every commit must pass `ruff check` and `pytest`.
- `veriformis run pipeline.yaml` is explicitly **M2** — M1 CLI exposes stage commands only.
- `aptus-dataset.json` bundle descriptor is explicitly **M5** (Aptus contract not yet read) — M1 bundle writes `dataset.jsonl` + `manifest.json` + optional `sources/` only.

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.github/workflows/ci.yml`, `src/veriformis/__init__.py`
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: nothing.
- Produces: importable `veriformis` package; `veriformis.__version__: str`; uv-locked env; CI running ruff + pytest.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scaffold.py
import veriformis


def test_package_imports_and_has_version():
    assert isinstance(veriformis.__version__, str)
    assert veriformis.__version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_scaffold.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis'`

- [ ] **Step 3: Write the scaffold**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "veriformis"
dynamic = ["version"]
description = "Local-first dataset compiler: raw documents to validated, provenance-sealed fine-tuning bundles"
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
keywords = ["dataset", "fine-tuning", "llm", "provenance", "jsonl"]
classifiers = [
  "Development Status :: 3 - Alpha",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
]
dependencies = [
  "markdown-it-py>=3.0",
  "mdit-py-plugins>=0.4",
  "python-docx>=1.1",
  "lxml>=4.9",
  "pydantic>=2.10,<3",
  "typer>=0.12",
  "jinja2>=3.1",
]

[project.optional-dependencies]
test = ["pytest>=8.0", "ruff==0.16.0"]

[project.scripts]
veriformis = "veriformis.cli:main"

[project.urls]
Repository = "https://github.com/ogprotege/Veriformis"
Issues = "https://github.com/ogprotege/Veriformis/issues"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.dynamic]
version = { attr = "veriformis.__version__" }

[tool.setuptools.package-data]
veriformis = ["serializers/templates/chat/*.jinja"]

[tool.ruff]
required-version = "==0.16.0"
extend-exclude = [".venv"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F"]

[tool.coverage.run]
source = ["veriformis"]

[tool.coverage.report]
show_missing = true
```

```python
# src/veriformis/__init__.py
"""Veriformis: local-first dataset compiler for LLM fine-tuning."""

__version__ = "0.1.0"
```

```gitignore
# .gitignore
.venv/
__pycache__/
*.egg-info/
*.pyc
.coverage
htmlcov/
dist/
build/
.pytest_cache/
.ruff_cache/
```

```yaml
# .github/workflows/ci.yml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv python install 3.12
      - run: uv sync --extra test
      - run: uv run ruff check src tests
      - run: uv run pytest -q
```

- [ ] **Step 4: Set up env, run test to verify it passes**

Run: `uv lock && uv sync --extra test && uv run pytest tests/test_scaffold.py -v`
Expected: PASS (1 passed). Also `uv run ruff check src tests` → no findings.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore .github/workflows/ci.yml src/veriformis/__init__.py tests/test_scaffold.py uv.lock
git commit -m "feat: project scaffold (src layout, uv, ruff, pytest, CI)"
```

---

### Task 2: Document IR with provenance

**Files:**
- Create: `src/veriformis/ir/__init__.py`, `src/veriformis/ir/nodes.py`, `src/veriformis/ir/serde.py`
- Test: `tests/ir/test_nodes_serde.py`

**Interfaces:**
- Consumes: nothing.
- Produces (used by Tasks 3–12):
  - `Span(start: int, end: int, page: int | None = None)` — offsets into the source's extracted-text stream.
  - Inline: `Text(value)`, `Bold(children)`, `Italic(children)`, `Strikethrough(children)`, `Superscript(children)`, `Subscript(children)`, `Code(value)`, `Link(children, href, title)`, `Image(alt, src, title)`, `LineBreak()`, `FootnoteRef(id)`, `EndnoteRef(id)`, `Math(source, display=False)`, `Citation(key, locator=None)`; union alias `Inline`.
  - Blocks (each has `span: Span | None = None` and `block_index: int = -1`): `Heading(level, children)`, `Paragraph(children)`, `CodeBlock(text, language=None)`, `Blockquote(children)`, `HorizontalRule()`, `ListBlock(ordered, items)`, `ListItem(children, checked=None)`, `Table(headers, rows, alignments)`, `Cell(children)`; union alias `Block` (also includes `Image`, `Math`).
  - `Footnote(id, children)`, `Endnote(id, children)`.
  - `Document(children, footnotes={}, endnotes={}, source_id="")`.
  - `document_to_dict(doc: Document) -> dict`; `document_from_dict(d: dict) -> Document` — JSON-safe roundtrip.
  - `block_text(block: Block) -> str` — plain-text content of a block (concatenated inline values).
  - `set_block_text(block: Block, text: str) -> Block` — returns the block with its inline content replaced by a single `Text` span (preserves type for `Paragraph`, `Heading`, `CodeBlock`, `Cell`; used by the cleaning stage).

- [ ] **Step 1: Write the failing test**

```python
# tests/ir/test_nodes_serde.py
from veriformis.ir.nodes import Document, Heading, Paragraph, Span, Text, block_text, set_block_text
from veriformis.ir.serde import document_from_dict, document_to_dict


def _doc():
    return Document(
        children=[
            Heading(level=1, children=[Text("Title")], span=Span(0, 5), block_index=0),
            Paragraph(children=[Text("Body text.")], span=Span(7, 17), block_index=1),
        ],
        source_id="src-1",
    )


def test_serde_roundtrip():
    doc = _doc()
    assert document_from_dict(document_to_dict(doc)) == doc


def test_block_text_and_set_block_text():
    para = _doc().children[1]
    assert block_text(para) == "Body text."
    replaced = set_block_text(para, "Cleaned.")
    assert block_text(replaced) == "Cleaned."
    assert type(replaced) is Paragraph
    assert replaced.span == para.span  # provenance preserved through cleaning
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ir/test_nodes_serde.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.ir'`

- [ ] **Step 3: Write the implementation**

```python
# src/veriformis/ir/nodes.py
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
```

```python
# src/veriformis/ir/serde.py
"""JSON-safe serialization for the IR (roundtrip: from_dict(to_dict(doc)) == doc)."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from veriformis.ir import nodes


def _node_to_dict(node: Any) -> dict:
    out: dict[str, Any] = {"type": type(node).__name__}
    for f in fields(node):
        out[f.name] = _value_to_json(getattr(node, f.name))
    return out


def _value_to_json(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _node_to_dict(value)
    if isinstance(value, list):
        return [_value_to_json(v) for v in value]
    if isinstance(value, dict):
        return {k: _value_to_json(v) for k, v in value.items()}
    return value


def document_to_dict(doc: nodes.Document) -> dict:
    return _node_to_dict(doc)


def _node_from_dict(d: dict) -> Any:
    d = dict(d)
    tag = d.pop("type")
    cls = getattr(nodes, tag)
    kwargs = {k: _value_from_json(v) for k, v in d.items()}
    return cls(**kwargs)


def _value_from_json(value: Any) -> Any:
    if isinstance(value, dict) and "type" in value:
        return _node_from_dict(value)
    if isinstance(value, dict):
        return {k: _value_from_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_value_from_json(v) for v in value]
    return value


def document_from_dict(d: dict) -> nodes.Document:
    doc = _node_from_dict(d)
    assert isinstance(doc, nodes.Document)
    return doc
```

```python
# src/veriformis/ir/__init__.py
from veriformis.ir.nodes import (  # noqa: F401
    Block, Blockquote, Bold, Cell, Citation, Code, CodeBlock, Document,
    Endnote, EndnoteRef, Footnote, FootnoteRef, Heading, HorizontalRule,
    Image, Inline, Italic, LineBreak, Link, ListBlock, ListItem, Math,
    Paragraph, Span, Strikethrough, Subscript, Superscript, Table, Text,
    block_text, set_block_text,
)
from veriformis.ir.serde import document_from_dict, document_to_dict  # noqa: F401
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/ir/test_nodes_serde.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/ir tests/ir
git commit -m "feat(ir): canonical document IR with provenance spans + JSON serde"
```

---

### Task 3: Source registry + plain-text/code parser

**Files:**
- Create: `src/veriformis/sources.py`, `src/veriformis/parsers/__init__.py`, `src/veriformis/parsers/text.py`
- Test: `tests/parsers/test_text.py`

**Interfaces:**
- Consumes: Task 2 IR.
- Produces (used by Tasks 4–12):
  - `SourceRef(id: str, path: str, sha256: str, size: int, parser: str, extracted_text: str)` — `id` is `"src-" + sha256[:12]`; `extracted_text` is the in-session text stream that all `Span` offsets index into.
  - `ParseResult(document: Document, source: SourceRef)` — every parser returns this; `document.source_id == source.id`.
  - `register_source(path: Path, parser: str, extracted_text: str) -> SourceRef`.
  - `parse_text(path: str | Path, *, language: str | None = None) -> ParseResult`.

- [ ] **Step 1: Write the failing test**

```python
# tests/parsers/test_text.py
import hashlib

from veriformis.parsers.text import parse_text


def test_parse_text_paragraphs_and_spans(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_text("First para.\n\nSecond para.\n\nThird para.", encoding="utf-8")
    result = parse_text(p)
    assert result.source.parser == "text"
    assert result.source.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()
    assert result.document.source_id == result.source.id
    blocks = result.document.children
    assert len(blocks) == 3
    for block in blocks:
        assert result.source.extracted_text[block.span.start:block.span.end] == block_text_of(block)


def test_parse_text_code_language(tmp_path):
    p = tmp_path / "snippet.py"
    p.write_text("print('hi')\n", encoding="utf-8")
    result = parse_text(p, language="python")
    assert result.document.children[0].language == "python"


def block_text_of(block):
    from veriformis.ir import block_text

    return block_text(block)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/parsers/test_text.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.parsers'`

- [ ] **Step 3: Write the implementation**

```python
# src/veriformis/sources.py
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
```

```python
# src/veriformis/parsers/text.py
"""Plain-text and source-code parser: blank-line paragraph splitting with spans."""
from __future__ import annotations

import re
from pathlib import Path

from veriformis.ir import CodeBlock, Document, Paragraph, Span, Text
from veriformis.sources import ParseResult, register_source

_BLANK = re.compile(r"\n\s*\n")


def parse_text(path: str | Path, *, language: str | None = None) -> ParseResult:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    source = register_source(p, "text", text)
    if language is not None:
        doc = Document(
            children=[CodeBlock(text=text, language=language, span=Span(0, len(text)), block_index=0)],
            source_id=source.id,
        )
        return ParseResult(document=doc, source=source)
    blocks = []
    pos = 0
    for chunk in _BLANK.split(text):
        stripped = chunk.strip()
        if not stripped:
            continue
        chunk_start = text.index(chunk, pos)
        start = chunk_start + (len(chunk) - len(chunk.lstrip()))
        pos = chunk_start + len(chunk)
        # span covers the stripped range, so stream[start:end] == block_text(block)
        blocks.append(
            Paragraph(children=[Text(stripped)], span=Span(start, start + len(stripped)),
                      block_index=len(blocks))
        )
    return ParseResult(document=Document(children=blocks, source_id=source.id), source=source)
```

```python
# src/veriformis/parsers/__init__.py
"""Parsers: one module per input format, each returning sources.ParseResult."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/parsers/test_text.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/sources.py src/veriformis/parsers tests/parsers
git commit -m "feat(parsers): source registry + text/code parser with spans"
```

---

### Task 4: Markdown parser (vendor-and-extend, decision D1)

**Files:**
- Create: `src/veriformis/parsers/markdown.py`, `tests/fixtures/sample.md`
- Test: `tests/parsers/test_markdown.py`

**Interfaces:**
- Consumes: Task 2 IR, Task 3 `register_source`/`ParseResult`.
- Produces:
  - `parse_md(source: str) -> Document` — library entry (no SourceRef).
  - `parse_md_file(path: str | Path) -> ParseResult` — file entry with spans.
  - Blocks carry `span` (char offsets into the markdown source, from `markdown-it` token `.map` line ranges) and sequential `block_index`.

**Vendoring protocol (privacy constraint — follow exactly):**

1. The dispatcher supplies the donor checkout location out-of-band at execution time (env var `PRIVATE_LIB`); it is never written into the repo, this plan, or commit messages.
2. Copy the donor's **markdown parser module only** (its `md/parser.py`) to `src/veriformis/parsers/markdown.py`. Do not copy its renderer, its pandoc-preprocessing module, or any `__init__`.
3. Adapt in place (this is the "extend" half of D1):
   - Replace the donor IR import with `from veriformis.ir import (...)`. Node mapping is 1:1 except its `List` → our `ListBlock`.
   - Attach provenance using the **extracted-stream contract** (same as Task 5, and required by the Task 8 stream contract): while emitting blocks, build the canonical stream incrementally — append each block's `block_text()` plus `"\n\n"` separator; set `span = Span(stream_pos_before, stream_pos_before + len(block_text))` and `block_index` in emission order. (markdown-it token `.map` line ranges may still be used internally for block segmentation, but spans must index the extracted stream, never the raw file.)
   - Public surface becomes exactly `parse_md` + `parse_md_file`. `parse_md(source)` also builds spans into a stream it constructs the same way (without a SourceRef); `parse_md_file(path)` reads the file, parses, then `register_source(p, "markdown", stream)` with the built stream, and sets `document.source_id`.
4. **Scrub:** remove every string that identifies the donor project — its name in comments/docstrings, any `*.io` namespace, any `*_IMAGE_CACHE` env-var reference, any `customXml` side-car references. Then verify:
   Run: `grep -rin "$(basename $PRIVATE_LIB)" src/veriformis/ ; test $? -eq 1`
   Expected: no matches (exit 1). Also `grep -rin "image_cache\|customXml" src/veriformis/parsers/markdown.py` → no matches.

- [ ] **Step 1: Write the failing test and fixture**

```markdown
<!-- tests/fixtures/sample.md -->
# Title

A paragraph with **bold**, _italic_, `code`, and a [link](https://example.com).

- item one
- item two
  - nested

```python
print(" fenced ")
```

| A | B |
|---|---|
| 1 | 2 |

> quoted

Inline math $x^2$ and a footnote.[^n]

[^n]: note text
```

```python
# tests/parsers/test_markdown.py
from pathlib import Path

from veriformis.ir import (
    Blockquote, CodeBlock, Heading, ListBlock, Paragraph, Table, block_text,
)
from veriformis.parsers.markdown import parse_md, parse_md_file

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample.md"


def test_block_types_and_order():
    doc = parse_md_file(FIXTURE).document
    types = [type(b) for b in doc.children]
    assert types[0] is Heading
    assert Paragraph in types and ListBlock in types
    assert CodeBlock in types and Table in types and Blockquote in types


def test_spans_point_into_source():
    result = parse_md_file(FIXTURE)
    text = result.source.extracted_text
    for block in result.document.children:
        assert block.span is not None
        assert block.span.start < block.span.end <= len(text)
    para = next(b for b in result.document.children if isinstance(b, Paragraph))
    assert "bold" in text[para.span.start:para.span.end]


def test_code_block_language_and_footnotes():
    doc = parse_md_file(FIXTURE).document
    code = next(b for b in doc.children if isinstance(b, CodeBlock))
    assert code.language == "python"
    assert "n" in doc.footnotes


def test_parse_md_library_entry():
    doc = parse_md("# Hi\n\ntext")
    assert isinstance(doc.children[0], Heading)
    assert block_text(doc.children[1]) == "text"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/parsers/test_markdown.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.parsers.markdown'`

- [ ] **Step 3: Vendor + adapt per the protocol above**

Copy the donor markdown parser, apply the node-mapping and span-attachment edits, expose `parse_md`/`parse_md_file`, scrub identifying strings, run the grep verification. The donor parser already handles footnotes, math, tables, strikethrough, task lists, and Pandoc-style sup/sub/citations via markdown-it-py plugins (`markdown-it-py>=3.0`, `mdit-py-plugins>=0.4` — already declared in Task 1's `pyproject.toml`); do not re-implement those behaviors.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/parsers/test_markdown.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/parsers/markdown.py tests/parsers/test_markdown.py tests/fixtures/sample.md
git commit -m "feat(parsers): markdown parser with char-offset provenance"
```

---

### Task 5: DOCX parser (vendor-and-extend, decision D1)

**Files:**
- Create: `src/veriformis/parsers/docx.py`, `src/veriformis/parsers/docx_styles.py`
- Test: `tests/parsers/test_docx.py`

**Interfaces:**
- Consumes: Task 2 IR, Task 3 `register_source`/`ParseResult`.
- Produces:
  - `parse_docx_file(path: str | Path) -> ParseResult`.
  - Extracted-text stream = block plain texts joined by `"\n\n"` in document order; each block's `span` indexes into that stream; `page` stays `None` (DOCX is unpaginated); `block_index` is document order.

**Vendoring protocol (same rules as Task 4):**

1. Donor location arrives via `PRIVATE_LIB` at execution time, never in the repo.
2. Copy the donor's **docx parser module and its style-mapping module only** (its `docx/parser.py`, `docx/styles.py`) → `docx.py`, `docx_styles.py`. Do not copy its renderer, CLI, linting, templates, MCP, or thesis-formatting modules.
3. Adapt in place:
   - Donor IR import → `from veriformis.ir import (...)`; its `List` → our `ListBlock`.
   - **Delete side-car support:** remove all code reading the donor's `customXml/*.xml` metadata part (roundtrip metadata for its own renderer — Veriformis has no renderer, so this is dead weight and it contains the donor's namespace). Footnotes/endnotes stay (they are standard OOXML parts).
   - Attach provenance: while walking body blocks, build the extracted-text stream incrementally — append each block's plain text plus `"\n\n"` separator; record `span = Span(stream_pos_before, stream_pos_before + len(block_text))` and sequential `block_index`.
   - Public surface becomes exactly `parse_docx_file` (wrapper: `register_source(p, "docx", stream)`, set `document.source_id`).
4. **Scrub + verify** as in Task 4 step 4 (donor name, `*.io` namespace, `*_IMAGE_CACHE`, `customXml` → zero matches).

- [ ] **Step 1: Write the failing test**

```python
# tests/parsers/test_docx.py
from docx import Document as DocxBuilder

from veriformis.ir import Heading, ListBlock, Paragraph, Table, block_text
from veriformis.parsers.docx import parse_docx_file


def _build(path):
    d = DocxBuilder()
    d.add_heading("Report", level=1)
    d.add_paragraph("Opening paragraph.")
    p = d.add_paragraph()
    p.add_run("Mixed ").bold = False
    run = p.add_run("bold")
    run.bold = True
    p.add_run(" text.")
    d.add_paragraph("First item", style="List Bullet")
    d.add_paragraph("Second item", style="List Bullet")
    table = d.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "H1"
    table.cell(0, 1).text = "H2"
    table.cell(1, 0).text = "a"
    table.cell(1, 1).text = "b"
    d.save(path)


def test_docx_structure_and_provenance(tmp_path):
    path = tmp_path / "sample.docx"
    _build(path)
    result = parse_docx_file(path)
    doc = result.document
    assert result.source.parser == "docx"
    types = [type(b) for b in doc.children]
    assert Heading in types and Paragraph in types
    assert ListBlock in types and Table in types
    heading = next(b for b in doc.children if isinstance(b, Heading))
    assert heading.level == 1 and block_text(heading) == "Report"
    # provenance: every span indexes into the extracted stream
    stream = result.source.extracted_text
    for block in doc.children:
        assert block.span is not None
        assert block.span.start < block.span.end <= len(stream)
    para = next(
        b for b in doc.children
        if isinstance(b, Paragraph) and "Opening" in block_text(b)
    )
    assert "Opening paragraph." in stream[para.span.start:para.span.end]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/parsers/test_docx.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.parsers.docx'`

- [ ] **Step 3: Vendor + adapt per the protocol above**

Copy the two donor modules, apply IR remapping, delete side-car handling, add stream/span tracking, expose `parse_docx_file`, scrub, grep-verify. The donor parser already handles headings/style mapping, nested lists, tables, footnotes/endnotes, tracked-change stripping, and images via direct lxml walks over OOXML (`python-docx>=1.1`, `lxml>=4.9` — already declared in Task 1); do not re-implement those behaviors.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/parsers/test_docx.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/parsers/docx.py src/veriformis/parsers/docx_styles.py tests/parsers/test_docx.py
git commit -m "feat(parsers): docx parser with document-order provenance"
```

---

### Task 6: Cleaning-rule engine

**Files:**
- Create: `src/veriformis/rules/__init__.py`, `src/veriformis/rules/engine.py`
- Test: `tests/rules/test_engine.py`

**Interfaces:**
- Consumes: Task 2 IR.
- Produces (used by Tasks 7, 11, 12):
  - `Edit(start: int, end: int, replacement: str = "")` — a mutation, offsets into the pre-edit text.
  - `RuleResult(text: str, edits: list[Edit])`.
  - `Rule` protocol: `name: str`; `apply(text: str) -> RuleResult`.
  - `RegexRule(name, pattern, replacement="", flags=re.IGNORECASE|re.MULTILINE)` — stock Rule.
  - `TransformRecord(rule: str, params: dict, block_index: int, edits: int, bytes_removed: int, warned: bool)` — `bytes_removed` may be negative (rule grew text).
  - `apply_rules(text: str, rules: list[Rule], *, max_remove_frac: float = 0.3) -> tuple[str, list[TransformRecord], list[str]]` — sequential; a rule that would remove more than `max_remove_frac` of its input is **skipped** and reported in `warnings` (never silently applied).
  - `clean_document(doc: Document, rules: list[Rule], *, max_remove_frac: float = 0.3) -> tuple[Document, list[TransformRecord], list[str]]` — applies rules per leaf block via `block_text`/`set_block_text`; returns edited block indexes in `TransformRecord.block_index`.

- [ ] **Step 1: Write the failing test**

```python
# tests/rules/test_engine.py
from veriformis.ir import Document, Paragraph, Text
from veriformis.rules.engine import RegexRule, apply_rules, clean_document


def test_apply_rules_logs_edits_and_runs_sequentially():
    text, records, warnings = apply_rules(
        "hello   world",
        [RegexRule("spaces", r"\s+", " "), RegexRule("shout", r"world", "WORLD")],
    )
    assert text == "hello WORLD"
    assert [r.rule for r in records] == ["spaces", "shout"]
    assert records[0].edits == 1
    assert warnings == []


def test_safety_valve_skips_destructive_rule():
    text = "keep this sentence. " * 10
    out, records, warnings = apply_rules(
        text, [RegexRule("nuke", r"\w+", "")], max_remove_frac=0.3
    )
    assert out == text  # rule skipped
    assert warnings and "nuke" in warnings[0]
    assert records[0].warned is True


def test_clean_document_edits_blocks_and_preserves_provenance():
    doc = Document(children=[
        Paragraph(children=[Text("alpha  beta")]),
        Paragraph(children=[Text("gamma")]),
    ])
    cleaned, records, _ = clean_document(doc, [RegexRule("spaces", r"\s+", " ")])
    from veriformis.ir import block_text

    assert block_text(cleaned.children[0]) == "alpha beta"
    assert block_text(cleaned.children[1]) == "gamma"
    assert records[0].block_index == 0
    assert all(r.block_index != 1 for r in records if r.edits > 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/rules/test_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.rules'`

- [ ] **Step 3: Write the implementation**

```python
# src/veriformis/rules/engine.py
"""Deterministic cleaning-rule engine. Every firing is logged; destructive
rules are refused, never silently applied."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from veriformis.ir import Document, block_text, set_block_text


@dataclass
class Edit:
    start: int
    end: int
    replacement: str = ""


@dataclass
class RuleResult:
    text: str
    edits: list[Edit] = field(default_factory=list)


class Rule(Protocol):
    name: str

    def apply(self, text: str) -> RuleResult: ...


@dataclass
class RegexRule:
    name: str
    pattern: str
    replacement: str = ""
    flags: int = re.IGNORECASE | re.MULTILINE
    params: dict = field(default_factory=dict)

    def apply(self, text: str) -> RuleResult:
        rx = re.compile(self.pattern, self.flags)
        edits = [
            Edit(m.start(), m.end(), m.expand(self.replacement))
            for m in rx.finditer(text)
        ]
        return RuleResult(text=rx.sub(self.replacement, text), edits=edits)


@dataclass
class TransformRecord:
    rule: str
    params: dict
    block_index: int
    edits: int
    bytes_removed: int
    warned: bool = False


def apply_rules(
    text: str, rules: list[Rule], *, max_remove_frac: float = 0.3
) -> tuple[str, list[TransformRecord], list[str]]:
    records: list[TransformRecord] = []
    warnings: list[str] = []
    current = text
    for rule in rules:
        before = current
        result = rule.apply(before)
        removed = len(before) - len(result.text)
        warned = len(before) > 0 and removed > max_remove_frac * len(before)
        records.append(
            TransformRecord(
                rule=rule.name,
                params=getattr(rule, "params", {}),
                block_index=-1,
                edits=len(result.edits),
                bytes_removed=removed,
                warned=warned,
            )
        )
        if warned:
            warnings.append(
                f"rule '{rule.name}' skipped: would remove {removed}/{len(before)} chars"
            )
        else:
            current = result.text
    return current, records, warnings


def clean_document(
    doc: Document, rules: list[Rule], *, max_remove_frac: float = 0.3
) -> tuple[Document, list[TransformRecord], list[str]]:
    all_records: list[TransformRecord] = []
    all_warnings: list[str] = []
    new_children = []
    for block in doc.children:
        original = block_text(block)
        cleaned, records, warnings = apply_rules(original, rules, max_remove_frac=max_remove_frac)
        for r in records:
            r.block_index = block.block_index
        all_records.extend(r for r in records if r.edits > 0 or r.warned)
        all_warnings.extend(warnings)
        new_children.append(set_block_text(block, cleaned) if cleaned != original else block)
    return (
        Document(
            children=new_children,
            footnotes=doc.footnotes,
            endnotes=doc.endnotes,
            source_id=doc.source_id,
        ),
        all_records,
        all_warnings,
    )
```

```python
# src/veriformis/rules/__init__.py
from veriformis.rules.engine import (  # noqa: F401
    Edit, RegexRule, Rule, RuleResult, TransformRecord, apply_rules, clean_document,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/rules/test_engine.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/rules tests/rules
git commit -m "feat(rules): deterministic cleaning engine with transform log + safety valve"
```

---

### Task 7: Cleaning-rule library

**Files:**
- Create: `src/veriformis/rules/library.py`
- Test: `tests/rules/test_library.py`

**Interfaces:**
- Consumes: Task 6 engine.
- Produces (used by Task 12 CLI): `RULES: dict[str, Callable[[], Rule]]` registry with keys `page-numbers`, `headers-footers`, `whitespace`, `urls`, `emails`, `special-chars`, `lowercase`; `custom_regex(pattern: str, replacement: str = "") -> Rule`; `default_rules() -> list[Rule]` (page-numbers + whitespace).

- [ ] **Step 1: Write the failing test**

```python
# tests/rules/test_library.py
from veriformis.rules.library import RULES, custom_regex, default_rules


def _apply(name, text):
    return RULES[name]().apply(text).text


def test_page_numbers_line_anchored_only():
    # THE canonical regression: tunerepo's regex deleted every standalone number.
    text = "In 1492 Columbus sailed.\n\n37\n\nPage 12 of 98\n\nThe year 1492 matters.\n"
    out = _apply("page-numbers", text)
    assert "1492" in out
    assert "37" not in out
    assert "Page 12 of 98" not in out


def test_page_numbers_conservative_on_inline_and_boundaries():
    # Task-7 review amendment: leading inline numbers survive; paragraph
    # boundaries are never merged by a removal.
    text = "37 people attended the meeting.\n\npara one\n\n42\n\npara two\n"
    out = _apply("page-numbers", text)
    assert out == "37 people attended the meeting.\n\npara one\n\n\npara two\n"


def test_headers_footers_strips_only_short_repeated_lines():
    lines = ["CONFIDENTIAL DRAFT"] + [f"Unique sentence number {i} here." for i in range(6)]
    text = "CONFIDENTIAL DRAFT\n" + "\n".join(lines[1:3]) + "\nCONFIDENTIAL DRAFT\n" + "\n".join(lines[3:]) + "\nCONFIDENTIAL DRAFT"
    out = _apply("headers-footers", text)
    assert "CONFIDENTIAL DRAFT" not in out
    assert "Unique sentence number 4 here." in out


def test_whitespace_urls_emails_lowercase():
    assert _apply("whitespace", "a   b\t\tc") == "a b c"
    assert _apply("whitespace", "a\n\n\nb") == "a\n\n\nb"  # newlines are structural
    assert _apply("urls", "see https://example.com/x now") == "see  now"
    assert _apply("emails", "mail me@example.com please") == "mail  please"
    assert _apply("lowercase", "HeLLo") == "hello"


def test_special_chars_whitelist_conservative():
    out = _apply("special-chars", "price: $5 (ok) — really!")
    assert "$" not in out and "—" not in out
    assert "price" in out and "really!" in out


def test_custom_regex_and_defaults():
    rule = custom_regex(r"\[.*?\]")
    assert rule.apply("keep [drop] this").text == "keep  this"
    assert [r.name for r in default_rules()] == ["page-numbers", "whitespace"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/rules/test_library.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.rules.library'`

- [ ] **Step 3: Write the implementation**

```python
# src/veriformis/rules/library.py
"""Stock cleaning rules. Line-anchored and conservative by design: a rule may
never delete inline content that merely *looks* structural."""
from __future__ import annotations

import re
from collections.abc import Callable

from veriformis.rules.engine import RegexRule, Rule


class _RepeatedLineRule:
    """Removes short lines (<=80 chars stripped) appearing >= threshold times —
    the honest v1 approximation of header/footer detection."""

    name = "headers-footers"

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.params = {"threshold": threshold}

    def apply(self, text: str):
        from veriformis.rules.engine import Edit, RuleResult

        lines = text.split("\n")
        counts: dict[str, int] = {}
        for line in lines:
            key = line.strip()
            if key and len(key) <= 80:
                counts[key] = counts.get(key, 0) + 1
        edits, out, pos = [], [], 0
        for line in lines:
            key = line.strip()
            drop = bool(key) and len(key) <= 80 and counts.get(key, 0) >= self.threshold
            if drop:
                edits.append(Edit(pos, pos + len(line)))
            else:
                out.append(line)
            pos += len(line) + 1
        return RuleResult(text="\n".join(out), edits=edits)


def custom_regex(pattern: str, replacement: str = "") -> Rule:
    return RegexRule("custom", pattern, replacement, params={"pattern": pattern, "replacement": replacement})


class _LowercaseRule:
    name = "lowercase"
    params: dict = {}

    def apply(self, text: str):
        from veriformis.rules.engine import Edit, RuleResult

        lowered = text.lower()
        return RuleResult(text=lowered, edits=[Edit(0, len(text))] if lowered != text else [])


RULES: dict[str, Callable[[], Rule]] = {
    "page-numbers": lambda: RegexRule(
        "page-numbers",
        r"^[ \t]*(?:\d{1,4}|(?:page|p\.?)\s*\d{1,4}(?:\s*of\s*\d{1,4})?)[ \t]*(?:\n|$)",
        "",
    ),
    "headers-footers": lambda: _RepeatedLineRule(),
    "whitespace": lambda: RegexRule("whitespace", r"[ \t]+", " ", flags=re.MULTILINE),
    "urls": lambda: RegexRule("urls", r"https?://[^\s]+"),
    "emails": lambda: RegexRule("emails", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "special-chars": lambda: RegexRule("special-chars", r"[^\w\s.,!?;:'\"()/-]"),
    "lowercase": lambda: _LowercaseRule(),
}


def default_rules() -> list[Rule]:
    return [RULES["page-numbers"](), RULES["whitespace"]()]
```

Note for the implementer: the `whitespace` rule collapses `[ \t]+` only — never newlines; paragraph boundaries are load-bearing downstream (chunkers depend on them).

Amendment (Task-7 review, 2026-07-28): the `page-numbers` regex was re-anchored to `[ \t]*…[ \t]*(?:\n|$)` after review found the original `^\s*…\s*\n?` form deleted paragraph-leading inline numbers and merged paragraph boundaries — both violations of this task's conservative-design constraint. The added test `test_page_numbers_conservative_on_inline_and_boundaries` pins the corrected behavior (and makes the "6 passed" expectation exact).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/rules/test_library.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/rules/library.py tests/rules/test_library.py
git commit -m "feat(rules): stock rule library with line-anchored page-number regression"
```

---

### Task 8: Chunkers

**Files:**
- Create: `src/veriformis/chunkers/__init__.py`, `src/veriformis/chunkers/base.py`, `src/veriformis/chunkers/strategies.py`
- Test: `tests/chunkers/test_strategies.py`

**Interfaces:**
- Consumes: Task 2 IR.
- Produces (used by Tasks 9–12):
  - `Chunk(id: str, source_id: str, block_index: int, span: Span | None, heading_path: list[str], text: str, tokens_est: int, transformed: bool)`.
  - **Stream contract (global):** every parser's `SourceRef.extracted_text` is the canonical extracted stream — leaf blocks' plain texts joined by `"\n\n"` — such that for any leaf block, `stream[block.span.start:block.span.end] == block_text(block)`. Chunk `span` indexes into that same stream. (Tasks 3–5 conform; Task 4's md spans are extracted-stream offsets computed at emission time, not token.map file offsets.)
  - `est_tokens(text: str) -> int` (`max(1, ceil(len/4))`).
  - `chunk_paragraph(blocks, *, max_size=1000, source_id="", transformed=()) -> list[Chunk]`
  - `chunk_fixed(blocks, *, size=1000, overlap=100, source_id="", transformed=()) -> list[Chunk]`
  - `chunk_sliding(blocks, *, size=1000, overlap=100, source_id="", transformed=()) -> list[Chunk]` — doc shorter than `size` yields exactly one chunk.
  - `chunk_sentence(blocks, *, max_size=1000, source_id="", transformed=()) -> list[Chunk]` — rule-based English splitter with abbreviation guard.
  - `chunk_structure(blocks, *, max_size=2000, source_id="", transformed=()) -> list[Chunk]` — splits at heading boundaries, attaches `heading_path`.
  - `transformed` param: iterable of `block_index` values edited by cleaning (from `TransformRecord.block_index`); any chunk containing one sets `transformed=True`.

- [ ] **Step 1: Write the failing test**

```python
# tests/chunkers/test_strategies.py
from veriformis.chunkers.strategies import (
    chunk_fixed, chunk_paragraph, chunk_sentence, chunk_sliding, chunk_structure,
)
from veriformis.ir import Heading, Paragraph, Span, Text


def _blocks(texts):
    blocks, pos = [], 0
    for i, t in enumerate(texts):
        blocks.append(Paragraph(children=[Text(t)], span=Span(pos, pos + len(t)), block_index=i))
        pos += len(t) + 2
    return blocks


def test_paragraph_chunks_preserve_coverage_and_provenance():
    blocks = _blocks(["alpha", "beta", "gamma"])
    chunks = chunk_paragraph(blocks, max_size=100, source_id="src-x")
    assert "\n\n".join(c.text for c in chunks) == "\n\n".join(["alpha", "beta", "gamma"])
    assert all(c.source_id == "src-x" for c in chunks)
    assert chunks[0].span.start == 0
    assert chunks[0].tokens_est >= 1


def test_sliding_short_document_yields_one_chunk():
    # regression: tunerepo's sliding window produced zero chunks for short docs
    chunks = chunk_sliding(_blocks(["tiny"]), size=1000, overlap=100)
    assert len(chunks) == 1 and chunks[0].text == "tiny"


def test_fixed_respects_size_and_overlap():
    blocks = _blocks(["a" * 100])
    chunks = chunk_fixed(blocks, size=30, overlap=10)
    assert all(len(c.text) <= 30 for c in chunks)
    assert chunks[1].text[:10] == chunks[0].text[-10:]  # overlap continuity


def test_sentence_splitter_respects_abbreviations():
    text = "Dr. Smith left. He met Ms. Lee at 5 p.m. sharp. It was late."
    chunks = chunk_sentence(_blocks([text]), max_size=1000)
    joined = chunks[0].text
    assert "Dr. Smith left." in joined
    assert "5 p.m. sharp." in joined


def test_structure_chunks_attach_heading_path():
    blocks = [
        Heading(level=1, children=[Text("Intro")], span=Span(0, 5), block_index=0),
        Paragraph(children=[Text("body one")], span=Span(7, 15), block_index=1),
        Heading(level=2, children=[Text("Scope")], span=Span(17, 22), block_index=2),
        Paragraph(children=[Text("body two")], span=Span(24, 32), block_index=3),
    ]
    chunks = chunk_structure(blocks, max_size=100, source_id="s")
    assert chunks[0].heading_path == ["Intro"]
    assert chunks[-1].heading_path == ["Intro", "Scope"]
    assert any("body two" in c.text for c in chunks)


def test_transformed_flag_marks_only_chunks_containing_edited_blocks():
    blocks = _blocks(["aaa", "bbb", "ccc"])
    chunks = chunk_paragraph(blocks, max_size=5, transformed=(1,))
    assert [c.transformed for c in chunks] == [False, True, False]


def test_stream_chunks_attribute_transformed_by_window_intersection():
    blocks = _blocks(["x" * 40, "y" * 40])
    chunks = chunk_fixed(blocks, size=30, overlap=10, transformed=(0,))
    assert chunks[0].transformed is True
    assert chunks[-1].transformed is False  # last window covers only block 1


def test_sentence_chunks_accumulate_contributing_blocks_for_transformed():
    blocks = _blocks(["Alpha one. Alpha two.", "Beta one."])
    chunks = chunk_sentence(blocks, max_size=1000, transformed=(1,))
    assert len(chunks) == 1
    assert chunks[0].transformed is True  # edited block 1 contributes mid-buffer
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/chunkers/test_strategies.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.chunkers'`

- [ ] **Step 3: Write the implementation**

```python
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
```

```python
# src/veriformis/chunkers/strategies.py
"""Chunking strategies. Coverage invariant: no source text is silently orphaned."""
from __future__ import annotations

import re
from collections.abc import Iterable

from veriformis.chunkers.base import Chunk, Span, flatten, heading_paths, make_chunk
from veriformis.ir import Block, Heading, block_text

_ABBREVS = ("mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "vs.", "etc.", "e.g.", "i.e.",
            "p.m.", "a.m.", "u.s.", "u.k.", "no.", "fig.", "approx.", "dept.", "est.")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def _norm(transformed: Iterable[int]) -> set[int]:
    return set(transformed)


def _path_map(blocks: list[Block]) -> dict[int, list[str]]:
    """heading_path per block_index (robust when `blocks` is a sub-list whose
    block_index values are not 0-based positions)."""
    paths = heading_paths(blocks)
    return {block.block_index: paths[i] for i, block in enumerate(blocks)}


def chunk_paragraph(blocks, *, max_size=1000, source_id="", transformed=()) -> list[Chunk]:
    tb, paths, chunks, seq = _norm(transformed), _path_map(blocks), [], 0
    group: list[Block] = []

    def flush() -> None:
        nonlocal seq
        seq += 1
        chunks.append(make_chunk(
            seq, group, flatten(group), source_id=source_id,
            heading_path=paths.get(group[0].block_index, []),
            span=Span(group[0].span.start, group[-1].span.end)
            if group[0].span and group[-1].span else None,
            transformed_blocks=tb,
        ))

    for block in blocks:
        if group and len(flatten(group + [block])) > max_size:
            flush()
            group = [block]
        else:
            group = group + [block]
    if group:
        flush()
    return chunks


def _block_ranges(blocks) -> list[tuple[int, int]]:
    """[start, end) offset of each block's region (text plus its following
    separator) within the flattened stream."""
    ranges, pos = [], 0
    for i, block in enumerate(blocks):
        end = pos + len(block_text(block)) + (0 if i == len(blocks) - 1 else 2)
        ranges.append((pos, end))
        pos = end
    return ranges


def _blocks_intersecting(blocks, ranges, start, end) -> list[Block]:
    return [b for b, (s, e) in zip(blocks, ranges, strict=True) if start < e and end > s]


def _stream_chunks(blocks, size, overlap, *, source_id, transformed):
    """Shared engine for fixed/sliding: `fixed` is boundary splitting with optional
    overlap; `sliding` is the same engine with overlap as a first-class parameter.
    A document shorter than `size` always yields exactly one chunk."""
    tb, stream, chunks, seq = _norm(transformed), flatten(blocks), [], 0
    ranges = _block_ranges(blocks)
    if len(stream) <= size:
        if stream:
            chunks.append(make_chunk(1, blocks, stream, source_id=source_id,
                                     heading_path=_path_map(blocks).get(blocks[0].block_index, []) if blocks else [],
                                     span=Span(0, len(stream)) if blocks and blocks[0].span else None,
                                     transformed_blocks=tb))
        return chunks
    step = max(1, size - overlap)
    pos = 0
    while pos < len(stream):
        end = min(pos + size, len(stream))
        seq += 1
        chunks.append(make_chunk(seq, _blocks_intersecting(blocks, ranges, pos, end),
                                 stream[pos:end], source_id=source_id,
                                 heading_path=[], span=Span(pos, end), transformed_blocks=tb))
        if end == len(stream):
            break
        pos += step
    return chunks


def chunk_fixed(blocks, *, size=1000, overlap=100, source_id="", transformed=()) -> list[Chunk]:
    return _stream_chunks(blocks, size, overlap, source_id=source_id, transformed=transformed)


def chunk_sliding(blocks, *, size=1000, overlap=100, source_id="", transformed=()) -> list[Chunk]:
    return _stream_chunks(blocks, size, overlap, source_id=source_id, transformed=transformed)


def _sentences(text: str) -> list[str]:
    parts = _SENT_SPLIT.split(text)
    merged: list[str] = []
    for part in parts:
        if merged and any(merged[-1].lower().endswith(a) for a in _ABBREVS):
            merged[-1] = merged[-1] + " " + part
        else:
            merged.append(part)
    return merged


def chunk_sentence(blocks, *, max_size=1000, source_id="", transformed=()) -> list[Chunk]:
    tb, paths, chunks, seq = _norm(transformed), _path_map(blocks), [], 0
    buf, buf_blocks = "", []
    for block in blocks:
        for sent in _sentences(block_text(block)):
            candidate = (buf + " " + sent).strip() if buf else sent
            if buf and len(candidate) > max_size:
                seq += 1
                chunks.append(make_chunk(seq, buf_blocks, buf, source_id=source_id,
                                         heading_path=paths.get(buf_blocks[0].block_index, []) if buf_blocks else [],
                                         span=None, transformed_blocks=tb))
                buf, buf_blocks = sent, [block]
            else:
                buf = candidate
                if not any(b is block for b in buf_blocks):
                    buf_blocks.append(block)
    if buf:
        seq += 1
        chunks.append(make_chunk(seq, buf_blocks, buf, source_id=source_id,
                                 heading_path=paths.get(buf_blocks[0].block_index, []) if buf_blocks else [],
                                 span=None, transformed_blocks=tb))
    return chunks


def chunk_structure(blocks, *, max_size=2000, source_id="", transformed=()) -> list[Chunk]:
    global_paths = _path_map(blocks)
    sections: list[list[Block]] = [[]]
    for block in blocks:
        if isinstance(block, Heading) and sections[-1]:
            sections.append([])
        sections[-1].append(block)
    chunks: list[Chunk] = []
    for section in sections:
        chunks.extend(chunk_paragraph(section, max_size=max_size, source_id=source_id, transformed=transformed))
    for i, chunk in enumerate(chunks, 1):
        chunk.id = f"chk-{i:04d}"
        # heading_path must reflect the document-wide context of the chunk's first
        # block, not just its section — re-attach from the global map
        chunk.heading_path = global_paths.get(chunk.block_index, chunk.heading_path)
    return chunks
```

```python
# src/veriformis/chunkers/__init__.py
from veriformis.chunkers.base import Chunk, est_tokens, flatten  # noqa: F401
from veriformis.chunkers.strategies import (  # noqa: F401
    chunk_fixed, chunk_paragraph, chunk_sentence, chunk_sliding, chunk_structure,
)
```

Note for the implementer: `chunk_sentence`'s span is intentionally `None` in v1 (sentence packing crosses block boundaries in a way the single-span model can't express honestly); `heading_path` is still attached. The provenance gate (Task 10) treats `span=None` as "linkage check only".

Amendment (Task-8 review, 2026-07-28): the `transformed` flag now reflects the blocks each chunk actually contains, per the global constraint "any chunk containing one sets `transformed=True`" — `_stream_chunks` attributes each window to its intersecting blocks via `_block_ranges`/`_blocks_intersecting` (the original listing passed the whole document to every chunk, so one edited block marked every chunk), and `chunk_sentence` accumulates every contributing block in `buf_blocks` (the original kept only the buffer's first block). Three tests pin the corrected semantics. Stream-chunk `heading_path=[]` is retained deliberately: heading attribution for arbitrary byte windows is ill-defined in v1.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/chunkers/test_strategies.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/chunkers tests/chunkers
git commit -m "feat(chunkers): five strategies with provenance + coverage invariants"
```

---

### Task 9: Serializers (completion / instruction / chat)

**Files:**
- Create: `src/veriformis/serializers/__init__.py`, `src/veriformis/serializers/formats.py`, `src/veriformis/serializers/chat.py`, `src/veriformis/serializers/templates/chat/{llama3,mistral,qwen,gemma,phi}.jinja`
- Test: `tests/serializers/test_formats.py`, `tests/serializers/test_chat.py`

**Interfaces:**
- Consumes: Task 8 `Chunk`.
- Produces (used by Tasks 10–12):
  - `serialize_completion(chunks: list[Chunk], *, include_heading_path: bool = False) -> list[dict]` → `{"text": ...}` per chunk; heading path prefixed as `"Intro > Scope\n\n"` when enabled.
  - `serialize_instruction(chunks: list[Chunk], *, instruction: str) -> list[dict]` → `{"instruction", "input", "output"}`; `input` is `" > ".join(heading_path)`.
  - `CHAT_TEMPLATES: dict[str, str]` — template name → Jinja source (loaded from package data).
  - `render_chat(messages: list[dict[str, str]], *, template: str) -> str` — messages have `role`/`content`; raises `UnsupportedInputError`-compatible `ValueError` on unknown template name.
  - `serialize_chat(records: list[dict], *, template: str) -> list[dict]` — input records carry `user`/`assistant` (+ optional `system`); output `{"text": rendered}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/serializers/test_formats.py
from veriformis.chunkers.base import Chunk
from veriformis.serializers.formats import serialize_completion, serialize_instruction


def _chunk(text="body", path=None):
    return Chunk(id="chk-1", source_id="s", block_index=0, span=None,
                 heading_path=path or [], text=text, tokens_est=2)


def test_completion_plain_and_with_heading_path():
    assert serialize_completion([_chunk()])[0] == {"text": "body"}
    out = serialize_completion([_chunk(path=["Intro", "Scope"])], include_heading_path=True)
    assert out[0]["text"] == "Intro > Scope\n\nbody"


def test_instruction_mapping():
    out = serialize_instruction([_chunk(path=["Ch1"])], instruction="Summarize the section.")
    assert out[0] == {"instruction": "Summarize the section.", "input": "Ch1", "output": "body"}
```

```python
# tests/serializers/test_chat.py
import pytest

from veriformis.serializers.chat import CHAT_TEMPLATES, render_chat, serialize_chat

MESSAGES = [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello!"},
]


def test_llama3_golden():
    assert render_chat(MESSAGES, template="llama3") == (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        "You are helpful.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
        "Hi<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\nHello!<|eot_id|>"
    )


def test_qwen_golden():
    assert render_chat(MESSAGES, template="qwen") == (
        "<|im_start|>system\nYou are helpful.<|im_end|>\n"
        "<|im_start|>user\nHi<|im_end|>\n<|im_start|>assistant\nHello!<|im_end|>"
    )


def test_mistral_gemma_phi_golden():
    assert render_chat(MESSAGES, template="mistral") == "<s>[INST] You are helpful.\n\nHi [/INST] Hello!</s>"
    assert render_chat(MESSAGES, template="gemma") == (
        "<bos><start_of_turn>user\nYou are helpful.\n\nHi<end_of_turn>\n<start_of_turn>model\nHello!<end_of_turn>"
    )
    assert render_chat(MESSAGES, template="phi") == (
        "<|system|>\nYou are helpful.<|end|>\n<|user|>\nHi<|end|>\n<|assistant|>\nHello!<|end|>"
    )


def test_unknown_template_fails_closed():
    with pytest.raises(ValueError, match="unknown-template"):
        render_chat(MESSAGES, template="unknown-template")


def test_serialize_chat_pairs():
    out = serialize_chat([{"user": "Hi", "assistant": "Hello!"}], template="qwen")
    assert out == [{"text": "<|im_start|>user\nHi<|im_end|>\n<|im_start|>assistant\nHello!<|im_end|>"}]


def test_builtin_template_set():
    assert set(CHAT_TEMPLATES) == {"llama3", "mistral", "qwen", "gemma", "phi"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/serializers -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.serializers'`

- [ ] **Step 3: Write the implementation**

```python
# src/veriformis/serializers/formats.py
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
```

```python
# src/veriformis/serializers/chat.py
"""Chat-template rendering. Templates are Jinja2, matching the HF chat_template
convention so output is byte-identical to what a trainer produces."""
from __future__ import annotations

from importlib import resources

from jinja2 import Template

_TEMPLATE_NAMES = ("llama3", "mistral", "qwen", "gemma", "phi")


def _load() -> dict[str, str]:
    out = {}
    for name in _TEMPLATE_NAMES:
        ref = resources.files("veriformis.serializers.templates.chat").joinpath(f"{name}.jinja")
        out[name] = ref.read_text(encoding="utf-8")
    return out


CHAT_TEMPLATES: dict[str, str] = _load()


def render_chat(messages: list[dict[str, str]], *, template: str) -> str:
    if template not in CHAT_TEMPLATES:
        raise ValueError(f"unknown-template: {template!r} (have: {sorted(CHAT_TEMPLATES)})")
    return Template(CHAT_TEMPLATES[template]).render(messages=messages)


def serialize_chat(records: list[dict], *, template: str) -> list[dict]:
    out = []
    for record in records:
        messages = []
        if record.get("system"):
            messages.append({"role": "system", "content": record["system"]})
        messages.append({"role": "user", "content": record["user"]})
        messages.append({"role": "assistant", "content": record["assistant"]})
        out.append({"text": render_chat(messages, template=template)})
    return out
```

```jinja
<|begin_of_text|>{% for m in messages %}<|start_header_id|>{{ m.role }}<|end_header_id|>

{{ m.content }}<|eot_id|>{% endfor %}
```
(file: `src/veriformis/serializers/templates/chat/llama3.jinja`)

```jinja
{% for m in messages %}<|im_start|>{{ m.role }}
{{ m.content }}<|im_end|>{% if not loop.last %}
{% endif %}{% endfor %}
```
(file: `src/veriformis/serializers/templates/chat/qwen.jinja`)

```jinja
<s>[INST] {% if messages[0].role == "system" %}{{ messages[0].content }}

{% endif %}{{ messages | selectattr("role", "equalto", "user") | map(attribute="content") | first }} [/INST] {{ messages | selectattr("role", "equalto", "assistant") | map(attribute="content") | first }}</s>
```
(file: `src/veriformis/serializers/templates/chat/mistral.jinja`)

```jinja
<bos><start_of_turn>user
{% if messages[0].role == "system" %}{{ messages[0].content }}

{% endif %}{{ messages | selectattr("role", "equalto", "user") | map(attribute="content") | first }}<end_of_turn>
<start_of_turn>model
{{ messages | selectattr("role", "equalto", "assistant") | map(attribute="content") | first }}<end_of_turn>
```
(file: `src/veriformis/serializers/templates/chat/gemma.jinja`)

```jinja
{% for m in messages %}<|{{ m.role }}|>
{{ m.content }}<|end|>{% if not loop.last %}
{% endif %}{% endfor %}
```
(file: `src/veriformis/serializers/templates/chat/phi.jinja`)

Template/output notes for the implementer (the golden tests are the contract):
- **No `{# #}` comment lines and no leading whitespace inside a `.jinja` template file** — a comment renders empty but the newline after it is emitted into the output. Put commentary here, never in the template.
- qwen/phi separate messages with `\n` via `{% if not loop.last %}` so there is no trailing newline after the last message; llama3/mistral/gemma need no separator logic.
- Jinja2's default `keep_trailing_newline=False` strips the template file's own final newline, so a normal file-ending newline in the `.jinja` file is safe.
- If a rendered output still differs from a golden string, adjust the template's whitespace control, never the golden string — unless the golden string is provably wrong against the model family's documented format.
- The mistral/gemma templates are single-exchange v1 (first user + first assistant turn, system folded into the first user turn); multi-turn support is a later milestone and must not be improvised.

```python
# src/veriformis/serializers/__init__.py
from veriformis.serializers.chat import CHAT_TEMPLATES, render_chat, serialize_chat  # noqa: F401
from veriformis.serializers.formats import serialize_completion, serialize_instruction  # noqa: F401
```

```python
# src/veriformis/serializers/templates/__init__.py
```

```python
# src/veriformis/serializers/templates/chat/__init__.py
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/serializers -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/serializers tests/serializers
git commit -m "feat(serializers): completion/instruction/chat with golden-tested model templates"
```

---

### Task 10: Validation gates

**Files:**
- Create: `src/veriformis/validate/__init__.py`, `src/veriformis/validate/gates.py`
- Test: `tests/validate/test_gates.py`

**Interfaces:**
- Consumes: Task 3 `SourceRef`, Task 8 `Chunk`.
- Produces (used by Tasks 11–12):
  - `GateResult(gate: str, passed: bool, messages: list[str])`.
  - `RECORD_SCHEMAS: dict[str, set[str]]` — `{"completion": {"text"}, "instruction": {"instruction","input","output"}, "chat": {"text"}}`.
  - `gate_schema(records: list[dict], format: str) -> GateResult`.
  - `gate_encoding(texts: list[str]) -> GateResult` — flags U+FFFD, common mojibake sequences (`â€™`, `Ã©`, `Ã¨`, `Ã¶`, `Ã¼`, `Ã¤`, `Â`), and control chars other than `\n`/`\t`.
  - `gate_provenance(chunks: list[Chunk], sources: dict[str, SourceRef]) -> GateResult` — per chunk: source registered; `block_index >= 0`; if `span` present: bounds within stream; if also not `transformed`: whitespace-normalized equality of `stream[span]` vs `chunk.text`; `span=None` → linkage checks only.
  - `run_gates(records, format, chunks, sources) -> list[GateResult]` — all three, in that order.

- [ ] **Step 1: Write the failing test**

```python
# tests/validate/test_gates.py
from veriformis.chunkers.base import Chunk
from veriformis.sources import SourceRef
from veriformis.validate.gates import (
    gate_encoding, gate_provenance, gate_schema, run_gates,
)


def _source(stream="alpha beta"):
    return SourceRef(id="s1", path="f.txt", sha256="x", size=10, parser="text", extracted_text=stream)


def test_schema_gate():
    assert gate_schema([{"text": "a"}], "completion").passed
    bad = gate_schema([{"txt": "a"}], "completion")
    assert not bad.passed and bad.messages


def test_encoding_gate():
    assert gate_encoding(["clean text\nwith\ttabs"]).passed
    assert not gate_encoding(["mojibake â€™ here"]).passed
    assert not gate_encoding(["control\x01char"]).passed


def test_provenance_gate_exact_and_transformed():
    src = _source()
    good = Chunk(id="c1", source_id="s1", block_index=0, span=_span(0, 5),
                 heading_path=[], text="alpha", tokens_est=2, transformed=False)
    assert gate_provenance([good], {"s1": src}).passed
    edited = Chunk(id="c2", source_id="s1", block_index=0, span=_span(0, 5),
                   heading_path=[], text="ALPHA", tokens_est=2, transformed=True)
    assert gate_provenance([edited], {"s1": src}).passed  # linkage only
    stale = Chunk(id="c3", source_id="s1", block_index=0, span=_span(0, 5),
                  heading_path=[], text="ALPHA", tokens_est=2, transformed=False)
    assert not gate_provenance([stale], {"s1": src}).passed  # slice mismatch, not marked
    missing = Chunk(id="c4", source_id="nope", block_index=0, span=None,
                    heading_path=[], text="x", tokens_est=1)
    assert not gate_provenance([missing], {"s1": src}).passed


def test_run_gates_order():
    results = run_gates([{"text": "a"}], "completion", [], {})
    assert [r.gate for r in results] == ["schema", "encoding", "provenance"]


def _span(a, b):
    from veriformis.ir import Span

    return Span(a, b)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/validate -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.validate'`

- [ ] **Step 3: Write the implementation**

```python
# src/veriformis/validate/gates.py
"""Validation gates. All gates report; sealing requires every gate to pass."""
from __future__ import annotations

from dataclasses import dataclass, field

from veriformis.chunkers.base import Chunk
from veriformis.sources import SourceRef


@dataclass
class GateResult:
    gate: str
    passed: bool
    messages: list[str] = field(default_factory=list)


RECORD_SCHEMAS: dict[str, set[str]] = {
    "completion": {"text"},
    "instruction": {"instruction", "input", "output"},
    "chat": {"text"},
}

_MOJIBAKE = ("â€™", "Ã©", "Ã¨", "Ã¶", "Ã¼", "Ã¤", "Â", "�")


def gate_schema(records: list[dict], format: str) -> GateResult:
    required = RECORD_SCHEMAS[format]
    problems = [
        f"record {i}: keys {sorted(r)} != required {sorted(required)}"
        for i, r in enumerate(records)
        if set(r) != required or not all(isinstance(r[k], str) for k in required)
    ]
    return GateResult("schema", not problems, problems[:20])


def gate_encoding(texts: list[str]) -> GateResult:
    problems = []
    for i, text in enumerate(texts):
        for marker in _MOJIBAKE:
            if marker in text:
                problems.append(f"text {i}: mojibake marker {marker!r}")
                break
        bad = [c for c in text if ord(c) < 0x20 and c not in "\n\t"]
        if bad:
            problems.append(f"text {i}: control char U+{ord(bad[0]):04X}")
    return GateResult("encoding", not problems, problems[:20])


def _squash(s: str) -> str:
    return "".join(s.split())


def gate_provenance(chunks: list[Chunk], sources: dict[str, SourceRef]) -> GateResult:
    problems = []
    for chunk in chunks:
        source = sources.get(chunk.source_id)
        if source is None:
            problems.append(f"{chunk.id}: unregistered source {chunk.source_id!r}")
            continue
        if chunk.block_index < 0:
            problems.append(f"{chunk.id}: invalid block_index")
        if chunk.span is None:
            continue  # linkage-only chunk (e.g. sentence-packed)
        stream = source.extracted_text
        if not (0 <= chunk.span.start < chunk.span.end <= len(stream)):
            problems.append(f"{chunk.id}: span out of bounds")
            continue
        if not chunk.transformed:
            if _squash(stream[chunk.span.start:chunk.span.end]) != _squash(chunk.text):
                problems.append(f"{chunk.id}: span content mismatch (not marked transformed)")
    return GateResult("provenance", not problems, problems[:20])


def run_gates(records, format, chunks, sources) -> list[GateResult]:
    texts = [r.get("text") or r.get("output", "") for r in records]
    return [
        gate_schema(records, format),
        gate_encoding(texts),
        gate_provenance(chunks, sources),
    ]
```

```python
# src/veriformis/validate/__init__.py
from veriformis.validate.gates import (  # noqa: F401
    GateResult, RECORD_SCHEMAS, gate_encoding, gate_provenance, gate_schema, run_gates,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/validate -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/validate tests/validate
git commit -m "feat(validate): schema/encoding/provenance gates, fail-closed"
```

---

### Task 11: Bundle writer + seal

**Files:**
- Create: `src/veriformis/errors.py`, `src/veriformis/bundle/__init__.py`, `src/veriformis/bundle/manifest.py`, `src/veriformis/bundle/writer.py`
- Test: `tests/bundle/test_writer.py`

**Interfaces:**
- Consumes: all earlier tasks.
- Produces (used by Task 12 CLI):
  - `errors.py`: `VeriformisError(Exception)` base with `.code: str`; `ParseError`, `UnsupportedInputError`, `RuleError`, `GateFailure` subclasses.
  - `Manifest` pydantic model: `bundle_id: str` (uuid4 hex), `created_at: str` (UTC ISO-8601), `veriformis_version: str`, `sources: list[SourceEntry]` (id/path/sha256/size/parser — no extracted_text), `transforms: list[TransformEntry]`, `chunks: list[ChunkEntry]` (id/source_id/block_index/span as `{start,end,page}` or null/heading_path/tokens_est/transformed), `dataset: DatasetInfo{format, template, record_count, total_chars, total_tokens_est}`, `validations: list[ValidationEntry]`, `files: dict[str, str]` (relative path → sha256).
  - `write_bundle(out_dir, *, records, chunks, sources, transforms, validations, format, template) -> Path` — raises `GateFailure` if any validation failed; writes `dataset.jsonl` + `manifest.json` (hashes computed over written files).
  - `verify_bundle(bundle_dir) -> bool` — recomputes `files` hashes against `manifest.json`.

- [ ] **Step 1: Write the failing test**

```python
# tests/bundle/test_writer.py
import json

import pytest

from veriformis.bundle.writer import verify_bundle, write_bundle
from veriformis.chunkers.base import Chunk
from veriformis.errors import GateFailure
from veriformis.ir import Span
from veriformis.rules.engine import TransformRecord
from veriformis.sources import SourceRef
from veriformis.validate.gates import GateResult


def _inputs(passed=True):
    source = SourceRef(id="s1", path="f.txt", sha256="ab", size=5, parser="text", extracted_text="hello world")
    chunk = Chunk(id="chk-0001", source_id="s1", block_index=0, span=Span(0, 5),
                  heading_path=[], text="hello", tokens_est=2, transformed=False)
    transforms = [TransformRecord(rule="whitespace", params={}, block_index=0, edits=1, bytes_removed=2, warned=False)]
    validations = [GateResult("schema", passed, [] if passed else ["bad record"])]
    return dict(
        records=[{"text": "hello"}], chunks=[chunk], sources=[source],
        transforms=transforms, validations=validations, format="completion", template=None,
    )


def test_write_and_verify_bundle(tmp_path):
    out = write_bundle(tmp_path / "b.vfbundle", **_inputs())
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["dataset"]["record_count"] == 1
    assert manifest["sources"][0]["sha256"] == "ab"
    assert manifest["files"]["dataset.jsonl"]
    assert verify_bundle(out) is True
    (out / "dataset.jsonl").write_text('{"text": "tampered"}\n')
    assert verify_bundle(out) is False


def test_seal_refuses_failed_gate(tmp_path):
    with pytest.raises(GateFailure):
        write_bundle(tmp_path / "b.vfbundle", **_inputs(passed=False))
    assert not (tmp_path / "b.vfbundle" / "manifest.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/bundle -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.bundle'`

- [ ] **Step 3: Write the implementation**

```python
# src/veriformis/errors.py
"""Typed errors shared by every surface (CLI, MCP, GUI)."""
from __future__ import annotations


class VeriformisError(Exception):
    code = "veriformis-error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ParseError(VeriformisError):
    code = "parse-error"


class UnsupportedInputError(VeriformisError):
    code = "unsupported-input"


class RuleError(VeriformisError):
    code = "rule-error"


class GateFailure(VeriformisError):
    code = "gate-failure"
```

```python
# src/veriformis/bundle/manifest.py
"""The sealed manifest: provenance, transforms, validations, and file hashes."""
from __future__ import annotations

from pydantic import BaseModel


class SourceEntry(BaseModel):
    id: str
    path: str
    sha256: str
    size: int
    parser: str


class TransformEntry(BaseModel):
    rule: str
    params: dict
    block_index: int
    edits: int
    bytes_removed: int
    warned: bool


class SpanEntry(BaseModel):
    start: int
    end: int
    page: int | None = None


class ChunkEntry(BaseModel):
    id: str
    source_id: str
    block_index: int
    span: SpanEntry | None
    heading_path: list[str]
    tokens_est: int
    transformed: bool


class DatasetInfo(BaseModel):
    format: str
    template: str | None
    record_count: int
    total_chars: int
    total_tokens_est: int


class ValidationEntry(BaseModel):
    gate: str
    passed: bool
    messages: list[str]


class Manifest(BaseModel):
    bundle_id: str
    created_at: str
    veriformis_version: str
    sources: list[SourceEntry]
    transforms: list[TransformEntry]
    chunks: list[ChunkEntry]
    dataset: DatasetInfo
    validations: list[ValidationEntry]
    files: dict[str, str]
```

```python
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
```

```python
# src/veriformis/bundle/__init__.py
from veriformis.bundle.manifest import Manifest  # noqa: F401
from veriformis.bundle.writer import verify_bundle, write_bundle  # noqa: F401
```

Note for the implementer: the manifest self-hash is written as `"pending"` on the first write, then the file is rewritten with the real hash of that first write — `verify_bundle` deliberately skips self-verification (a file cannot hash itself). The two-phase write exists so tampering with `dataset.jsonl` or any future added file is always detected, which is what the test asserts.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/bundle -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/errors.py src/veriformis/bundle tests/bundle
git commit -m "feat(bundle): fail-closed sealer with provenance manifest + hash verification"
```

---

### Task 12: CLI (stage commands)

**Files:**
- Create: `src/veriformis/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: Tasks 1–11.
- Produces: `veriformis` console script with commands: `parse`, `clean`, `chunk`, `format`, `validate`, `seal`, `preview`, `version`. Workspace directory layout (created by `parse`, consumed by later commands):
```
<workspace>/
  registry.json          # list[SourceEntry-like dict WITHOUT extracted_text]
  <stem>.ir.json         # Document (serde dict)
  <stem>.extracted.txt   # extracted stream
  transforms.json        # list[TransformRecord dicts]      (written by clean)
  chunks.json            # list[Chunk dicts]                (written by chunk)
  records.jsonl          # records                          (written by format)
  validations.json       # list[GateResult dicts]           (written by validate)
```
- `parse PATHS... -o WORKSPACE` — extension dispatch: `.txt` → text parser; `.md`/`.markdown` → markdown; `.docx` → docx; code extensions (`.py .js .ts .java .c .cpp .go .rs .rb .sh`) → text parser with `language=<ext>`; anything else → `UnsupportedInputError` printed, exit code 2.
- `clean WORKSPACE --rules page-numbers,whitespace [--custom PATTERN]` — defaults to `default_rules()`.
- `chunk WORKSPACE --strategy paragraph|fixed|sliding|sentence|structure [--size N] [--overlap N]`.
- `format WORKSPACE --format completion|instruction|chat [--template llama3|...] [--instruction TEXT] [--with-heading-path]`.
- `validate WORKSPACE --format completion|instruction|chat` — runs `run_gates`, writes `validations.json`, exits 1 if any gate failed.
- `seal WORKSPACE -o BUNDLE_DIR` — calls `write_bundle`; on `GateFailure` prints the failure and exits 1.
- `preview PATH --rules ...` — dry-run cleaning on one file; prints transform log + before/after excerpt; writes nothing.
- `version` — prints `veriformis.__version__`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
import json

from typer.testing import CliRunner

from veriformis.cli import app

runner = CliRunner()


def test_full_pipeline_on_text_file(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("First paragraph here.\n\n37\n\nSecond paragraph here.", encoding="utf-8")
    ws = tmp_path / "ws"

    result = runner.invoke(app, ["parse", str(src), "-o", str(ws)])
    assert result.exit_code == 0, result.output
    assert (ws / "notes.ir.json").exists()

    result = runner.invoke(app, ["clean", str(ws)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["chunk", str(ws), "--strategy", "paragraph"])
    assert result.exit_code == 0, result.output
    chunks = json.loads((ws / "chunks.json").read_text())
    assert len(chunks) >= 1

    result = runner.invoke(app, ["format", str(ws), "--format", "completion"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["validate", str(ws), "--format", "completion"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["seal", str(ws), "-o", str(tmp_path / "out.vfbundle")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out.vfbundle" / "manifest.json").exists()


def test_parse_rejects_unknown_extension(tmp_path):
    bad = tmp_path / "data.xyz"
    bad.write_text("x")
    result = runner.invoke(app, ["parse", str(bad), "-o", str(tmp_path / "ws2")])
    assert result.exit_code == 2
    assert "unsupported" in result.output.lower()


def test_preview_writes_nothing(tmp_path):
    src = tmp_path / "doc.txt"
    src.write_text("line\n\n42\n\nmore")
    result = runner.invoke(app, ["preview", str(src)])
    assert result.exit_code == 0
    assert "page-numbers" in result.output
    assert list(tmp_path.iterdir()) == [src]


def test_preview_covers_all_blocks(tmp_path):
    src = tmp_path / "doc.txt"
    src.write_text("line\n\n42\n\nmore")
    result = runner.invoke(app, ["preview", str(src)])
    assert result.exit_code == 0
    after = result.output.split("--- after ---")[-1]
    assert "42" not in after  # whole-file dry run, not just the first block


def test_validate_rejects_unknown_format(tmp_path):
    result = runner.invoke(app, ["validate", str(tmp_path), "--format", "bogus"])
    assert result.exit_code == 2
    assert "unknown format" in result.output.lower()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0 and "0.1.0" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veriformis.cli'`

- [ ] **Step 3: Write the implementation**

```python
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
```

Amendment (Task-12 review, 2026-07-28): two review findings fixed at plan level. (1) `preview` now cleans the whole extracted stream (`result.source.extracted_text`) — the original listing cleaned only `children[0]`, silently misrepresenting multi-paragraph files and contradicting this task's "dry-run cleaning on one file" interface. (2) `validate` rejects unknown `--format` values with a clean exit 2 (membership check against `RECORD_SCHEMAS`), matching the sibling commands' error convention; previously an unknown format crashed with a raw `KeyError`. Two tests pin the corrected behaviors.

- [ ] **Step 4: Run full suite to verify everything passes**

Run: `uv run pytest -q && uv run ruff check src tests`
Expected: all tests PASS; ruff reports no findings.

- [ ] **Step 5: Commit**

```bash
git add src/veriformis/cli.py tests/test_cli.py
git commit -m "feat(cli): stage commands (parse/clean/chunk/format/validate/seal/preview/version)"
```

---

## M1 definition of done

- `uv run pytest -q` green across `tests/` (scaffold, ir, parsers, rules, chunkers, serializers, validate, bundle, cli).
- `uv run ruff check src tests` clean.
- End-to-end on a real file: `veriformis parse notes.txt -o ws && veriformis clean ws && veriformis chunk ws && veriformis format ws --format completion && veriformis validate ws --format completion && veriformis seal ws -o out.vfbundle` produces a sealed bundle whose `manifest.json` shows the source hash, transform log, chunk provenance, passing gates, and file hashes.
- Privacy grep clean: no donor-project identifiers anywhere in the repo.
