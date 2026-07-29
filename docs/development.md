# Development Guide

This guide covers the implemented Veriformis `0.1.0` Python project. Planned services, applications, and release tooling are documented only in the [build roadmap](plans/2026-07-29-veriformis-roadmap.md).

## Requirements

- Python 3.11 or newer
- `uv`
- Git

The package uses a setuptools `src/` layout. Runtime dependencies are declared in `pyproject.toml` and locked in `uv.lock`.

## Set up the project

```bash
git clone https://github.com/ogprotege/Veriformis.git
cd Veriformis
uv sync --extra test
uv run veriformis --help
```

The test extra installs pytest and the repository-pinned Ruff version.

## Required checks

Run the project checks before submitting a change:

```bash
uv lock --check
uv run ruff check src tests
uv run pytest -q
git diff --check
```

For focused work:

```bash
uv run pytest tests/parsers/test_markdown.py -q
uv run pytest tests/test_cli.py -q
```

Rerun the commands above for current evidence. Test totals are intentionally
omitted because coverage grows. Strict expected failures remain pinned to
later-step defects.

## Repository layout

```text
.
├── src/veriformis/
│   ├── parsers/
│   ├── ir/
│   ├── rules/
│   ├── chunkers/
│   ├── construction/
│   ├── serializers/
│   ├── validate/
│   ├── bundle/
│   ├── contracts.py
│   ├── diagnostics.py
│   ├── evidence.py
│   ├── identity.py
│   ├── workspace.py
│   └── cli.py
├── tests/
├── docs/
├── pyproject.toml
└── uv.lock
```

The CLI is the current composition root. A surface-neutral `PipelineService` is planned but does not exist in `0.1.0`.

## Test map

| Area | Tests |
|---|---|
| Package and version | `tests/test_scaffold.py` |
| End-to-end CLI path | `tests/test_cli.py` |
| Product and parser contracts | `tests/contracts/` |
| Group 1 integrity regressions | `tests/regressions/` |
| Group 2 construction models, evidence, constructors, pipeline, and CLI | `tests/construction/` |
| Pinned later-step defects | `tests/known_gaps/` |
| Canonical IR | `tests/ir/` |
| Text, Markdown, DOCX | `tests/parsers/` |
| Cleaning rules and safety | `tests/rules/` |
| Chunk coverage and provenance | `tests/chunkers/` |
| Record and chat serialization | `tests/serializers/` |
| Validation gates | `tests/validate/` |
| Bundle seal and tamper check | `tests/bundle/` |

Add a regression test before repairing an integrity defect. Keep multi-source
fixtures because source scope and collision resistance are durable contracts.
Groups 1 and 2 defects must be ordinary passing tests. Later-step defects may remain
strict expected failures until their owning group repairs them.

## Continuous integration

GitHub Actions runs on pushes and pull requests. The current job uses Ubuntu, Python 3.12, uv, Ruff, and pytest.

CI does not yet run:

- a Python version matrix;
- a package build and installation smoke test;
- static type checking;
- coverage enforcement;
- dependency or security scanning;
- macOS packaging, signing, or installation checks.

Do not describe these as release gates until they exist. Roadmap Step 26 requires release evidence, but its detailed gate order still needs an implementation plan.

## Engineering constraints

### Keep current behavior deterministic and local

The implemented pipeline has no LLM or network stage. Do not introduce either casually. Governed model-assisted construction is a later, optional roadmap item.

### Preserve source evidence

Parser spans refer to the canonical extracted stream. Tests must verify both the emitted text and the span contract. If parsing drops or normalizes content, make that loss explicit rather than claiming raw-file fidelity.

Visible image alt text, citations, and note references belong in that canonical
projection. Body, footnote, and endnote blocks share one stream but must retain
distinct evidence regions. Group 2 `IRFieldEvidence` binds IR-only scalar
metadata to its exact source, artifact, RFC 6901 pointer, value digest,
encoding, output digest, and construction context.

