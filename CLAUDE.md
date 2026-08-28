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
GitHub checks passed. Phase 6 (goal-first recipes and previews) is complete
under its standard packet. Item 6.1's plain-language goal catalog merged as
PR #60 at `7316d94faf2d6c23b7abb6fe200f154da47d398c` after all 14 GitHub
checks passed; item 6.2's per-goal contracts and seventh taxonomy axis
`input_family` merged as PR #61 at
`81becfa676fd9111868b8d4b62549218a644d3e2`; item 6.3's runtime-only goal
preview merged as PR #62 at `9cbab117e47cde6bd8850d67f0d363e03f0660ce`; item
6.4's versioned recipe presets and goal-first compile surfaces merged as PR #63
at `abdd630e25e83ebf346316319caec892f4d64886` after all 14 GitHub checks
passed. Item 6.5's compile preflight over raw sources merged as PR #64 at
`b2e28b3dcfe48cd28ec74d8d8eaed12049f72d2d` after all 14 checks passed.
Item 6.6's frozen goal acceptance matrix merged as PR #65 at
`7b93a32a5a9b18e5bc9c032750f467c4d9c43ea5` after all 14 checks passed.
Item 6.7's instruction templates, truthfulness check, U1–U6 judgment, and
Phase 6 closeout merged as PR #67 at
`6995d17bef0d09f235b1c464e947c38c63dd313d` after all 14 GitHub checks
passed, then stamped complete as PR #69 at
`6c4694c2e1c523156cd7c8f34c12f258a3ce0b01`. Phase 7 (existing-dataset import
and mapping) is complete under its standard packet. Items 7.1–7.10 merged as
PR #71 through PR #80. Closeout merged as PR #80 at
`b7bb7f0c2046fba87fd7c9da12f7d2ccb5c2c88f` after all 14 GitHub checks
passed. Dataset-row compilation is opt-in: `parse --mode dataset-row` then
`map` on revision v4, with confirmed mapping plans, `mapped_value` evidence,
JSON/CSV/JSONL capture, rejection reports, and packaged templates. Phase 8
(first consumer profiles) is complete under its standard packet. Items 8.1–8.6
merged as PR #82 through PR #87. Item 8.7 promotes `trl` and `mlx-lm` to
implemented optional adapters, names accepted/transformed/rejected goals and
rows, and closes the phase. The exporter does not train. Phase 9 (columnar
and Hugging Face dataset containers) is complete under its standard
packet. Items 9.1–9.8 merge sequentially. Item 9.8 loads the three
containers through PyArrow and Hugging Face Datasets in optional CI,
measures JSONL versus columnar tree sizes, promotes `parquet`, `arrow`,
and `hugging-face-dataset` to implemented, and closes the phase. Extra
`columnar` stays empty. Phase 10 (expand consumer profiles under
evidence gates) is complete under its standard packet. Items 10.1–10.2
opened the packet and pinned admissions as PR #97 and PR #98. Items
10.3–10.8 emit Axolotl and LLaMA-Factory, skip Unsloth, move Aptus onto
`ExportService`, add official-schema harnesses, and close the phase.
Empty extras stay empty. The exporter does not train.
Phase 11 collection ingest is complete: shared collection plan v1;
archives, parser subprocesses, and new input families skipped. Phase 12 optional local OCR is complete: Tesseract 5 under ADR-0016;
digital / OCR / merged recovery; confidence thresholds; `ocr-preview`;
empty extra `ocr`. Closeout merged as PR #112 at
`892939f527974b69282296ded04eb3b43643554f`. Default parse still refuses
image-only PDF. `ocr-image` remains explicitly unsupported.
Phase 13 quality intelligence is complete: versioned quality report,
previewable gates, labeled fixtures. Closeout merged as PR #122 at
`ef31559c9184b553209a3c45eca5d943fbb9a680`. No heuristic blocks seal.
There is no quality-report command.
Phase 14 review workflows are complete: queues, corrections as new
identities, named-seed sampling, CLI/MCP/Python packet exchange,
required-review seal blocking, and auditable supersession. Default
recipes stay `none`. Mac Review belongs to Phase 18. Do not start
Phase 15 from that packet.
Phase 15 scale work is complete. Named-hardware reports exist.
`scale-support` discovery publishes an empty tier list. 15.5–15.8 were
skipped with a record. Sequential PRs 15.1–15.9. Phase 16 extension
architecture is complete. Sequential PRs 16.1–16.10. ADR-0017 Decision
A: no untrusted loader. Public plugins skipped with a record.
Phase 17 advanced dataset families is in progress under its own packet.
Item 17.1 is honesty only. Do not start Phase 18 from that packet.
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
11. `docs/contracts/constrained-csv-export-v1.md`,
    `docs/contracts/goal-catalog-v1.md`,
    `docs/contracts/recipe-preset-v1.md`,
    `docs/contracts/row-mapping-v1.md`,
    `docs/contracts/profile-admission-v1.md`,
    `docs/contracts/columnar-schema-v1.md`,
    `docs/contracts/columnar-fingerprint-v1.md`,
    `docs/contracts/parquet-export-v1.md`,
    `docs/contracts/trl-export-v1.md`,
    `docs/contracts/mlx-lm-export-v1.md`,
    `docs/contracts/axolotl-export-v1.md`,
    `docs/contracts/llama-factory-export-v1.md`,
    `docs/contracts/aptus-export-v1.md`,
    `docs/contracts/collection-plan-v1.md`,
    `docs/contracts/parser-identity-v1.md`,
    `docs/contracts/ocr-recovery-identity-v1.md`,
    `docs/contracts/quality-report-v1.md`,
    `docs/contracts/review-v1.md`,
    `docs/contracts/scale-corpus-v1.md`,
    `docs/contracts/scale-baseline-v1.md`,
    `docs/contracts/scale-support-v1.md`, and
    `docs/contracts/extension-protocol-v1.md`
12. `docs/adr/0006-receipt-anchored-export-pack-transport.md`,
    `docs/adr/0007-goal-first-catalog-as-versioned-data.md`,
    `docs/adr/0008-input-family-taxonomy-axis.md`, and
    `docs/adr/0010-input-mode-as-compiler-path.md`,
    `docs/adr/0011-imported-records-and-mapping-evidence.md`, and
    `docs/adr/0012-consumer-profile-as-optional-adapter.md`,
    `docs/adr/0013-columnar-containers-as-optional-generic-exports.md`, and
    `docs/adr/0014-independently-admitted-consumer-profiles.md`,
    `docs/adr/0015-collection-plan-as-ingest-contract.md`,
    `docs/adr/0016-optional-local-tesseract-ocr.md`, and
    `docs/adr/0017-no-untrusted-extension-loader.md`
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
- `goals/` for the packaged versioned goal catalog, recipe presets, goal
  preview, and compile preflight, whose strict models resolve plain-language
  goals and presets to existing objectives, row schemas, and executable recipe
  settings, and probe raw sources without workspace mutation;
- `profiles/` for implemented TRL, MLX-LM, Axolotl, LLaMA-Factory, and Aptus admission pins and adapters;
- `quality/` for the versioned quality report (facts, policy, recommendations; previewable gates; not enforcing);
- `review/` for the versioned review bundle (queue kinds, waiver, correction; 14.2 schema pin; does not block seal);
- `extensions/` for the internal extension protocol, built-in-only registry, and read-only capability declarations (no loader);
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
