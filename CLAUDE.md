# CLAUDE.md

This file gives coding-agent guidance for the current Veriformis repository.

## Current state

Veriformis is a Python development **alpha** with implemented source code and
tests. Version `0.1.0` on `main` includes: M1 core; Groups 1–7; Group 9
automated release gates; beta-prep docs; private beta Mac workbench Phases 0–2
(thin SwiftUI over CLI); and independent-product Phases 0–3, including the
implemented taxonomy contract and discovery surfaces. Phase 4 verified export
foundation is in progress. Its opening slice introduces the typed internal
`ExportService` composition boundary and a descriptor-anchored verified source
view. Strict verified-export v1 models and trusted-by-default source admission
with explicit lower trust are implemented. Plan construction, writers, public
export commands, generic export containers, and planned trainer-specific
profiles are not implemented. Do not claim public
beta or production readiness without the checklists in
`docs/beta-limitations.md` and `docs/release.md`.

Read these current authorities before changing code:

1. `docs/product-contract.md`
2. `docs/current-status.md`
3. `docs/contracts/integrity-v1.md`
4. `docs/contracts/dataset-construction-v1.md`
5. `docs/contracts/finished-dataset-v1.md`
6. `docs/contracts/taxonomy-v1.md`
7. `docs/contracts/verified-export-v1.md`
8. `docs/architecture.md`
9. `docs/analysis/2026-08-11-independent-product-analysis.md`
10. `docs/plans/2026-08-11-veriformis-independent-product-roadmap.md`
11. `docs/governance/project-tracking.md`,
   `dev/active/independent-product/program.json`, and the current or most
   recently completed phase packet
12. `docs/governance/support-registry.json` and `docs/evidence/index.json`
13. `docs/contracts/aptus-handoff-v1.md` (optional Aptus integration)
14. `docs/plans/2026-07-29-veriformis-roadmap.md` and
    `docs/plans/2026-08-06-private-beta-workbench.md` (historical evidence)
15. `docs/install.md`, `docs/beta-limitations.md`, `docs/release.md`

Dated specifications and completed plans are historical records. Current status
and versioned contracts control present capability claims.

Then use `WIP.md` as the reviewed work queue. It never overrides current
status, the roadmap, or a versioned contract.

## Product doctrine

Veriformis owns the path from heterogeneous raw sources through faithful
canonical recovery, cleaning, objective-driven construction, curation, splits,
formatting, validation, and final seal. A cleaned corpus is an intermediate
compiler state unless a `full_text` recipe explicitly selects it as the target.
It must install, compile, verify, export, and release independently of Aptus or
any other trainer. Consumer profiles are optional adapters over verified
datasets.

Non-negotiable rules:

1. Preserve raw-source identity and make extraction loss explicit.
2. Record every cleaning change in a source-scoped replayable plan.
3. Bind every constructed field to exact source-text or strict-IR evidence.
4. Keep v1 deterministic, local, and free of LLM or network generation.
5. Fail closed on unsupported input, malformed persisted state, stale state,
   identity mismatch, evidence mismatch, or replay mismatch.
6. Do not describe a construction result as a finished dataset. A finished
   dataset must pass curation, splitting, construction-aware row lowering,
   exact whole-dataset validation, atomic sealing, and verification.

There is no deterministic `summary` objective. Never label copied source text
as a summary or another transformation that did not occur.

## Current architecture

The typed composition root is `veriformis.pipeline.PipelineService`. The
installed `veriformis` CLI is a thin Typer adapter over that service. The main
flow is `parse -> clean -> chunk -> construct -> curate -> split -> format ->
validate -> seal -> verify`.

Key modules under `src/veriformis/` are:

- `parsers/`, `ir/`, `diagnostics.py`, and `evidence.py` for recovery and source truth;
- `rules/` for replayable cleaning;
- `chunkers/` for evidence-bearing segmentation;
- `construction/` for objectives, recipes, constructors, lifecycle, and replay;
- `datasets/` for curation, leakage-safe splitting, product rows, and exact
  dataset validation;
- `taxonomy.py` for the versioned registry, compatibility policy, and read-only
  discovery catalog;
- `bundle/` for atomic finished-bundle publication and independent verification;
- `pipeline/` for surface-neutral stage orchestration (`PipelineService`);
- `recipes/` for named recipe builders, statistics, and YAML pipeline specs;
- `mcp/` for the constrained local MCP adapter;
- `handoff/` for the versioned Aptus handoff descriptor and consumer check;
- `serializers/` and `validate/` for retained M1 compatibility utilities;
- `workspace.py` for revisioned atomic state; and
- `cli.py` for the Typer adapter; and
- `macos/` for the SwiftUI workbench (thin CLI adapter; same digests as terminal).

The physical workspace layout schema is 1. Current revision schema is 3.
`upgrade-workspace` migrates verified revision-v1 workspaces through v2 and
then v3. Revision v3 adds `curate` and `split` and binds the complete stage
graph through `seal`. Every stage commit must pass semantic replay before
`HEAD` advances.

## Commands and checks

Use Python 3.11 or newer, `uv`, Pydantic v2, Typer, pytest, and the pinned Ruff
version.

```bash
uv sync --extra test
uv lock --check
uv run ruff check src tests
uv run python scripts/check_project_tracking.py
uv run pytest -q
git diff --check
```

Run focused tests while developing, then run the complete checks before handoff.
Construction tests live under `tests/construction/`. Finished-dataset and
bundle tests live under `tests/datasets/` and `tests/bundle/`. Workspace,
identity, evidence, migration, and atomicity regressions live under
`tests/regressions/`.

## Engineering constraints

- Use strict versioned persisted schemas and recompute durable identities on load.
- Preserve exact Unicode strings except where a locator contract explicitly defines NFC equivalence.
- Keep source scope sorted, unique, non-empty, and exact.
- Preserve accepted candidate fields and lineage unchanged in `DatasetRecord`.
- Treat review as recipe state. Do not require it for every recipe.
- Keep finished plans, curation decisions, split assignments, rows, validation,
  and seals bound to one exact source scope and `plan_id`.
- Do not make serializers invent objectives, targets, review facts, or split
  facts.
- Use workspace transactions for persisted stage output. Do not mutate content-addressed objects.
- Add positive, negative, multi-source, Unicode, malformed, tamper, replay, and interruption tests in proportion to the change.
- Preserve Python 3.11 compatibility.
- Keep confidential implementation lineage unnamed.

When documentation and code disagree, verify the current implementation and
tests, then update active documentation in the same change. Do not rewrite
historical dated records except when their explicit status section is active.
