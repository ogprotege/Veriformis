# Phase 4 Evidence

**Evidence status:** In progress — Phases 4.1–4.7 merged; Phase 4.8 is locally
implemented with every required local gate passing and pull-request review
pending

**Predecessor:** [Phase 3 closeout](../phase-03-taxonomy/closeout.md)

## Source-verified starting facts

| Fact | Evidence | Limitation |
| --- | --- | --- |
| Canonical source is the closed `minimal-v1` bundle | Finished Dataset Contract v1; `bundle/finished.py` | Not an external trainer container |
| External digest is the existing trusted bundle grade | `bundle/verifier.py`; Finished Dataset Contract v1 | Requires a separately retained manifest digest |
| Verifier reconstructs exact rows and provenance | `bundle/verifier.py` row-alignment pass | Prior public result discarded reconstructed state |
| `PipelineService` is the composition root | `pipeline/service.py`, CLI, MCP, workbench architecture | No export service existed at the Phase 3 baseline |
| Generic containers are planned for Phase 5/9 | Taxonomy v1 and support registry | Phase 4 conformance exporter must remain test-only |
| Phase 4 began from synchronized commit `db9d93e` | Fresh `git fetch`; local and `origin/main` rev-parse | Recorded local |

## Required final evidence

- [x] Strict export contract models and canonical identity replay.
- [x] Explicit trusted and lower-trust source policy.
- [x] Complete source, split, row, profile, dependency, and output-plan bindings.
- [x] Complete immutable source membership baseline derived from aligned rows and
      provenance.
- [x] Normalized semantic candidate no-membership-change proof.
- [x] Atomic, path-safe, cancelable, no-replace publication.
- [x] Exact-byte and semantic-only evidence limits.
- [x] Discovery, dry run, inspect, execute, and verify parity across surfaces.
- [ ] Contract/property, tamper, path, race, and partial-publication harness.
- [ ] Full Phase 4 exit and reconciliation gates.

Observed results are appended only after the commands complete.

## 2026-08-21 — Phase 4.1 typed service and verified source view

- Focused export, finished-bundle, and retained Phase 3 compatibility suite:
  77 passed.
- Full Python suite: 772 passed with the expected transport durability-warning
  regression warning.
- Exact standalone release gate: 760 passed, 1 deselected, the same expected
  warning; clean-wheel install, both objective goldens, external-digest checks,
  and deterministic transports passed with retained digests unchanged.
- Ruff, project tracking, CLI/workbench parity, and `git diff --check` passed.
- macOS XCTest: 38 passed.
- An adversarial read-only review found and the implementation corrected
  subclass initialization, falsey injection, runtime annotation resolution,
  and legacy verifier error-envelope compatibility before the final reruns.

This evidence proves only the Phase 4.1 service/source boundary. It does not
claim persisted export models, a writer, public commands, a generic container,
or a trainer profile.

## 2026-08-21 — Phase 4.2 versioned export models

- Verified Export Contract v1 fixes ten exact schemas and identity domains.
- All models are strict, frozen, exactly fielded, canonically serialized, and
  independently reload every nested identity and cross-reference.
- Adversarial coverage rejects malformed versions, duplicate keys, floats,
  noncanonical bytes, Boolean/integer coercion, Unicode/path aliases,
  cross-partition leakage groups, forged source-verification identities,
  zero-count success evidence, and mismatched plan/receipt graphs.
- Focused model and contract suite: 55 passed.
- Combined export-service, model, and contract suite: 63 passed.
- Full Python suite: 827 passed with the expected exercised transport
  durability-warning regression warning.
- Exact standalone release gate: 815 passed, 1 deselected, the same expected
  warning; clean-wheel install, both objective goldens, external-digest checks,
  and deterministic transports passed with retained digests unchanged.
- Ruff, project tracking, CLI/workbench parity, and `git diff --check` passed.
- macOS XCTest: 38 passed.
- A fresh independent adversarial review found no remaining Phase 4.2 blocker
  after source-verification, dependency, path, Unicode, zero-byte, and digest-
  preimage closure fixes.

PR #44 passed all 14 GitHub checks and merged as `8d9ab904`. This increment did not implement source
admission, plan population, writing, commands, a production container, or a
trainer profile.

## 2026-08-21 — Phase 4.3 source-trust enforcement

