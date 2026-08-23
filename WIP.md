# Veriformis Work in Progress

**Status:** Active, non-authoritative working inventory

**Implementation baseline reviewed:** `799d56f` on `main` after PR #82
(Groups 1–7; Group 9 automated gates; beta-prep; private beta workbench
Phases 0–2; independent-product Phases 0–7 complete; Phase 8.2 admission pins)

**Product version:** `0.1.0` development alpha (not beta-labeled)

**Last reviewed:** 2026-08-23 (independent-product Phase 8.2 admission pins)

**Next review:** Phase 8.2 pull-request merge, item 8.3, beta label cut, or
any listed-item status change. Do not start Phase 9, 10, or 13 from this
packet.

> **Authority:** This file is a convenience tracker. It does not define product
> truth. [Current implementation status](docs/current-status.md) controls
> present capability claims. The
> [independent product roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) controls future work
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
a finished dataset only after construction, curation, splitting, row lowering,
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
- [x] Beta-prep: [docs/beta-limitations.md](docs/beta-limitations.md), clean-path evidence, [docs/install.md](docs/install.md).
- [x] Private beta workbench plan Phases **0–2** on `main`
      ([historical plan](docs/plans/2026-08-06-private-beta-workbench.md): dogfood,
      KISS shell, and debugger power).
- [ ] Independent product roadmap Phases 0–20; machine state and next gates:
      [program.json](dev/active/independent-product/program.json).
- [x] Independent product Phase 4 is complete. Its closeout merged as PR #52
      at `a76e0fe3185b0e317cd453b9c28a1d2054e617dd`.
- [x] Independent product Phase 5 is complete under its
      [completed packet](dev/active/independent-product/phase-05-generic-local-exports/README.md).
      Item 5.6 merged as PR #58 at
      `cd017941090c7352cb1d10f9a383042b954d4f2e`; item 5.7's operator guide
      and phase closeout merged as PR #59 at
      `65cbd471e96d83f8dd65e2cda60e90f64a916e2b`.
- [x] Independent product Phase 6 is complete under its
      [completed packet](dev/active/independent-product/phase-06-goal-first-recipes/README.md).
      Item 6.1's plain-language goal catalog merged as PR #60 at
      `7316d94faf2d6c23b7abb6fe200f154da47d398c` and item 6.2's goal
      contracts and `input_family` axis merged as PR #61 at
      `81becfa676fd9111868b8d4b62549218a644d3e2`, each after all 14 GitHub
      checks passed; item 6.3's goal preview merged as PR #62 at
      `9cbab117e47cde6bd8850d67f0d363e03f0660ce`; item 6.4's versioned recipe
      presets and goal-first compile surfaces merged as PR #63 at
      `abdd630e25e83ebf346316319caec892f4d64886`; item 6.5 compile preflight
      merged as PR #64 at `b2e28b3dcfe48cd28ec74d8d8eaed12049f72d2d`;
      item 6.6's goal acceptance matrix merged as PR #65 at
      `7b93a32a5a9b18e5bc9c032750f467c4d9c43ea5`; item 6.7's instruction
      truthfulness and Phase 6 closeout merged as PR #67 at
      `6995d17bef0d09f235b1c464e947c38c63dd313d` after all 14 GitHub checks
      passed.
- [x] Independent product Phase 7 is complete under its
      [completed packet](dev/active/independent-product/phase-07-existing-dataset-import/README.md).
      Items 7.1–7.10 merged as PR #71–#80. Closeout merged as PR #80 at
      `b7bb7f0c2046fba87fd7c9da12f7d2ccb5c2c88f` after all 14 GitHub checks
      passed.
- [ ] Independent product Phase 8 is in progress under its
      [packet](dev/active/independent-product/phase-08-consumer-profiles/README.md).
      Item 8.1 merged as PR #82. Item 8.2 pins planned TRL and MLX-LM
      admission records with empty extras; both remain non-executable.
