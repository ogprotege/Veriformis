# Veriformis Work in Progress

**Status:** Active, non-authoritative working inventory

**Implementation baseline reviewed:** `fc33c56` on `main` after PR #16
(Groups 1–7, Group 9 automated gates PRs #14/#15, beta-prep docs/evidence PR #16)

**Product version:** `0.1.0` development alpha (not beta-labeled)

**Last reviewed:** 2026-08-06 (full docs/WIP sync to post–Group 9 + beta-prep main)

**Next review:** Deliberate beta label cut, public-ready Mac evidence, optional
Group 8 plan, or any listed-item status change

> **Authority:** This file is a convenience tracker. It does not define product
> truth. [Current implementation status](docs/current-status.md) controls
> present capability claims. The
> [build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md) controls work
> order and exit gates. The applicable versioned contract controls guarantees
> within its scope. If this file conflicts with those sources, the canonical
> source controls. Test totals and verification results are dated snapshots.

## Product target

Veriformis owns the difficult path from heterogeneous raw source material to a
finished, integrity-bearing training dataset:

```text
raw source capture
  -> canonical recovery -> cleaning -> chunking -> construction
  -> curation -> leakage-safe splitting -> product rows
  -> exact validation -> atomic seal -> independent verification
```

Canonical IR and cleaned text are accountable intermediate states. A
`full_text` recipe may select cleaned text as exact target content. It becomes
a finished dataset only after construction, curation, splitting, formatting,
validation, sealing, and verification. The deterministic pipeline remains
local, offline, and free of LLM generation.

## Current boundary

- [x] M1 core is implemented.
- [x] Groups 1 through 7 are implemented.
- [x] Steps 1 through 24 are complete.
- [ ] Step 25 remains (optional Group 8).
- [x] Group 4 / M1.1 service surface is complete.
- [x] Group 5 ingest and recipe expansion is complete.
- [x] Group 6 MCP and Aptus handoff is complete.
- [x] Group 7 SwiftUI workbench is complete.
- [x] Group 9 automated gates: CI matrix, lock check, install smoke, golden compile, release docs/scripts (on `main`).
- [x] Beta-prep: [docs/beta-limitations.md](docs/beta-limitations.md), clean-path evidence recorder + pack.
- [ ] Private beta workbench plan:
      [docs/plans/2026-08-06-private-beta-workbench.md](docs/plans/2026-08-06-private-beta-workbench.md)
      (Phase 0 dogfood → Phase 1 shell → …).
- [ ] Deliberate beta **label** cut (still alpha until then).
- [ ] Group 9 owner remainder: signed/notarized Mac (blocks **public** Mac app claim).
- [ ] Group 8 optional (owner-gated).

The current stage-command runtime is:

```text
parse -> clean -> chunk -> construct -> curate -> split
      -> format -> validate -> seal -> verify
```

## Completed and verified

### Group 1: Integrity foundation

**Status:** Complete

- [x] 1. Product and acceptance contract
- [x] 2. Regression tests
- [x] 3. Transactional workspace
- [x] 4. Source-scoped identities
- [x] 5. IR, diagnostics, and source evidence
- [x] 6. Replayable cleaning plans

**Delivered:** Immutable workspace revisions, atomic commits, stale-stage
invalidation, deterministic identities, explicit parser loss, source-grounded
evidence, and one cleaning plan shared by preview and application.

**Evidence:** [Integrity Contract v1](docs/contracts/integrity-v1.md),
[current status](docs/current-status.md), and the
[Group 1 architecture review](dev/active/group-1-integrity-foundation/architecture-review.md).

### Group 2: Dataset construction core

**Status:** Complete

- [x] 7. Training objectives and recipes
- [x] 8. Construction passes and evidence
- [x] 9. Record lifecycle
- [x] 10. Deterministic constructors

**Delivered:** Five deterministic objectives, versioned recipes, ordered
passes, field-level evidence, auditable decisions, immutable accepted records,
and exact construction replay.

**Evidence:**
[Dataset Construction Contract v1](docs/contracts/dataset-construction-v1.md),
the [Group 2 plan](dev/active/group-2-dataset-construction/plan.md), and the
[Group 2 code review](dev/active/group-2-dataset-construction/group-2-dataset-construction-code-review.md).

### Group 3: Finished-dataset pipeline

**Status:** Complete

- [x] 11. Curation and quality
- [x] 12. Leakage-safe splitting
- [x] 13. Construction and serialization separation
- [x] 14. Contract product rows
- [x] 15. Exact dataset validation
- [x] 16. Atomic sealing and verification

**Delivered:** Deterministic curation, explicit coverage, transitive leakage
groups, authoritative train and evaluation assignments, four product row
schemas, aligned provenance, 17 validation gates, atomic six-file bundles, and
independent verification.

**Evidence:** [Finished Dataset Contract v1](docs/contracts/finished-dataset-v1.md),
the [Group 3 plan](dev/active/group-3-finished-dataset/plan.md), and the
[Group 3 code review](dev/active/group-3-finished-dataset/group-3-finished-dataset-code-review.md).

## Completed: Group 4

### Group 4: M1.1 completion

**Status:** Complete

- [x] 17. Pipeline service
- [x] 18. Thin CLI adapter
- [x] 19. Dual-objective M1.1 acceptance

**Delivered:** `veriformis.pipeline.PipelineService` owns stage orchestration;
`cli.py` is a thin Typer adapter; dual-objective acceptance proves API/CLI
parity for `full_text` and `continuation` on the golden multi-source corpus.

**Evidence:** [Group 4 plan](dev/active/group-4-pipeline-service/plan.md),
`tests/pipeline/test_pipeline_service.py`.

## Completed: Group 5

### Group 5: Input and recipe expansion

**Status:** Complete

- [x] 20. Full declared ingest
- [x] 21. Expanded deterministic recipe library

**Delivered:** HTML/PDF/CSV/JSON/JSONL parsers with explicit loss diagnostics,
named OCR refusal, five named recipe builders, deterministic statistics, and
`veriformis.pipeline/v1` YAML execution through `PipelineService`.

**Evidence:** [Group 5 plan](dev/active/group-5-input-recipe-expansion/plan.md),
`tests/parsers/test_group5_formats.py`,
`tests/recipes/test_recipe_library_and_pipeline.py`, and permanent
`tests/regressions/test_group5_declared_format_pipeline.py` (solo/mixed
seal+verify, CLI, OCR refusal, YAML, construction replay).

## Completed: Group 6

### Group 6: Integrations

**Status:** Complete

- [x] 22. MCP automation
- [x] 23. Versioned Aptus handoff

**Delivered:** local MCP adapter over PipelineService; sibling Aptus handoff
v1; CLI `mcp` / `handoff` / `handoff-verify`; consumer verification of
external digest, partitions, rows, and assignment projection.

**Evidence:** `tests/mcp/`, `tests/handoff/`,
`docs/contracts/aptus-handoff-v1.md`.

## Completed: Group 7

### Group 7: macOS product

**Status:** Complete

- [x] 24. SwiftUI dataset workbench

**Delivered:** `macos/` SwiftUI app shells to `veriformis` CLI; drag-drop sources;
stage log; sealed bundle + handoff reveal; `parity_check.sh` digest lock.

## Next work: private beta workbench / Group 9 owner / optional Group 8

### Private beta Mac workbench (owner plan)

Authority:
[docs/plans/2026-08-06-private-beta-workbench.md](docs/plans/2026-08-06-private-beta-workbench.md)

- [x] Phase 0 — Dogfood current workbench; punch list of UX/debug pain
      ([phase-0-dogfood.md](dev/active/private-beta-workbench/phase-0-dogfood.md))
- [ ] Phase 1 — KISS shell: Home / Compile / History / Settings + run sheet
- [ ] Phase 2 — Debugger power (digests, reveal, failure stage)
- [ ] Phase 3 — Optional post-seal export (only formats we implement)
- [ ] Phase 4 — Heavy post-processors if still needed (never replace seal)

### Group 8: Advanced construction (optional)

- [ ] 25. Governed model-assisted construction (owner-approved plan required)

### Group 9: Public release

- [x] 26a. Automated gates — CI matrix (3.11–3.13 + macOS 3.12), `uv lock --check`,
  wheel install smoke, golden corpus seal/verify/handoff-verify, `scripts/release/`,
  [docs/release.md](docs/release.md), permanent regression
  `tests/regressions/test_group9_release_gates.py`
- [x] 26a+. Beta limitations register + clean-path evidence pack (CLI beta prep; not a label cut)
- [ ] 26b. Owner Mac distribution — Developer ID sign, notarize, staple, clean-Mac
  install, golden + Aptus evidence (see release checklist) — **public** Mac claim

**Evidence for Group 7:** [`macos/README.md`](macos/README.md),
`macos/scripts/parity_check.sh`, and Xcode unit tests under `macos/Tests/`.

**Evidence for Group 9 automated:** [docs/release.md](docs/release.md),
`.github/workflows/ci.yml`, `scripts/release/`, main CI green after PR #15.

**Beta prep:** [docs/beta-limitations.md](docs/beta-limitations.md),
[beta readiness audit](dev/active/group-9-public-release/beta-readiness-audit.md),
[evidence packs](dev/active/group-9-public-release/evidence/).

## Optional work requiring owner approval

### Group 8: Advanced construction

- [ ] 25. Governed model-assisted construction
  - Add an optional `GeneratorPass` for source-grounded QA, dialogue,
    classification, and transformation candidates.
  - Add complete generation lineage and policy gates.

This step requires a separate owner-approved plan. It is not part of
deterministic v1 and does not block Group 9. If approved, every generated
candidate must retain model, prompt, parameters, source evidence, output,
quality, and review lineage. It must pass through the existing finished-dataset
contracts.

**Exit gate:** Generated candidates retain model, prompt, parameter,
source-evidence, output, quality, and review lineage. They pass through the same
curation, split, validation, and sealing contracts as deterministic candidates.

## Final required work

### Group 9: Public release

- [x] 26a. Automated public-release gates (CI, install smoke, golden path, docs)
  - Supported-platform CI matrix and lockfile check.
  - Package installation smoke and golden corpus compile evidence scripts.
  - Migration verification remains in the ordinary regression suite.
  - Release runbook documents owner signing/notarization (no silent skip).
- [x] 26a+. Beta-prep on `main` (PR #16) — limitations register, clean-path
  evidence pack, alpha honesty (not a beta label cut).
- [ ] 26b. Owner-executed public-ready evidence
  - macOS packaging with Developer ID signing, notarization, and staple.
  - Clean supported Mac install of the signed product.
  - Golden raw corpus compile + verify + Aptus-compatible handoff with retained logs.

**Exit gate (public):** A clean supported Mac can install the signed and
notarized product, compile the golden raw corpus, verify the final bundles, and
hand them to a compatible Aptus release with independently recorded evidence.

**CLI beta (future label cut):** See [docs/beta-limitations.md](docs/beta-limitations.md)
and the [beta readiness audit](dev/active/group-9-public-release/beta-readiness-audit.md).

## Execution order and dependencies

- Complete required Groups 1 through 7 in order.
- Do not start a later required group before the earlier exit gate passes.
- Add tests and documentation within every group.
- Preserve deterministic and offline dataset compilation through Group 7.
- When Step 25 is deferred, proceed from Group 7 directly to Group 9.
- When Step 25 is approved, proceed from Group 7 through Group 8 to Group 9.
- Do not let Step 25 weaken deterministic compilation or provenance guarantees.
- Track build, publication, installation, signing, notarization, and downstream
  compatibility as separate release states.

## Nonblocking follow-up debt

The Group 1 review recorded two Important architecture deferrals. They do not
reopen the Group 1 gate, but their stated trigger conditions still apply.

- [ ] Bound memory use and deduplicate integrity work before advertising
  large-corpus support.
- [ ] Make parser, rule, and chunker replay version-addressable before changing
  persisted producer behavior.

The Group 3 review recorded three minor maintenance items. They do not reopen
the Group 3 gate.

- [ ] Deeply freeze or strongly type nested `ProductRow.payload` values.
- [ ] Consolidate duplicate closed-contract registries where typing permits.
- [ ] Split `WorkspaceTransaction._validate_stage_semantics` into private
  per-stage validators.

Additional product follow-ups remain unassigned within the numbered roadmap:

- [ ] Add CLI ingestion for completed `ReviewEvidence`. Today,
  `--require-review` leaves candidates pending.
- [ ] Define a retention profile for portable bundles that embed replay
  material. Closed-bundle verification remains workspace-independent, while
  full source replay remains available through workspace history.

## Documentation status

Architecture deep-dive, Groups 1–7 docs sync, Group 9 release guide, and beta
limitations are on `main` (through PRs #6 lineage, #13–#16).

Remaining documentation debt:

- [ ] Re-verify architecture deep-dive `file:line` citations when entry points
  drift materially.
- [ ] Machine-render Mermaid diagrams in CI (currently hand-reviewed).
- [x] Group 9 automated: packaging runbook + release troubleshooting
  (`docs/release.md`).
- [x] Beta limitations register + clean-path evidence docs (PR #16).
- [ ] Group 9 owner: notarization evidence and security hardening follow-ups
  when claiming a public Mac app.

## Deferred documentation

- [x] Add the stable Python API surface via `PipelineService`.
- [x] Add the dual-objective M1.1 API and CLI acceptance procedure.
- [x] Add the versioned Aptus handoff contract and consumer verification.
- [x] Document expanded declared ingest and YAML pipelines.
- [x] Document MCP and SwiftUI workbench surfaces.
- [x] Release guide and troubleshooting entry points for Group 9 automated gates.
- [x] Beta limitations and clean-path evidence documentation (PR #16).
- [ ] Expand security hardening and owner notarization evidence as needed.

## Known current limitations

- OCR is unsupported (empty-text PDFs refuse with a named limitation).
- Declared inputs are text, Markdown, DOCX, HTML, digitally-born PDF, CSV,
  JSON, JSONL, and listed source-code formats — not arbitrary binary.
- Current Aptus MLX intake rejects plain `text` rows (recorded in handoff
  capabilities).
- The CLI cannot submit completed human review evidence.
- The minimal bundle omits raw sources and complete replay artifacts.
- External trust requires a manifest digest retained outside the bundle.
- Model-assisted construction remains optional and unapproved (Group 8).
- Automated CI/packaging gates land; public readiness still needs owner Mac evidence.

## Verification snapshot

Post–Group 9 + beta-prep on `main` (`fc33c56`, 2026-08-06):

```text
uv lock --check
uv run ruff check src tests
uv run pytest -q            # 658 passed locally at Group 9 land; re-run for current total
bash scripts/release/smoke_install.sh
bash scripts/release/golden_compile.sh
git diff --check
```

CI on `main` (after PR #15/#16): Python 3.11–3.13 Ubuntu + 3.12 macOS, Ruff,
pytest, install-smoke, golden-compile.

Additional permanent locks: Group 5 declared-format e2e, MCP/service parity,
Aptus handoff consumer tests, Group 9 release-gate regressions,
`macos/scripts/parity_check.sh`, and clean-path pack under
`dev/active/group-9-public-release/evidence/`.

Rerun these checks before calling this snapshot current.

## Maintenance rules

1. Check an item only after its implementation and exit gate merge to `main`.
2. Update this file in the same change that alters a listed status.
3. Keep completed items visible. They preserve execution history.
4. Do not duplicate contract details that belong in a versioned contract.
5. Keep Group 8 separate until the owner approves its implementation plan.
6. Keep maturity as alpha until a deliberate beta label cut; complete Group 9
   owner Mac evidence only for a public Mac app claim. Group 8 remains optional.
7. Preserve deterministic and offline operation through Group 7.
8. Keep the retained manifest digest and integrity-controlled publication
   parent requirements visible in every future sealing surface.

## Canonical references

- [Current implementation status](docs/current-status.md)
- [Authoritative build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md)
- [Product contract](docs/product-contract.md)
- [Integrity Contract v1](docs/contracts/integrity-v1.md)
- [Dataset Construction Contract v1](docs/contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](docs/contracts/finished-dataset-v1.md)
- [Aptus Handoff Contract v1](docs/contracts/aptus-handoff-v1.md)
- [Architecture](docs/architecture.md)
- [Architecture tree](docs/architecture/README.md)
- [CLI reference](docs/cli.md)
- [Development guide](docs/development.md)
- [Release guide](docs/release.md)
- [Beta limitations](docs/beta-limitations.md)
- [Private beta workbench vision](docs/plans/2026-08-06-private-beta-workbench.md)
- [Beta readiness audit](dev/active/group-9-public-release/beta-readiness-audit.md)
- [macOS workbench](macos/README.md)
