# Veriformis — Design Spec

**Date:** 2026-07-28 · **Status:** Draft for owner review · **Repo:** github.com/ogprotege/Veriformis

> **Veriformis** *(verus + forma, "true-formed")* — a local-first macOS dataset compiler.
> Raw documents in → validated, provenance-sealed training bundles for LLM fine-tuning out.
> Sibling product to **Aptus** (which plans/compiles the training run); Veriformis supplies
> the ground truth Aptus trains on.

---

## 1. Problem

Preparing a corpus for fine-tuning is the most painful, error-prone stage of the workflow:
documents arrive in mixed formats (PDF, DOCX, HTML, MD, TXT, code, CSV/JSON), every
conversion leaks or silently drops content, cleaning rules destroy data without record, and
the final step — shaping text into the exact chat/instruction template a model family
expects — is done by hand with no validation. Nothing in the chain talks to anything else
without a translation barrier, and nothing tells you what was lost along the way.

Existing options are libraries (Unstructured, Docling) or cloud services (LlamaParse).
None are a local, private, Mac-native workbench with a complete audit trail and
fine-tuning-native output formats.

## 2. Product doctrine (non-negotiables)

1. **Canonical IR, hub-and-spoke.** Every input format parses into one document IR; every
   output format serializes from it. N parsers + M serializers, never N×M converters —
   the proven doctrine for markup conversion.
2. **Nothing silent.** Originals are preserved by SHA-256. Every transformation is logged
   with what changed, where, and why. Every output chunk traces back to source document,
   page, and character offsets. "Lossless" means *provably nothing critical lost* — not a
   marketing word.