- [ ] Deliberate beta **label** cut (still alpha until then).
- [ ] Group 9 owner remainder: signed/notarized Mac (blocks **public** Mac app claim).
- [ ] Group 8 optional (owner-gated).

## Independent product program

The machine-readable ledger is authoritative for execution state. This table
is checked against it by `scripts/check_project_tracking.py` and pytest.

<!-- INDEPENDENT-PROGRAM:START -->
| Phase | Title | Status | Packet / authority |
| --- | --- | --- | --- |
| 0 | Establish authority, baseline, and decision records | Completed | [Completed packet](dev/active/independent-product/phase-00-foundation/README.md) |
| 1 | Enforce standalone independence | Completed | [Completed packet](dev/active/independent-product/phase-01-standalone-independence/README.md) |
| 2 | Close known reliability and artifact-boundary defects | Completed | [Completed packet](dev/active/independent-product/phase-02-reliability-artifact-boundary/README.md) |
| 3 | Formalize the goal, schema, container, and profile taxonomy | Completed | [Completed packet](dev/active/independent-product/phase-03-taxonomy/README.md) |
| 4 | Build the verified export foundation | Completed | [Completed packet](dev/active/independent-product/phase-04-verified-export-foundation/README.md) |
| 5 | Ship lossless generic local exports | Completed | [Completed packet](dev/active/independent-product/phase-05-generic-local-exports/README.md) |
| 6 | Deliver goal-first recipes and previews | Completed | [Completed packet](dev/active/independent-product/phase-06-goal-first-recipes/README.md) |
| 7 | Add first-class existing-dataset import and mapping | Completed | [Completed packet](dev/active/independent-product/phase-07-existing-dataset-import/README.md) |
| 8 | Implement the first consumer profiles | In progress | [Active packet](dev/active/independent-product/phase-08-consumer-profiles/README.md) |
| 9 | Add columnar and Hugging Face dataset containers | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 10 | Expand consumer profiles under evidence gates | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 11 | Harden collection ingest and qualify additional input types | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 12 | Add optional local OCR with accountable recovery | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 13 | Build dataset quality intelligence | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 14 | Deliver human review and correction workflows | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 15 | Measure and engineer scale, streaming, and sharding | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 16 | Establish a safe extension architecture | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 17 | Add governed advanced dataset families | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 18 | Complete the goal-first Mac workbench | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 19 | Complete automation and optional publication boundaries | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
| 20 | Cut the stable independent 1.0 product | Planned | [Roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) |
<!-- INDEPENDENT-PROGRAM:END -->

### Completed Phase 0 status

- [x] Phase 0.1 tracking and claim-control structures created.
- [x] Machine program ledger created.
- [x] Machine support registry created and bound to code constants.
- [x] Machine evidence index and evidence grades created.
- [x] Standard phase packet and ADR set created.
- [x] Automated drift checker and pytest regression added.
- [x] Phase 0.1 final verification and evidence recording.
- [x] Privacy-preserving corpus/workflow-demand matrix, with representative
      owner-corpus and trainer-frequency gaps explicitly unranked.
- [x] Active-document reconciliation against current code and authority.
- [x] Phase 0 closeout and final evidence recording.

### Completed Phase 1 status

- [x] CLI, MCP, and workbench default handoff disabled; explicit opt-in retained.
- [x] Default CLI/MCP import isolation and artifact absence locked by regression.
- [x] Required release and parity gates made standalone; optional Aptus adapter
      evidence split into a non-blocking job and explicit script.
- [x] Clean-wheel installed-CLI golden proof and standalone workbench smoke added.
- [x] Integrated Phase 1 closeout gates and final evidence recording.

### Completed Phase 2 status

- [x] Standard Phase 2 packet created after the Phase 1 exit gate passed.
- [x] Workbench process-concurrency, bounded-output, invalid-UTF-8, and cancellation regressions pinned.
- [x] Main-actor waiting replaced by responsive asynchronous execution with TERM/KILL recovery receipts.
- [x] Deterministic `.vfbundle.zip` selected and proved as the Finder-safe transport without weakening `minimal-v1`.
- [x] Workbench creates and reveals only the externally verified transport artifact for Finder use.
- [x] Mac, Linux, clean-wheel, golden, parity, launch, tracking, lint, and diff gates recorded.