- Export admission defaults to `require_external_digest` and refuses a missing
  retained expected manifest SHA-256 before resolving the source path.
- `allow_self_consistent` must be selected explicitly. With no digest it
  records `self_consistent`; with matching evidence it records
  `external_digest` rather than forcing a downgrade.
- Malformed, mismatched, and tampered evidence fails without retry or fallback
  under both policies. Impossible inspector grade or digest drift fails under
  the verified-export error envelope instead of being relabeled.
- Adversarial path-like probes prove malformed evidence is rejected before
  `__fspath__`; mismatch and tamper regressions prove source bytes remain
  unchanged. This increment has no destination or writer surface.
- Focused export-service, model, and contract suite: 83 passed.
- Full Python suite: 847 passed with the expected exercised transport
  durability-warning regression warning.
- Exact standalone release gate: 835 passed, 1 deselected, the same expected
  warning; clean-wheel install, both objective goldens, external-digest checks,
  and deterministic transports passed with retained digests unchanged.
- Ruff, project tracking, CLI/workbench parity, and `git diff --check` passed.
- macOS XCTest: 38 passed.
- Independent adversarial review found and the implementation corrected
  digest-validation-before-path ordering and one overbroad dependency claim;
  focused tests and release/full gates were rerun after the code fix.

This evidence proves only source-trust admission. It does not claim plan
population, destination binding, writing, public commands, a production
container, or a trainer profile.

PR #45 passed every required GitHub check and merged as `159fcce4`. Local
`main` was clean and synchronized to that commit before Phase 4.4 began.

## 2026-08-21 — Phase 4.4 source-derived plan population

- `ExportService.create_plan` performs one trusted source admission and derives
  every source identity, objective identity, source-ID scope, and complete
  source membership baseline from the returned immutable bundle view.
- The membership baseline binds record, row, provenance, assignment,
  leakage-group, partition, ordinal, and payload-digest facts in authoritative
  source order. It is not accepted from the caller.
- Caller-controlled inputs are limited to the strict container profile,
  optional consumer profile, dependencies, file plans, and source-trust
  policy/evidence. Invalid or cross-source evidence fails before any write.
- Exact-byte file plans bind expected SHA-256 and size; semantic-only file plans
  bind semantic content and intentionally defer actual instance SHA-256 and
  size to later destination evidence.
- No destination membership reconstruction or comparison, writer, receipt,
  public surface, supported container, or trainer profile is claimed.

- Focused export-service, model, and contract suite: 99 passed.
- Full Python suite: 863 passed with the expected exercised transport
  durability-warning regression warning.
- Exact standalone release gate: 851 passed, 1 deselected, the same expected
  warning; clean-wheel install, both objective goldens, external-digest checks,
  and deterministic transports passed with retained digests unchanged.
- Ruff, project tracking, CLI/workbench parity, JSON and shell structure, 329
  changed-document local links, and `git diff --check` passed.
- macOS XCTest: 38 passed.
- Independent adversarial review found a coherent stale-identity substitution
  gap. Fresh strict source-model replay plus manifest/snapshot/report/row-set
  byte-edge closure corrected it; the reproducer and adjacent forged-graph
  cases now fail closed, and re-review found no remaining blocker.

PR #46 passed every required GitHub check and merged as
`3ba83aeb3164d72d1aa14100637272a141f580c9`. Local `main` was clean and exactly
equal to `origin/main` before the Phase 4.5 branch was created.

## 2026-08-21 — Phase 4.5 derivative-only semantic membership

- `ExportService.validate_derivative_membership` fresh-loads the plan and
  normalized candidate train rows, evaluation rows, and aligned provenance.
- It reconstructs a candidate `RowSet` using only plan-bound identities,
  requires the exact planned row-set identity, derives the complete candidate
  projection, and requires exact object and canonical-byte equality with the
  source membership baseline.
- Separate logical partition sequences prevent repartitioning from being hidden
  in claimed provenance. Counts and assignment-projection digest alone never
  constitute success.
- Omission, addition, duplication, reordering, coherent target mutation,
  assignment and leakage-group substitution, objective/source-scope drift,
  balancing, repartitioning, and resplitting fail closed.
- The operation exposes no membership-changing or destination control, performs
  no filesystem write, and creates no destination binding or receipt.
- Focused export-service tests: 59 passed; combined export and verified-export
  contract tests: 114 passed.