3. **Fail-closed.** A bundle that fails validation does not seal. An unsupported input
   (e.g., a scanned PDF with no text layer) is refused with a clear reason, never
   processed into garbage. (Aptus's evidence-ladder ethos, applied one stage earlier.)
4. **Deterministic or it doesn't ship (v1).** No LLM calls inside the pipeline. Cleaning,
   chunking, structuring, validating are all deterministic and testable.
5. **Local and private.** No cloud, no accounts, no telemetry. Documents never leave the
   machine. (The corpus may be sensitive — e.g., unpublished scholarly material.)

## 3. Scope

### v1 in scope
- **Inputs:** Markdown, DOCX, plain text, HTML, digitally-born PDF (text layer present),
  source code files, JSON/CSV/JSONL (already-structured, validated passthrough).
- **Language:** English.
- **Outputs:** JSONL training bundles — completion, instruction (Alpaca-style), and chat
  formats with per-model-family templates (Llama 3, Mistral/Mixtral, Qwen 2/3, Gemma,
  Phi) plus user-defined custom templates.
- **Surfaces:** Python library, CLI, MCP server, macOS GUI (SwiftUI shell).
- **Integration:** export bundle satisfies Aptus's supervised-dataset contract.

### Explicitly out of scope (v1)
- OCR / scanned documents (refused cleanly; future horizon — the IR and provenance model
  are designed so page-image lineage and script metadata can be added without rework).
- Non-English language handling (same future-horizon design accommodation).
- LLM-based QA-pair / synthetic-data generation.
- Cloud sync, multi-user, auth, billing.
- Actual training (that is Aptus's job).

## 4. Architecture

One Python core, three thin front doors. Mirrors the owner's proven patterns:
one engine shared by CLI and MCP surfaces, and a SwiftUI shell over an embedded
Python backend on the desktop.

```
┌──────────────────────────── surfaces ────────────────────────────┐
│  veriformis CLI      MCP server      macOS GUI (SwiftUI shell)    │
└──────────────┬──────────────┬──────────────────┬─────────────────┘
               └──────────────┴──────┬───────────┘
                                     │ python API
┌────────────────────────────────────▼─────────────────────────────┐
│  pipeline orchestrator (yaml-driven, also single-call API)        │
├─────────┬──────────┬──────────┬────────────┬──────────┬──────────┤
│ parsers │ rules    │ chunkers │ serializers│ validate │ bundle   │
│ → IR    │ (clean)  │          │ (format)   │ (gates)  │ (seal)   │
└─────────┴──────────┴──────────┴────────────┴──────────┴──────────┘
```

### 4.1 Document IR (`ir/`)
The spine: a canonical document model with first-class provenance, designed for
roundtrip fidelity.

- **Block nodes:** heading(level), paragraph, list(ordered?, depth), list_item, blockquote,
  code_block(language), table, image(ref, alt), math, footnote/endnote, thematic_break.
- **Inline:** text spans with marks — bold, italic, code, link, superscript, subscript,
  citation marker.
- **Provenance:** every block carries `source_id`, optional `page`, and char offsets
  into the source's extracted text stream.
- Serializable to/from JSON (roundtrip-testable: parse → IR → serialize → parse ≡ identity).

### 4.2 Parsers (`parsers/`)
One module per format, each emitting IR + registering the source (path, sha256, size).
The md/docx pair is vendor-and-extend work (decision D1, §12) — proven canonical-IR
parsing code taken in-house and extended to attach provenance, no runtime dependency.
- `md` — canonical-IR markdown parser with provenance attachment.
- `docx` — OOXML (unzipped-XML) parser on the same IR, with provenance.
- `txt` / `code` — trivial; code keeps language tag from extension.
- `html` — readability-style main-content extraction → IR (see D4, §12).
- `pdf` — **pypdfium2** (Apache-2.0/BSD; *not* PyMuPDF, which is AGPL and would poison
  distribution). Page-level extraction preserves page provenance. Scanned/no-text-layer
  PDFs → fail-closed refusal naming OCR as the missing capability.
- `json`/`csv`/`jsonl` — structured passthrough with schema validation (feeds the
  serializer stage directly).

### 4.3 Cleaning rules (`rules/`)
Deterministic, ordered, composable rules; every firing logged as a transform record
(rule id, params, affected spans, bytes removed). Dry-run/preview is a first-class API
(the GUI's before/after view depends on it).

Rule library (from the salvaged UDP taxonomy, with its two known bugs fixed):
- `remove_headers_footers` — repeated line detection across pages (not naive ALL-CAPS).
- `remove_page_numbers` — **line-anchored** patterns only (`^\s*\d+\s*$`,
  `^Page \d+( of \d+)?$`). The tunerepo regex that deleted every standalone number is the
  canonical regression test.
- `normalize_whitespace`, `remove_urls`, `remove_emails`, `remove_special_chars`
  (whitelist-based, conservative), `to_lowercase`, `custom_regex` (user-supplied, logged
  verbatim).
- Safety valve: any rule that would remove more than a configurable fraction
  (default 30%) of a document warns instead of silently applying.

### 4.4 Chunkers (`chunkers/`)
- `fixed` (size + overlap), `sentence` (rule-based English splitter with abbreviation
  guard), `paragraph`, `sliding` (window + overlap; **short-document edge case fixed** —
  a doc smaller than the window yields one chunk, never zero), `structure` (heading-path
  aware: chunks never cross section boundaries; heading path stored as context).
- Every chunk carries: `chunk_id`, `source_id`, IR block path, char start/end,
  `heading_path`, token estimate.

### 4.5 Serializers (`serializers/`)
- `completion` — chunk text as-is (optionally with heading-path prefix).
- `instruction` — instruction/input/output field mapping (Alpaca-style).
- `chat` — per-model-family templates. Templates are **Jinja2**, matching Hugging Face
  `chat_template` convention, so output is byte-identical to what the trainer sees.
  Built-ins: llama-3, mistral, qwen2/3 (`<|im_start|>` family), gemma, phi. Users can add
  custom templates by name.
- `custom` — user Jinja template over chunk/QA fields.
- Structured inputs (CSV/JSONL with question/answer or messages columns) route here
  directly after validation.

### 4.6 Validation gates (`validate/`)
All gates report; the bundle seals only if every *required* gate passes.
- `schema` — output conforms to the target format's JSON Schema.
- `encoding` — valid UTF-8, no mojibake/control-char pollution.
- `provenance` — every chunk resolves to a live source span (integrity check).
- `dedup` — exact-hash duplicates always reported; near-dup (shingle/Jaccard) behind a flag
  (decision D2, §12).
- `pii` — regex-based email/phone/SSN/etc. scan; reports matches, never auto-redacts
  (the owner decides — nothing silent).
- `stats` — document/chunk counts, length distribution, char+estimated-token totals
  (exact tokenizer counts available via optional extra — decision D3, §12).

### 4.7 Bundle & seal (`bundle/`)
Output bundle:
```
my-dataset.vfbundle/
├── dataset.jsonl              # (or multiple split files)
├── manifest.json              # the seal — see below
├── sources/                   # optional: copies of originals
└── aptus-dataset.json         # Aptus dataset-contract descriptor
```
`manifest.json`: bundle id, created-at, veriformis version, sources[] (path, sha256,
size, parser, pages), transforms[] (full cleaning log), chunks[] (provenance map),
dataset (format, template, counts, stats), validations[] (per-gate results), and a
SHA-256 of every emitted file. Sealing recomputes and writes hashes; any later tampering
is detectable.

### 4.8 Surfaces
- **CLI (`veriformis`)** — typer. Stage commands (`parse`, `clean`, `chunk`, `format`,
  `validate`, `seal`) plus `veriformis run pipeline.yaml` for end-to-end batch, and
  `veriformis preview` for dry-run cleaning.
- **MCP server (`mcp/`)** — built on fastmcp; tools like `veriformis_ingest`,
  `veriformis_preview_clean`, `veriformis_build`, `veriformis_validate`. Lets
  Claude/Cursor drive dataset prep conversationally against the same engine.
- **macOS GUI (`desktop/macos/`)** — SwiftUI shell + embedded Python backend, cloning
  Aptus's proven packaging (PyInstaller backend spec, local IPC). Five screens matching
  the pipeline: **Sources** (drag-drop, hash register) → **Clean** (rule toggles, live
  before/after diff) → **Chunk** (strategy + parameters + preview) → **Format** (template
  picker, field mapping, rendered-sample preview) → **Seal** (gate dashboard, export).
  UX reference: salvaged tunerepo UDP playground (its layout, not its code).

## 5. Data flow

```
raw files ──parse──▶ IR docs (+source registry, sha256)
         ──clean──▶ IR docs' (+transform log per rule firing)
         ──chunk──▶ chunks (+provenance: source/block/offsets/heading-path)
         ──format─▶ jsonl records (template-rendered)
         ──gates──▶ validation report (fail-closed)
         ──seal───▶ bundle: jsonl + manifest.json + hashes (+ aptus descriptor)
```

## 6. Error handling

- Every stage has typed errors (`ParseError`, `UnsupportedInputError`, `RuleError`,
  `GateFailure`) carrying human-readable reasons and machine codes.
- Unsupported input → refusal with the missing capability named (e.g., "scanned PDF —
  OCR not supported in v1"). Never partial garbage.
- Gate failure → bundle refuses to seal; report states exactly which gate and why.
- GUI/CLI/MCP all surface the same error objects.

## 7. Testing strategy

"Lossless" is a testable claim, and the suite is built to prove it:
- **Roundtrip fidelity:** IR → serialize → parse ≡ identity, per format.
- **Provenance integrity:** reconstruct each chunk's source span from the manifest and
  assert byte equality with the original.
- **Golden files:** fixture corpus per parser (including nasty cases: multi-column PDF,
  nested DOCX lists, malformed HTML, mixed encodings).
- **Rule-safety regressions:** the tunerepo number-deleting regex is enshrined as a test;
  every rule has must-keep/must-remove fixture pairs.
- **Property tests:** chunk coverage (no source text silently orphaned), size bounds,
  overlap correctness, sliding-window short-doc edge case.
- **Gate tests:** fail-closed behavior (bad bundle never seals; scanned PDF refused).
- **Template conformance:** rendered chat output diffed against reference tokenizer
  templates per model family.
- pytest; fixtures live in `tests/fixtures/`.

## 8. Stack & conventions

- Python 3.11+, `uv` + `pyproject.toml`, ruff (pinned, like Aptus), pytest, pydantic v2,
  typer, Jinja2, pypdfium2, trafilatura (D4), fastmcp.
- MIT license. Conventional commits. CI: GitHub Actions (lint + typecheck + tests).
- Code conventions follow Aptus: contract-first modules, typed boundaries,
  no silent mutation, docs that state scope limits up front.

## 9. Repo layout

```
Veriformis/
├── pyproject.toml / uv.lock
├── src/veriformis/
│   ├── ir/  parsers/  rules/  chunkers/  serializers/  validate/  bundle/
│   ├── pipeline/  cli.py  mcp/
├── desktop/macos/            # SwiftUI shell (M4)
├── tests/  fixtures/
├── docs/   (incl. this spec)
└── reference/tunerepo-salvage/   # lineage material (already imported)
```

## 10. Milestones

- **M1 — Core engine + CLI:** IR, md/txt/docx parsers, rule engine, chunkers,
  completion + instruction + chat serializers, schema/encoding/provenance gates,
  seal, pytest base.
- **M2 — Full ingest + gates:** pdf + html parsers, dedup + pii + stats gates, pipeline
  yaml runner.
- **M3 — MCP server.**
- **M4 — macOS GUI** (SwiftUI shell + embedded backend, Aptus packaging pattern).
- **M5 — Aptus bundle polish:** verified end-to-end handoff (Veriformis bundle → Aptus
  plan), joint docs.

## 11. Lineage & salvage

- **tunerepo-salvage** (`reference/tunerepo-salvage/`): UDP cleaning/chunking taxonomy as
  reference spec (two known bugs documented in `SALVAGE-MANIFEST.md` and covered by
  regression tests), UDP playground as UX reference. Everything else from tunerepo was
  deliberately destroyed; the old repo and staging folder are deletable once this file
  is committed.
- **Aptus** (`/Users/biscuit/Aptus`): desktop packaging pattern, dataset contract (the
  M5 integration target — exact contract to be read from Aptus source at implementation
  time), evidence/fail-closed philosophy. Aptus remains untouched.
- Certain md/docx parsing internals are vendored from the owner's prior private work
  (decision D1). That source is not named or referenced anywhere in this repository
  by request; it remains untouched.

## 12. Decisions

Resolved with the owner, 2026-07-28:

- **D1 — md/docx parsing:** vendor-and-extend prior internal code (no runtime
  dependency on the private source; provenance fields added in-house).
- **D2 — near-dup detection:** in v1, behind a flag (exact-hash always on).
- **D3 — token statistics:** estimates in core; exact tokenizer counts via optional
  extra (`veriformis[tokens]`).
- **D4 — HTML extraction:** trafilatura (MIT) primary; reassess at M2 if extraction
  quality disappoints on the golden-file corpus.
