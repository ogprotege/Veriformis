# Phase 4 Evidence

**Evidence status:** In progress — Phases 4.1–4.3 merged; Phase 4.4 local gates passed

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
- [ ] No-membership-change proof.
- [ ] Atomic, path-safe, cancelable, no-replace publication.
- [ ] Exact-byte and semantic-only evidence limits.
- [ ] Discovery, dry run, inspect, execute, and verify parity across surfaces.
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