- Full Python suite: 878 passed with the expected exercised transport
  durability-warning regression warning.
- Exact standalone release gate: 866 passed, 1 deselected, the same expected
  warning; clean-wheel install, both objective goldens, external-digest checks,
  and deterministic transports passed.
- Ruff, project tracking, CLI/workbench parity, JSON and shell structure, 329
  changed-document local links, and `git diff --check` passed.
- macOS XCTest: 38 passed.
- Independent adversarial review found that the first implementation validated
  but retained caller-owned candidate models and their mutable payload mapping.
  The service now strict-serializes and reloads every candidate row and
  provenance value before row-set construction. An identity-separation
  regression proves those fresh snapshots, and re-review found no remaining
  blocker.

This evidence proves normalized in-memory semantic membership preservation. It
does not prove that produced destination bytes encode those semantics; writing
remains Phase 4.6 and exact-byte or semantic replay remains Phase 4.7.

PR #47 passed every required GitHub check and merged as
`1675c1a22830d506bdf27e45150170befc984bdf`. Local `main` was clean and exactly
equal to `origin/main` before the Phase 4.6 branch was created.

## 2026-08-21 — Phase 4.6 exact-byte atomic publication

The implementation under review is scoped to one private test-injected
`portable_exact_bytes` conformance renderer. It re-verifies the source and
rebuilds the exact plan before rendering, validates the renderer's complete
exact-byte file set and normalized semantic membership before staging, writes a
canonical in-tree receipt through anchored descriptors, independently rewalks
the closed tree, and uses one atomic no-replace promotion.

The Phase 4.6 proof includes cancellation before visibility, owned-
staging cleanup, existing-target and race preservation, path/link/special-file
rejection, staged and visible-tree tamper rejection, source re-verification,
canonical receipt and actual digest/size replay, and honest post-visibility
durability reporting.

- Publication-only tests: 36 passed.
- Combined export and verified-export contract tests: 150 passed.
- Full Python suite: 914 passed with the expected exercised transport
  durability-warning regression warning.
- Exact standalone release gate: 902 passed, 1 deselected, with the same
  expected warning; clean-wheel installation, both objective goldens,
  external-digest verification, and deterministic transport passed.
- macOS XCTest: 38 passed.
- CLI/workbench parity, lock, Ruff, project tracking, JSON and shell structure,
  347 changed-document local links, and `git diff --check` passed.
- Independent adversarial review reproduced and verified fixes for plan-digest
  self-anchoring, verification-before-staging, cleanup ownership and name-swap
  races, FIFO blocking, receipt bounds, cancellation ordering, target
  substitution, typed verifier I/O, and partial-publication reporting. Final
  review found no remaining blocker under the documented integrity-controlled
  destination-parent boundary.

This increment does not prove a second exact render, reconstruct semantic
content from produced bytes, publish `semantic_content_only`, install or select
a product renderer, expose `PipelineService`/CLI/MCP/Mac operations, or promote
a container or consumer profile.

PR #48 passed every required GitHub check and merged as
`3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`. Local `main` was clean and exactly
equal to `origin/main` before the Phase 4.7 branch was created.

## 2026-08-21 — Phase 4.7 deterministic evidence implementation

- Both determinism claims invoke the private renderer twice from independent
  strict plan and source-row-set reloads and validate complete membership for
  each result before destination access.
- `portable_exact_bytes` normalizes by exact planned path and requires complete
  byte-tree equality. Only the first identical tree is published.
- `semantic_content_only` permits physical byte differences but privately
  reconstructs complete profile-versioned canonical semantic preimages and
  normalized membership from both trees. The service computes the digests and
  requires both results to match each other and the plan.
- Semantic publication replays descriptor-reread staged bytes again and
  requires the complete preflight semantic evidence before verification and
  promotion.
- Deterministic plan, receipt, verification, and closed-tree fixtures exercise
  the private conformance profile without registering or advertising it.
- The public `publish` signature and all ten persisted v1 schemas remain
  unchanged. `ExportVerification` binds one published instance and its profile
  claim, not a durable rerender transcript.
- The default service still has no renderer or semantic replayer. No public
  surface, discovery entry, generic container, consumer profile, taxonomy
  change, or support-registry change is part of this increment.

Observed results:

- Focused deterministic-evidence suite: 14 passed.
- Complete export suite: 158 passed.
- Combined export and verified-export contract suite: 163 passed.
- Full Python suite: 927 passed with the expected exercised transport
  durability-warning regression warning.
- Standalone release gate: 915 passed, 1 deselected, with the same expected
  warning; clean-wheel install and golden compile checks passed.
- macOS XCTest: 38 passed.
- CLI/workbench parity passed.
- Project tracking passed for all 21 roadmap phases and governed packets.
- Ruff, lock integrity, 14 JSON files, 10 shell files, 345 changed-document
  local links, and `git diff --check` passed.
- Independent source review found no blocker after confirming the private
  render/replay hooks are trusted conformance code and documenting that semantic
  replay retains each complete produced file in memory. The fixture is
  statically bounded; every future shipped semantic profile must enforce
  explicit resource limits.

PR #49 passed all 14 GitHub checks and merged at
`6c3f0aff2e35edaa7920a0964270c410bf53f47b`. This is not completed Phase 4
exit evidence; Phase 4.8 surfaces and Phase 4.9 closeout remain separate.

## 2026-08-21 — Phase 4.8 strict cross-surface export operations

- A private immutable exact-selector implementation catalog backs discovery,
  dry run, inspect, execute, and verify. The production catalog is empty; only
  tests inject the conformance renderer and semantic replayer.
- Dry run derives its plan from one admitted source without destination access.
  Execute re-derives the plan and requires its operator-confirmed identity
  before rendering or destination access. Inspect proves only self-described
  physical closure; source-bound verify separately re-verifies the source and
  re-derives the plan.
- `PipelineService`, CLI, MCP, and the CLI-backed Mac bridge use the same three
  strict canonical surface schemas. Frozen cross-surface evidence proves the
  same plan, receipt, verification, and file digests.
- Python publicly exports the cancellation callback type, frozen publication
  outcome, and visible-partial exception so callers can type honest runtime
  behavior without importing an underscore module; render, replay, and
  filesystem hooks remain private.
- Requests cannot supply a plan, profile, dependency graph, file plan,
  membership projection, renderer, semantic replayer, registry entry, force,
  or replacement control. Overwrite policy is exactly `refuse`.
- Admission bounds requests and responses at 1 MiB, runtime paths at 32 KiB,
  executable dry-run responses at 256 KiB, and directory depth at 128 before
  rendering. The Mac bridge independently bounds each process stream at 2 MiB
  and validates canonical stdout without treating stderr as protocol data.
- Cancellation preserves a complete successful or visible-partial response;
  forced termination without a complete response is reported as ambiguous,
  never as a proven rollback.
- Pull-request review additionally verified failure-safe visible-partial
  reporting without strict evidence reloads, cooperative cancellation around
  source admission and planning, serialized large-receipt inspection memory,
  shared root anchoring, public MCP test dispatch, raw-byte taxonomy decoding,
  and the Mac-side 32 KiB UTF-8 path bound.

Observed results:

- Focused API and adapter suite: 29 passed.
- Complete export suite: 187 passed.
- Combined export and verified-export contract suite: 192 passed.
- Full Python suite: 956 passed with the expected exercised transport
  durability-warning regression warning.
- Standalone release gate: 944 passed, 1 deselected, with the same expected
  warning; clean-wheel installation, both objective goldens, external-digest
  verification, and deterministic transports passed.
- macOS XCTest: 54 passed.
- CLI/workbench parity and project tracking passed.
- Ruff, lock integrity, 15 JSON files, 10 shell files, 373 changed-document
  local links, and `git diff --check` passed.
- Independent and pull-request adversarial review found and verified
  corrections for invalid-Unicode error serialization, recursive deep-tree
  failure, unbounded concurrent receipt parsing, delayed cancellation, lossy
  taxonomy decoding, and failure-prone visible-partial reporting. Iterative
  descriptor traversal, bounded memory and depth, canonical adapter failures,
  pre-render admission, and regression tests leave no known Phase 4.8 blocker.

This evidence does not ship or advertise a renderer, semantic replayer,
generic export container, or consumer profile and changes none of the ten
persisted verified-export v1 schemas, the taxonomy, or the support registry.
It is not Phase 4 exit evidence; the complete adversarial closeout harness and
reconciliation remain Phase 4.9.
