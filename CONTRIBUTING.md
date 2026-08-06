# Contributing to Veriformis

Veriformis is an alpha dataset compiler with strict source-fidelity and integrity goals. Contributions should improve the implemented product without overstating guarantees that the code does not yet provide.

## Start with the current contract

Before changing code, read:

- [Product contract](docs/product-contract.md)
- [Integrity Contract v1](docs/contracts/integrity-v1.md)
- [Dataset Construction Contract v1](docs/contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](docs/contracts/finished-dataset-v1.md)
- [Aptus Handoff Contract v1](docs/contracts/aptus-handoff-v1.md)
- [Current implementation status](docs/current-status.md) (Groups 1–7 + Group 9 automated gates)
- [Architecture](docs/architecture.md)
- [CLI reference](docs/cli.md)
- [Development guide](docs/development.md)
- [Release guide](docs/release.md)
- [Beta limitations](docs/beta-limitations.md)
- [macOS workbench](macos/README.md)
- [Build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md)

The roadmap is ordered. Groups 1–7 exit gates are closed on `main`. Group 9
automated gates (CI matrix, install smoke, golden compile) and beta-prep
docs/evidence are on `main`; maturity remains development **alpha**. Owner Mac
signing/notarization evidence remains for a **public Mac app** claim. Group 8
is optional and owner-gated. Do not describe the product as beta or
public-ready without the checklists in [docs/beta-limitations.md](docs/beta-limitations.md)
and [docs/release.md](docs/release.md).

After reading these authorities, consult [Work in progress](WIP.md) as the
non-authoritative reviewed work queue.

## Set up

```bash
uv sync --extra test
uv run ruff check src tests
uv run pytest -q
```

Python 3.11 or newer is required. CI runs Python 3.11–3.13 on Ubuntu plus
Python 3.12 on macOS, with install-smoke and golden-compile jobs (see
[docs/release.md](docs/release.md)).

## Choose a focused change

Keep each change centered on one behavior or one coherent roadmap step. Preserve unrelated worktree changes. Do not mix broad refactors, new features, and documentation replacement without a clear reason.

For integrity or provenance repairs:

1. write a failing regression test;
2. demonstrate the incorrect current behavior;
3. implement the smallest complete repair;
4. run focused tests;
5. run the full required checks;
6. update affected documentation.

## Required contribution standards

### Evidence and provenance

- Preserve original-file hashes and source identity.
- Keep canonical-stream and span semantics explicit.
- Report parser loss or refusal. Do not silently claim fidelity.
- Test multi-source behavior whenever identities or workspace state change.
- Keep validation facts bound to the artifacts they describe.

### Dataset semantics

- Do not label copied source text as a summary or another transformation that did not occur.
- Do not invent instructions or targets inside a serializer.
- Keep recipe source selection exact. Do not silently widen or narrow it.
- Bind every constructed field to replayable source-text or strict-IR evidence.
- Keep structured prompt and target boundaries when downstream masking depends on them.
- Treat human review as a recipe or policy state, not a universal prerequisite for dataset construction.
- Keep curation and split policy explicit, versioned, deterministic, and bound
  to the finished plan.
- Keep `0.1.0` deterministic and offline unless an approved roadmap step changes that boundary.

### Safety and compatibility

- Fail closed on unsupported formats and failed validation.
- Avoid destructive cleaning defaults.
- Add negative tests for malformed input and stale state.
- Preserve Python 3.11 compatibility even though current CI runs Python 3.12.
- Do not add a dependency without checking its license, maintenance status, and necessity.

### Documentation

- Use present tense only for implemented, merged, tested behavior.
- Put planned behavior in a clearly labeled section and link the roadmap.
- Update command examples when CLI flags or defaults change.
- State known integrity and provenance limitations directly.
- Do not claim a gate, input format, interface, or bundle guarantee that is not exercised by code and tests.

## Tests expected by change type

| Change | Minimum evidence |
|---|---|
| Parser | Structural fixture, canonical text, spans, refusal or loss diagnostics |
| Cleaning rule | Positive case, false-positive case, safety-threshold case |
| Chunker | Coverage, short input, identity, span, overlap or boundary behavior |
| Constructor | Declared objective, source evidence, negative semantic case |
| Serializer | Exact schema and loss-bearing field boundaries |
| Validation gate | Passing, failing, malformed, and stale-input cases |
| Bundle or workspace | Tamper, replay, collision, interruption, and recovery cases |
| CLI | Help contract, exit status, artifacts, and actionable error text |

## Pull request checklist

- [ ] The change has a narrow stated purpose.
- [ ] New behavior has regression or acceptance tests.
- [ ] `uv run ruff check src tests` passes.
- [ ] `uv run pytest -q` passes.
- [ ] Current and planned behavior remain clearly separated.
- [ ] Relevant CLI, architecture, development, and limitation docs are updated.
- [ ] No unrelated generated files, secrets, credentials, or local configuration are included.
- [ ] The pull request identifies any remaining unverified claim or follow-up work.

## Current project boundary

Version `0.1.0` provides the core Python package, the complete stage-command
runtime through independent bundle verification, transactional workspace
revision schema 3, deterministic construction, curation, leakage-safe splits,
product rows, and exact 17-gate validation. Groups 1 through 3 are complete.
Group 4 must add `PipelineService`, make the CLI a thin adapter, and prove
dual-objective M1.1 API and CLI parity. Additional ingest formats, YAML, MCP,
the versioned Aptus handoff, the SwiftUI application, and public release gates
remain planned.

Follow the numbered sequence and exit gates in the [build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md).