Persist artifact JSON and construct durable identity and configuration-digest
payloads with exact-string serialization so distinct Unicode normalization
forms remain distinct. In those durable paths, normalize only fields whose
contracts explicitly define NFC equivalence, currently logical source paths.
Do not substitute an audit revision ID for a portable state digest or per-source
parse-input digest.

### Preserve revision integrity

Use `Workspace` transactions for every persisted stage result. Do not write
inter-stage files at the workspace root or mutate content-addressed objects.
Tests must cover atomic visibility, expected-revision conflicts, stale-stage
invalidation, duplicate identity rejection, and digest verification. The
transactional workspace does not imply that Step 16 atomic sealing is complete.

Parse, clean, chunk, and construct artifacts must pass their cross-artifact
semantic checks before `HEAD` promotion. Construction must reload its canonical
recipe and result and match a fresh deterministic replay over the exact selected
upstream inputs.

### Keep construction separate from serialization

Group 2 construction creates evidence-bearing accepted `DatasetRecord` values.
The legacy `format` branches still project chunks directly. Group 3 must make
new serializers lower accepted records without inventing an objective, target,
review state, curation result, or split assignment.

The cleaned corpus remains intermediate unless a `full_text` recipe explicitly
selects its retained sequences as targets. A constructor for any other
objective must prove its semantic field relation through replayable evidence.

### Do not strengthen unsupported claims

Current validation has only schema, encoding, and provenance gates. Current verification does not authenticate the manifest or reject extra files. Documentation and tests must state those boundaries precisely.

## Adding a parser

A parser should:

1. produce the canonical IR;
2. build one canonical extracted-text stream;
3. assign body and note block indexes, regions, and valid spans into that stream;
4. register the original file hash and parser identity;
5. report unsupported or lost structures explicitly;
6. serialize through the strict versioned IR and parse-report schemas;
7. include adversarial fixtures, not only a happy-path sample.

Additional declared input formats are planned for roadmap step 20. They are not part of `0.1.0`.

## Adding a rule

A cleaning rule should be deterministic, preserve document meaning, and return
exact edit ranges. Add tests for normal input, false-positive resistance, the
30 percent removal safety threshold, rich-node preservation, plan serialization,
and tamper rejection. Current prose rules must leave code, math, and other
literal payloads unchanged. Preview and application must use the same plan and
replay path. Given the same locator, bytes, parser, rules, and configuration,
raw preview, workspace preview, and clean must produce the same plan ID.

## Adding a constructor

A constructor must:

1. implement one declared objective and exact field shape;
2. dispatch through a versioned constructor ID;
3. bind each field to source-text or strict-IR evidence;
4. retain exact source, chunk, transform, recipe, objective, and pass lineage;
5. emit deterministic diagnostics for ineligible inputs or omissions;
6. remain pure, local, order-independent, and exactly replayable; and
7. include positive, negative, multi-source, Unicode, malformed, and tamper tests.

Do not treat `source-chunks-unavailable` as corpus-wide coverage accounting.
Curation and coverage are Group 3 concerns.

## Adding a chunker or serializer

Chunker tests should cover:

- complete source coverage or explicit rejection;
- empty and short inputs;
- heading context;
- transformed-block attribution;
- multi-source identity;
- span and overlap semantics.

Serializer tests should verify exact row fields and training-loss semantics. A serializer must not invent an instruction, target, review state, or training objective.

## Documentation discipline

Use present tense only for merged, tested behavior. Label roadmap items as planned. When behavior changes, update the CLI reference, architecture, limitations, and tests in the same pull request.

## Related documentation

- [Product contract](product-contract.md)
- [Integrity Contract v1](contracts/integrity-v1.md)
- [Dataset Construction Contract v1](contracts/dataset-construction-v1.md)
- [Current implementation status](current-status.md)
- [Architecture](architecture.md)
- [CLI reference](cli.md)
- [Build roadmap](plans/2026-07-29-veriformis-roadmap.md)
- [Contributing](../CONTRIBUTING.md)