### Completed Phase 3 status

- [x] Standard Phase 3 packet created after Phase 2 and pre-Phase-3 defect closure.
- [x] Versioned taxonomy contract and machine registry.
- [x] Current names reviewed; UI aliases recorded separately from persisted IDs.
- [x] Current and future-only families declared without false implementation claims.
- [x] Loss/masking described for every implemented semantic row.
- [x] Compatibility checks wired to fail before compile on every surface.
- [x] One registry exposed through PipelineService, CLI, MCP, and workbench help.
- [x] Public “format” language inventory and rewrite without persisted-ID changes.
- [x] Taxonomy golden round-trip and pre-taxonomy workspace/bundle compatibility proof.
- [x] Full Phase 3 closeout gates and status/support/evidence reconciliation.

### Completed Phase 4 status

- [x] Phase 4.1 — typed `ExportService` and descriptor-anchored verified source
      inspection are implemented.
- [x] Phase 4.2 — strict versioned export contracts and persisted models are
      implemented.
- [x] Phase 4.3 — trusted-by-default source admission and explicit lower-trust
      policy are implemented and merged.
- [x] Phase 4.4 — source-derived plan population binds immutable source,
      membership-baseline, profile, dependency, and output-plan evidence.
- [x] Phase 4.5 — normalized semantic candidates are fresh-reconstructed and
      required to match the exact plan row-set and membership baseline; merged
      at `1675c1a22830d506bdf27e45150170befc984bdf`.
- [x] Phase 4.6 — internal `portable_exact_bytes` publication re-verifies the
      source and plan, checks normalized membership, writes and independently
      verifies a closed receipt-bearing staging tree, and performs one atomic
      no-replace promotion; merged at
      `3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`.
- [x] Phase 4.7 — the private conformance path renders twice from independent
      strict inputs. Exact profiles require identical normalized byte trees;
      semantic profiles require equal versioned canonical semantic preimages,
      complete plan-equal membership, service-computed digests, and staged
      descriptor replay. PR #49 passed all 14 GitHub checks and merged at
      `6c3f0aff2e35edaa7920a0964270c410bf53f47b`.
- [x] Phase 4.8 — a private production-empty implementation catalog and strict
      cross-surface discovery, dry-run, inspect, execute, and verify operations
      merged as PR #50 at `fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`; review
      corrections merged as PR #51 at
      `d91542fe12c5a492de578ad060836a7d65999e42`.
- [x] Phase 4.9 — the consolidated adversarial harness, full exit gate, and
      active-document reconciliation are complete in the
      [completed packet](dev/active/independent-product/phase-04-verified-export-foundation/README.md).

At Phase 4 closeout, the foundation shipped without a production
implementation: discovery was empty and tests alone injected the conformance
exporter. Phase 5.1–5.3 install reviewed exact-byte renderers for
`split-jsonl-directory`, canonical `json`, and `constrained-csv` v1 and promote
only those consumer-neutral physical containers. Phase 5.4 adds their
post-export archive transport. No semantic replayer or trainer-specific profile
ships. The ten persisted export v1 models remain unchanged; additive request v2
carries only split JSONL's strict configuration. Constrained CSV admits the
three flat row schemas and refuses `messages` before publication.

### Completed Phase 5 status

- [x] Standard Phase 5 packet created and machine/human phase state changed to
      `in_progress` from baseline
      `a76e0fe3185b0e317cd453b9c28a1d2054e617dd`.
- [x] Phase 5.1 — generic split JSONL v1 merged as PR #53 at
      `4f12a55063c2721993b65cfbe30e68eaad55f87f`.
- [x] Phase 5.2 — canonical JSON v1 with explicit split/schema metadata merged
      as PR #54 at `f6a5d45f01e0b3117c259271bc59f3599a89dbb6`.
