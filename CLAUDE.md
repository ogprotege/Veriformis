# CLAUDE.md

This file gives coding-agent guidance for the current Veriformis repository.

## Current state

Veriformis is a Python development alpha with implemented source code and tests.
Version `0.1.0` includes the M1 core, Group 1 integrity foundation, and Group 2
dataset-construction core. Read these current authorities before changing code:

1. `docs/product-contract.md`
2. `docs/current-status.md`
3. `docs/contracts/integrity-v1.md`
4. `docs/contracts/dataset-construction-v1.md`
5. `docs/architecture.md`
6. `docs/plans/2026-07-29-veriformis-roadmap.md`

Dated specifications and completed plans are historical records. Current status
and versioned contracts control present capability claims.

## Product doctrine

Veriformis owns the path from heterogeneous raw sources through faithful
canonical recovery, cleaning, objective-driven construction, curation, splits,
formatting, validation, and final seal. A cleaned corpus is an intermediate
compiler state unless a `full_text` recipe explicitly selects it as the target.

Non-negotiable rules:

1. Preserve raw-source identity and make extraction loss explicit.
2. Record every cleaning change in a source-scoped replayable plan.
3. Bind every constructed field to exact source-text or strict-IR evidence.
4. Keep v1 deterministic, local, and free of LLM or network generation.
5. Fail closed on unsupported input, malformed persisted state, stale state,
   identity mismatch, evidence mismatch, or replay mismatch.
6. Do not describe a construction result as a finished dataset. Group 3 still
   owns curation, splitting, construction-aware serialization, product rows,
   exact whole-dataset validation, atomic sealing, and verification.

There is no deterministic `summary` objective. Never label copied source text
as a summary or another transformation that did not occur.

## Current architecture

The installed `veriformis` CLI is the current composition root. The main flow
is `parse -> clean -> chunk -> construct`. A separate legacy M1 branch remains
`chunk -> format -> validate -> seal`; it does not consume accepted construction
records.

Key modules under `src/veriformis/` are:

- `parsers/`, `ir/`, `diagnostics.py`, and `evidence.py` for recovery and source truth;
- `rules/` for replayable cleaning;
- `chunkers/` for evidence-bearing segmentation;
- `construction/` for objectives, recipes, constructors, lifecycle, and replay;
- `serializers/`, `validate/`, and `bundle/` for the legacy M1 output branch;
- `workspace.py` for revisioned atomic state; and
- `cli.py` for command orchestration.

The physical workspace layout schema is 1. Current revision schema is 2.
`upgrade-workspace` performs the only supported revision-v1 to revision-v2
migration. Construct commits store `recipe` and `result` and must pass semantic
replay before `HEAD` advances.

## Commands and checks

Use Python 3.11 or newer, `uv`, Pydantic v2, Typer, pytest, and the pinned Ruff
version.

```bash
uv sync --extra test
uv lock --check
uv run ruff check src tests
uv run pytest -q
git diff --check
```

Run focused tests while developing, then run the complete checks before handoff.
Construction tests live under `tests/construction/`. Workspace, identity,
evidence, migration, and atomicity regressions live under `tests/regressions/`.

## Engineering constraints

- Use strict versioned persisted schemas and recompute durable identities on load.
- Preserve exact Unicode strings except where a locator contract explicitly defines NFC equivalence.
- Keep source scope sorted, unique, non-empty, and exact.
- Preserve accepted candidate fields and lineage unchanged in `DatasetRecord`.
- Treat review as recipe state. Do not require it for every recipe.
- Keep `curation_policy` and `split_policy` deferred until Group 3 implements them.
- Do not make serializers invent objectives, targets, review facts, or split facts.
- Use workspace transactions for persisted stage output. Do not mutate content-addressed objects.
- Add positive, negative, multi-source, Unicode, malformed, tamper, replay, and interruption tests in proportion to the change.
- Preserve Python 3.11 compatibility.
- Keep confidential implementation lineage unnamed.

When documentation and code disagree, verify the current implementation and
tests, then update active documentation in the same change. Do not rewrite
historical dated records except when their explicit status section is active.
