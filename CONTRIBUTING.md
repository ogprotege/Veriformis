# Contributing to Veriformis

Veriformis is an alpha dataset compiler with strict source-fidelity and integrity goals. Contributions should improve the implemented product without overstating guarantees that the code does not yet provide.

## Start with the current contract

Before changing code, read:

- [Product contract](docs/product-contract.md)
- [Integrity Contract v1](docs/contracts/integrity-v1.md)
- [Dataset Construction Contract v1](docs/contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](docs/contracts/finished-dataset-v1.md)
- [Dataset Taxonomy Contract v1](docs/contracts/taxonomy-v1.md)
- [Verified Export Contract v1](docs/contracts/verified-export-v1.md)
- [Aptus Handoff Contract v1](docs/contracts/aptus-handoff-v1.md)
- [Current implementation status](docs/current-status.md)
- [Project tracking and evidence policy](docs/governance/project-tracking.md)
- [Active independent-product ledger](dev/active/independent-product/program.json)
- [Support registry](docs/governance/support-registry.json)
- [Install guide](docs/install.md)
- [Architecture](docs/architecture.md)
- [CLI reference](docs/cli.md)
- [Development guide](docs/development.md)
- [Release guide](docs/release.md)
- [Beta limitations](docs/beta-limitations.md)
- [macOS workbench](macos/README.md)
- [Independent product roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md)

The roadmap is ordered. Historical Groups 1–7, Group 9 automated gates,
beta-prep, and private beta workbench Phases 0–2 are implemented. Independent
product Phases 0–3 are complete. Phase 4, verified export foundation, is
`in_progress`; consult its
[active packet](dev/active/independent-product/phase-04-verified-export-foundation/README.md)
and the machine ledger before changing that boundary. The typed service,
verified source view, strict v1 model contracts, source-trust admission, and
read-only source-derived plan population do not yet authorize destination
rendering, generic export containers, or trainer-specific profiles. Maturity remains
development **alpha**. Do not describe the
product as public-ready without [docs/beta-limitations.md](docs/beta-limitations.md)
and [docs/release.md](docs/release.md).

After reading these authorities, consult [Work in progress](WIP.md) as the
non-authoritative reviewed work queue.

## Set up

```bash
uv sync --extra test
uv run ruff check src tests
uv run python scripts/check_project_tracking.py
uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"
```

Python 3.11 or newer is required. The test matrix runs Python 3.11, 3.12, and
3.13 on Ubuntu plus Python 3.12 on macOS. Separate Ubuntu jobs run install
smoke and golden compilation (see
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
- Preserve Python 3.11 compatibility; it is an explicit CI matrix cell.
- Do not add a dependency without checking its license, maintenance status, and necessity.

### Documentation

- Use present tense only for implemented, merged, tested behavior.
- Put planned behavior in a clearly labeled section and link the roadmap.
- Update command examples when CLI flags or defaults change.
- State known integrity and provenance limitations directly.
- Do not claim a gate, input format, interface, or bundle guarantee that is not exercised by code and tests.
- Update the active phase packet, program ledger, support registry, WIP,
  current status, and evidence records when tracked truth changes.

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
- [ ] `uv run python scripts/check_project_tracking.py` passes.
- [ ] `uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"` passes.
- [ ] Current and planned behavior remain clearly separated.
- [ ] Relevant CLI, architecture, development, and limitation docs are updated.
- [ ] No unrelated generated files, secrets, credentials, or local configuration are included.
- [ ] The pull request identifies any remaining unverified claim or follow-up work.

## Current project boundary

Version `0.1.0` provides the complete deterministic stage-command runtime
through independent bundle verification, `PipelineService`, transactional
workspace revision schema 3, five objectives, curation, leakage-safe splits,
four row schemas, exact 17-gate validation, expanded declared ingest, YAML,
local MCP, optional Aptus handoff, and the SwiftUI workbench. It remains a
development alpha. Follow the current state and exit gates in the
[independent product roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md),
[program ledger](dev/active/independent-product/program.json), and the current
phase packet when one is active. Generic export containers and new
trainer-specific profiles remain planned until their own roadmap gates pass;
this does not erase the existing canonical or optional Aptus profiles.
