# Phase 4 Evidence

**Evidence status:** In progress — Phase 4.1 merged; Phase 4.2 local gates passed

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
- [ ] Explicit trusted and lower-trust source policy.
- [ ] Complete source, split, row, profile, dependency, and destination bindings.
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

GitHub evidence remains pending. This increment does not implement source
admission, plan population, writing, commands, a production container, or a
trainer profile.
