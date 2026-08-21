# Phase 4 Progress Log

This file is append-only by dated entry. Corrections are recorded in later
entries rather than deleting earlier history.

## 2026-08-21 — Phase 4 started

**Status:** In progress

**Predecessor:** Phase 3 completed and merged on `main` as PR #41 at
`db9d93ef88e273e3727e1ba85841589530d59da3`. Local `main` was clean and equal
to freshly fetched `origin/main` before the Phase 4.1 branch was created.

**Starting facts reviewed:**

- `minimal-v1` remains the canonical strict six-file bundle.
- The bundle verifier already reconstructs exact rows and aligned provenance
  under anchored descriptors, but previously discarded that typed state.
- There is no export plan, receipt, publication service, export verifier,
  generic export command, or production generic export container.
- CLI and MCP call `PipelineService`; the Mac workbench shells the CLI.
- Generic JSONL, JSON, and CSV containers remain Phase 5 work.

**Next action:** Complete Phase 4.1 by installing the typed service beneath the
composition root, retaining verified source semantics from the same anchored
verification pass, and observing all required PR gates.

## 2026-08-21 — Phase 4.1 local implementation complete

**Status:** Ready for pull-request review

The typed `ExportService` is injected beneath `PipelineService` and exposes a
verified-source operation only. The finished-bundle verifier now offers an
immutable semantic inspection result from its existing descriptor-anchored
pass while `verify_finished_bundle()` preserves its established result and
error contracts. Existing subclasses that omit `super().__init__()` and falsey
injected services remain compatible.

Observed local gates: 77 focused tests, 772 full Python tests, 760 standalone
core tests with 1 deselected, clean-wheel and both golden compile/transport
flows, Ruff, tracking, CLI/workbench parity, 38 Xcode tests, and diff checks all
passed. The only Python warning was the expected exercised transport
durability-warning regression.

**Next action:** Open Phase 4.1 PR, require every GitHub check to pass, merge,
and synchronize clean local `main` to `origin/main` before Phase 4.2 begins.

## 2026-08-21 — Phase 4.1 merged and synchronized

**Status:** Complete

PR #43 passed every GitHub check and was squash-merged as
`494fb3b2f4083b17392763258f905af8bd539da0`. Local `main` was fetched, clean,
and exactly equal to `origin/main` before the Phase 4.2 branch was created.

## 2026-08-21 — Phase 4.2 local implementation complete

**Status:** Ready for pull-request review

Verified Export Contract v1 and ten strict persisted models now close the
portable plan/profile/dependency/membership/file/receipt/verification graph.
Every identity is replayed from canonical exact fields; nested source,
membership, evidence-mode, path, and receipt relationships fail closed. The
support registry and taxonomy remain unchanged: no generic container or
trainer profile is promoted.

Focused model/contract (55) and combined export (63) tests pass. The full
Python suite passed 827 tests; the standalone release gate passed 815 with 1
deselected; both emitted only the expected transport durability warning. Clean
wheel, both objective goldens, deterministic transport, 38 XCTest tests,
parity, tracking, Ruff, and diff checks passed. Independent adversarial review
found no remaining Phase 4.2 blocker.

**Next action:** Open the Phase 4.2 PR, require all GitHub checks to pass,
merge, and synchronize clean local `main` before Phase 4.3 begins.

## 2026-08-21 — Phase 4.2 merged and synchronized

**Status:** Complete

PR #44 passed all 14 GitHub checks and was squash-merged as
`8d9ab90448b70b7d6673dd187754156c450fde7a`. Local `main` was clean and
exactly equal to `origin/main` before the Phase 4.3 branch was created.

## 2026-08-21 — Phase 4.3 source-trust enforcement started

**Status:** In progress

Export-source admission now defaults to `require_external_digest`; a retained
expected manifest SHA-256 is required before source inspection. The existing
lower trust grade is admitted only through explicit `allow_self_consistent`.
Any supplied digest remains authoritative, and the service rejects mismatched
or impossible observed evidence without retrying or relabeling it. This
increment remains read-only and adds no plan builder, destination writer,
surface method, generic container, or trainer profile.

**Next action:** Complete focused, full, release, parity, tracking, Mac, Ruff,
diff, and independent review gates before opening the Phase 4.3 PR.

## 2026-08-21 — Phase 4.3 local implementation complete

**Status:** Ready for pull-request review

The export service now makes externally anchored trust the secure default,
requires explicit policy for self-consistent admission, preserves every
supplied digest as authoritative evidence, and rejects impossible observed
grades or digests. Validation occurs before source-path resolution, one
descriptor-anchored inspector pass performs all bundle reads, and failure
tests prove source bytes remain unchanged. No writer or destination operation
exists in this increment.

Focused service/model/contract tests passed 83 tests. The full Python suite
passed 847 tests; the standalone release gate passed 835 with 1 deselected;
both emitted only the expected transport durability warning. Clean wheel,
both objective goldens, deterministic transport, 38 XCTest tests, parity,
tracking, Ruff, and diff checks passed. Independent adversarial review found
the pre-path digest-ordering defect, confirmed its correction under both trust
policies, and found no remaining implementation blocker.

**Next action:** Open the Phase 4.3 PR, require every GitHub check to pass,
merge, and synchronize clean local `main` before Phase 4.4 begins.

## 2026-08-21 — Phase 4.3 merged and synchronized

**Status:** Complete

PR #45 passed every required GitHub check and was squash-merged as
`159fcce46059b1becad5664046331d44980d0f14`. Local `main` was clean and exactly
equal to `origin/main` before the Phase 4.4 branch was created.

## 2026-08-21 — Phase 4.4 source-derived plan population complete

**Status:** Implementation complete; local gates pending

`ExportService.create_plan` now admits one source through the existing trust
boundary and derives every bundle, manifest, validation, snapshot, objective,
split, row-set, row-schema, source-scope, and source-membership-baseline fact
from that immutable verified view. Callers provide only strict container and
optional consumer profiles, exact dependency bindings, and file-plan evidence.
The resulting portable plan excludes destination roots and runtime state.

This increment does not render or compare destination membership, write or
publish files, create a receipt, expose a public surface, or register a
supported container or consumer profile. Phase 4.5 owns destination membership
reconstruction and comparison; Phase 4.6 owns filesystem operations.

Focused, full, release, parity, tracking, Mac, Ruff, and diff gates have not yet
been recorded for this increment.

**Next action:** Complete every required local gate and independent review,
then open the Phase 4.4 PR. Require every GitHub check to pass, merge, and
synchronize clean local `main` before Phase 4.5 begins.

## 2026-08-21 — Phase 4.4 local gates complete

**Status:** Ready for pull-request review

Focused service/model/contract tests passed 99 tests. The full Python suite
passed 863 tests; the standalone release gate passed 851 with 1 deselected;
both emitted only the expected transport durability warning. Clean-wheel
install, both objective goldens, external-digest verification, deterministic
transport, 38 XCTest tests, CLI/workbench parity, tracking, Ruff, structured
files, shell syntax, 329 changed-document local links, and diff checks passed.

Independent adversarial review reproduced a coherent stale-identity source
substitution across snapshot, row set, and provenance. The service now fresh-
validates every admitted source model and closes manifest-to-snapshot,
manifest-to-report, and snapshot-to-row-set byte edges before plan creation.
The exploit and adjacent forged-graph cases fail closed; re-review found no
remaining blocker.

**Next action:** Open the Phase 4.4 PR, require every GitHub check to pass,
merge, and synchronize clean local `main` before Phase 4.5 begins.
