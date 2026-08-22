# CLAUDE.md

This file gives coding-agent guidance for the current Veriformis repository.

## Current state

Veriformis is a Python development **alpha** with implemented source code and
tests. Version `0.1.0` on `main` includes: M1 core; Groups 1–7; Group 9
automated release gates; beta-prep docs; private beta Mac workbench Phases 0–2
(thin SwiftUI over CLI); independent-product Phases 0–4; and Phase 5.1–5.4's
supported generic `split-jsonl-directory`, canonical `json`, and
`constrained-csv` v1 exports plus receipt-anchored export-pack transport.
Phase 5.4 merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`. Phase 5.5's consolidated
semantic round-trip matrix merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1`. Phase 5.6's exact dry-run preview
merged as PR #58 at `cd017941090c7352cb1d10f9a383042b954d4f2e` after
all 14 GitHub checks passed. Phase 5.7's operator guide and Phase 5 closeout
merged as PR #59 at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b` after all 14
GitHub checks passed. Phase 6 (goal-first recipes and previews) is in progress
under its standard packet. Item 6.1's plain-language goal catalog merged as
PR #60 at `7316d94faf2d6c23b7abb6fe200f154da47d398c` after all 14 GitHub
checks passed; item 6.2 adds per-goal contracts and the seventh taxonomy axis
`input_family`.
Phase 4 introduces the
implemented taxonomy contract/discovery surfaces and the typed internal
`ExportService` composition boundary and a descriptor-anchored verified source
view. Strict verified-export v1 models and trusted-by-default source admission
with explicit lower trust are implemented. Read-only plan population now
derives all source identities and the source membership baseline from that
immutable view; callers provide only strict profile, dependency, and file-plan
evidence. Read-only derivative enforcement fresh-reconstructs normalized
candidate semantic rows, provenance, row-set identity, and membership and
requires exact plan-baseline equality. Phase 4's private, initially empty
implementation catalog backs strict discovery, dry
run, self-described inspect, operator-confirmed no-replace execute, and source-
bound verify operations through `PipelineService`, CLI, MCP, and the CLI-backed
Mac bridge. Phase 4.8 merged as PR #50 at
`fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`, with review corrections in PR #51
at `d91542fe12c5a492de578ad060836a7d65999e42`; Phase 4.9 completes the
adversarial harness and closeout reconciliation.
Private render/replay hooks are trusted code, not a plugin boundary, and
semantic replay currently retains each complete produced file in memory.
Phase 5.1–5.3 install three production exact-byte renderers and discoverable
physical containers: `split-jsonl-directory`, canonical `json`, and
`constrained-csv` v1.
Request v1 selects split JSONL's safe `train` / `evaluation` names and aligned
provenance, canonical JSON's fixed dataset/provenance tree, or constrained
CSV's fixed quoted-CSV tree. Request
v2 applies only to split JSONL and requires the complete
`veriformis.split-jsonl-options/v1` object for custom safe stems or
provenance-off; `json` and `constrained-csv` v1 refuse configured requests.
Constrained CSV admits only the flat `text`, `prompt_completion`, and
`instruction_output` row schemas; `messages` must use split JSONL or canonical
JSON. All three derivatives preserve rows, ordering, and authoritative
partition membership and claim
compatibility with no trainer. No production semantic replayer or trainer-
specific profile is shipped. Phase 5.4 adds no fourth renderer or request
schema: `deterministic-export-pack-zip-v1` uses the existing
`package` / `package-verify` family to wrap one unchanged export directory as
`.vfexport.zip` under a separately retained canonical receipt digest. It
preserves the embedded source trust grade, is not source-bound export
verification, and adds no MCP or Mac UI operation. Phase 5.5 adds only a
frozen, discovery-closed test fixture that strictly reloads ordinary emitted
files for all 11 compatible container/schema pairs, proves the sole nested-CSV
refusal, and exercises semantic tampering. It adds no production importer,
replayer, request, schema, taxonomy, or support claim. Phase 5.6 adds a
runtime-only dry-run response v2: the unchanged plan, exact ordinal-zero
samples for non-empty train/evaluation partitions, and a normalized plan-
derived destination tree plus `export-receipt.json`. Payloads over 64 KiB or
unable to fit the response budget are omitted whole with an exact reason;
ASCII-safe transport preserves decoded values. Preview must not call a
renderer or access a destination, and it changes no persisted model, request,
discovery, selector, taxonomy, support, consumer, or trainer claim. Do not
claim public beta or production readiness without the checklists in
`docs/beta-limitations.md` and `docs/release.md`.

Read these current authorities before changing code:

1. `docs/product-contract.md`
2. `docs/current-status.md`
3. `docs/contracts/integrity-v1.md`
4. `docs/contracts/dataset-construction-v1.md`
5. `docs/contracts/finished-dataset-v1.md`
6. `docs/contracts/taxonomy-v1.md`
7. `docs/contracts/bundle-transport-v1.md`
8. `docs/contracts/verified-export-v1.md`
9. `docs/contracts/split-jsonl-export-v1.md`
10. `docs/contracts/canonical-json-export-v1.md`
11. `docs/contracts/constrained-csv-export-v1.md` and
    `docs/contracts/goal-catalog-v1.md`
12. `docs/adr/0006-receipt-anchored-export-pack-transport.md`,
    `docs/adr/0007-goal-first-catalog-as-versioned-data.md`, and
    `docs/adr/0008-input-family-taxonomy-axis.md`
13. `docs/generic-exports.md`
14. `docs/architecture.md`
15. `docs/analysis/2026-08-11-independent-product-analysis.md`
16. `docs/plans/2026-08-11-veriformis-independent-product-roadmap.md`
17. `docs/governance/project-tracking.md`,
   `dev/active/independent-product/program.json`, and the current or most
   recently completed phase packet
18. `docs/governance/support-registry.json` and `docs/evidence/index.json`
19. `docs/contracts/aptus-handoff-v1.md` (optional Aptus integration)
20. `docs/plans/2026-07-29-veriformis-roadmap.md` and
    `docs/plans/2026-08-06-private-beta-workbench.md` (historical evidence)
21. `docs/install.md`, `docs/beta-limitations.md`, `docs/release.md`

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
- `exports/` for verified derivatives and receipt-anchored export-pack
  transport, with `_archive_transport.py` holding the deterministic ZIP codec
  shared with bundle transport;
- `pipeline/` for surface-neutral stage orchestration (`PipelineService`);
- `recipes/` for named recipe builders, statistics, and YAML pipeline specs;
- `goals/` for the packaged versioned goal catalog and its strict models that
  resolve plain-language goals to existing objectives and row schemas;
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
