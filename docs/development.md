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

Run both checks before submitting a change:

```bash
uv run ruff check src tests
uv run pytest -q
```

The verified `0.1.0` baseline contains 50 passing tests.

For focused work:

```bash
uv run pytest tests/parsers/test_markdown.py -q
uv run pytest tests/test_cli.py -q
```

## Repository layout

```text
.
├── src/veriformis/
│   ├── parsers/
│   ├── ir/
│   ├── rules/
│   ├── chunkers/
│   ├── serializers/
│   ├── validate/
│   ├── bundle/
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
| Canonical IR | `tests/ir/` |
| Text, Markdown, DOCX | `tests/parsers/` |
| Cleaning rules and safety | `tests/rules/` |
| Chunk coverage and provenance | `tests/chunkers/` |
| Record and chat serialization | `tests/serializers/` |
| Validation gates | `tests/validate/` |
| Bundle seal and tamper check | `tests/bundle/` |

Add a regression test before repairing an integrity defect. Multi-source fixtures are especially important because current stem, chunk-ID, and block-index identities can collide.

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

### Treat workspace artifacts as unsafe mutable state

Until transactional revisions exist, tests should assume that upstream reruns can leave stale downstream files. Do not broaden sealing claims around the current mutable workspace.

### Separate construction from serialization

The existing CLI format branches combine record construction and serialization. New work should follow the roadmap contract: a declared objective and evidence-bearing construction pass should create records, then a serializer should lower accepted records into a target schema.

### Do not strengthen unsupported claims

Current validation has only schema, encoding, and provenance gates. Current verification does not authenticate the manifest or reject extra files. Documentation and tests must state those boundaries precisely.

## Adding a parser

A parser should:

1. produce the canonical IR;
2. build one canonical extracted-text stream;
3. assign top-level block indexes and valid spans into that stream;
4. register the original file hash and parser identity;
5. report unsupported or lost structures explicitly;
6. include adversarial fixtures, not only a happy-path sample.

Additional declared input formats are planned for roadmap step 20. They are not part of `0.1.0`.

## Adding a rule

A cleaning rule should be deterministic, preserve document meaning, and return exact edit ranges. Add tests for normal input, false-positive resistance, and the 30 percent removal safety threshold.

Remember that `clean_document` currently runs rules per top-level block, while `preview` runs against the whole canonical stream. The roadmap replaces this divergence with replayable edit plans.

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
- [Current implementation status](current-status.md)
- [Architecture](architecture.md)
- [CLI reference](cli.md)
- [Build roadmap](plans/2026-07-29-veriformis-roadmap.md)
- [Contributing](../CONTRIBUTING.md)
