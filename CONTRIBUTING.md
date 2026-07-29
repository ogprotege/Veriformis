# Contributing to Veriformis

Veriformis is an alpha dataset compiler with strict source-fidelity and integrity goals. Contributions should improve the implemented product without overstating guarantees that the code does not yet provide.

## Start with the current contract

Before changing code, read:

- [Product contract](docs/product-contract.md)
- [Current implementation status](docs/current-status.md)
- [Architecture](docs/architecture.md)
- [CLI reference](docs/cli.md)
- [Development guide](docs/development.md)
- [Build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md)

The roadmap is ordered. Do not implement a later group while an earlier exit gate remains incomplete unless the roadmap is revised through review.

## Set up

```bash
uv sync --extra test
uv run ruff check src tests
uv run pytest -q
```

Python 3.11 or newer is required. CI currently runs Python 3.12 on Ubuntu.

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
- Keep structured prompt and target boundaries when downstream masking depends on them.
- Treat human review as a recipe or policy state, not a universal prerequisite for dataset construction.
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

Version `0.1.0` provides the core Python package and stage-command CLI. Transactional workspace state, recipe-driven construction, full dataset validation, atomic sealing, additional ingest formats, MCP, downstream handoff, and the SwiftUI application are planned work.

Follow the numbered sequence and exit gates in the [build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md).