- [x] Phase 5.3 — constrained CSV v1 for `text`, `prompt_completion`, and
      `instruction_output` merged as PR #55 at `c6d7fc13a09a`; `messages` is
      refused before publication.
- [x] Phase 5.4 — deterministic generic export-pack archive integration merged
      as PR #56 at `499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`.
- [x] Phase 5.5 — the test-only semantic import-round-trip matrix merged as PR
      #57 at `c72b8e9ec7bc2746d74404226aa086d497e15db1`. It adds no production
      importer or replayer.
- [x] Phase 5.6 — exact sample-row and destination-tree dry-run previews merged
      as PR #58 at `cd017941090c7352cb1d10f9a383042b954d4f2e` after all 14
      GitHub checks passed; local `main` was synchronized before item 5.7.
- [x] Phase 5.7 — the
      [generic export operator guide](docs/generic-exports.md) separates
      container choice from objective, schema, and consumer compatibility, and
      the phase closeout records are reconciled. It merged as PR #59 at
      `65cbd471e96d83f8dd65e2cda60e90f64a916e2b` after all 14 GitHub checks
      passed; clean local `main` was synchronized before Phase 6 opened.

The Phase 5.1–5.7 implementation, guidance, and admission evidence support the
split JSONL, canonical JSON, and constrained CSV promotions. Phase 5 is
complete. Phase 5.4 ships
`deterministic-export-pack-zip-v1` through the existing `package` /
`package-verify` family and adds no fourth renderer, trainer compatibility,
source-bound archive verification, or Mac UI. Phase 5.5's merged,
discovery-closed fixture proves the 11 compatible pairs, the sole nested-CSV
refusal, and per-container semantic tampering without adding a production
importer or replayer. Item 5.6 adds only runtime response v2
with the unchanged plan, exact whole-or-omitted ordinal-zero partition samples,
and a normalized plan-derived tree plus receipt. Item 5.7 adds guidance and
closeout only. It changes no runtime contract, selector, taxonomy, support
state, consumer profile, or trainer claim; trainer-specific profiles remain
later work.

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

## Historical implementation program: private workbench / Groups 8–9

This section preserves the pre-independent-program implementation record. It
is not the active work queue; the machine ledger and phase table above control
current execution order.

### Private beta Mac workbench (owner plan)

Authority:
[docs/plans/2026-08-06-private-beta-workbench.md](docs/plans/2026-08-06-private-beta-workbench.md)

- [x] Phase 0 — Dogfood; punch list
      ([phase-0-dogfood.md](dev/active/private-beta-workbench/phase-0-dogfood.md))
- [x] Phase 1 — KISS shell on `main` (PR #22)
      ([phase-1-design.md](dev/active/private-beta-workbench/phase-1-design.md))
- [x] Phase 2 — Debugger power (digests, reveal, failure stage, re-run)
      ([phase-2-design.md](dev/active/private-beta-workbench/phase-2-design.md))
- Historical Phase 3–4 proposals are superseded by independent-roadmap Phases
  4–10 and 18. They are retained in the historical plan, not active here.

### Group 8: Advanced construction (optional)

- [ ] 25. Governed model-assisted construction (owner-approved plan required)

### Group 9: Public release

- [x] 26a. Automated gates — CI matrix (3.11–3.13 + macOS 3.12), `uv lock --check`,
  wheel install smoke, and the then-current golden corpus
  seal/verify/handoff-verify path under `scripts/release/`,
  [docs/release.md](docs/release.md), permanent regression
  `tests/regressions/test_group9_release_gates.py`
- [x] 26a+. Beta limitations register + clean-path evidence pack (CLI beta prep; not a label cut)
- [ ] 26b. Owner Mac distribution — Developer ID sign, notarize, staple, and
  clean-Mac install (see release checklist) — **public** Mac claim. Aptus proof
  is optional integration evidence, not a core product-release requirement.

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

## Historical Group 9 remainder

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
  - Golden raw corpus compile + standalone verification with retained logs.
  - Optional Aptus integration evidence is recorded separately when claimed.

**Exit gate (public):** A clean supported Mac can install the signed and
notarized product, compile the golden raw corpus, and independently verify the
final bundles. Any named consumer compatibility claim requires its own
independently recorded profile evidence.

**CLI beta (future label cut):** See [docs/beta-limitations.md](docs/beta-limitations.md)
and the [beta readiness audit](dev/active/group-9-public-release/beta-readiness-audit.md).

## Historical execution order and dependencies

These rules governed the completed group-based program. The independent
product roadmap now controls active sequencing.

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

Groups 1–7 documentation, the Group 9 release guide, and beta limitations are
retained as implementation history. The active architecture deep-dive is being
reconciled against `PipelineService` and the independent product authority.

Remaining documentation debt:

- [ ] Keep architecture deep-dives semantic and symbol-oriented; avoid fragile
  line citations where stable source symbols are available.
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
- The checked-in optional Aptus adapter policy rejects plain `text` rows; live
  named-version compatibility has not been established in this repository.
- The CLI cannot submit completed human review evidence.
- The minimal bundle omits raw sources and complete replay artifacts.
- External trust requires a manifest digest retained outside the bundle.
- Model-assisted construction remains optional and unapproved (Group 8).
- Automated CI/packaging gates land; public readiness still needs owner Mac evidence.

## Verification snapshot

Historical post–private-beta-workbench snapshot (`18d7541`, 2026-08-06):

```text
uv lock --check
uv run ruff check src tests
uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"
bash scripts/release/smoke_install.sh
bash scripts/release/golden_compile.sh
bash macos/scripts/parity_check.sh
git diff --check
```

Current CI definition: Python 3.11–3.13 Ubuntu + 3.12 macOS; Ruff; core
pytest; clean-wheel installed-CLI smoke; standalone golden compile; optional
non-blocking Aptus adapter self-conformance.

Additional permanent locks: Group 5 declared-input-type e2e, MCP/service parity,
optional Aptus adapter, Group 9 release-gate regressions, workbench Swift tests,
`macos/scripts/parity_check.sh`, clean-path evidence under
`dev/active/group-9-public-release/evidence/`.

Rerun these checks before calling this snapshot current. Do not hard-code
pytest totals; they grow.

## Maintenance rules

1. Check an item only after its deliverable, verification, evidence, and
   documentation satisfy the local completion rule. Do not treat that check as
   proof of its own pull-request result; where execution is sequential, merge
   the item and synchronize clean `main` before starting the next item or phase.
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
- [Authoritative independent product roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md)
- [Product contract](docs/product-contract.md)
- [Integrity Contract v1](docs/contracts/integrity-v1.md)
- [Dataset Construction Contract v1](docs/contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](docs/contracts/finished-dataset-v1.md)
- [Deterministic Archive Transport v1](docs/contracts/bundle-transport-v1.md)
- [Split JSONL Export Contract v1](docs/contracts/split-jsonl-export-v1.md)
- [Canonical JSON Export Contract v1](docs/contracts/canonical-json-export-v1.md)
- [Constrained CSV Export Contract v1](docs/contracts/constrained-csv-export-v1.md)
- [Generic Export Operator Guide](docs/generic-exports.md)
- [Aptus Handoff Contract v1](docs/contracts/aptus-handoff-v1.md)
- [Architecture](docs/architecture.md)
- [Architecture tree](docs/architecture/README.md)
- [CLI reference](docs/cli.md)
- [Development guide](docs/development.md)
- [Install guide](docs/install.md)
- [Release guide](docs/release.md)
- [Beta limitations](docs/beta-limitations.md)
- [Private beta workbench vision](docs/plans/2026-08-06-private-beta-workbench.md)
- [Beta readiness audit](dev/active/group-9-public-release/beta-readiness-audit.md)
- [macOS workbench](macos/README.md)
