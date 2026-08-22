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

## 2026-08-21 — Phase 4.4 merged and synchronized

**Status:** Complete

PR #46 passed every required GitHub check and was squash-merged as
`3ba83aeb3164d72d1aa14100637272a141f580c9`. Local `main` was clean and exactly
equal to `origin/main` before the Phase 4.5 branch was created.

## 2026-08-21 — Phase 4.5 derivative-only membership implemented

**Status:** Focused tests passed; remaining local gates in progress

`ExportService.validate_derivative_membership` now fresh-reconstructs one
candidate `RowSet` from separate normalized train/evaluation `ProductRow`
sequences and their aligned `RowProvenance`. It uses only plan-bound identities,
requires the exact planned row-set identity, derives the complete candidate
membership projection, and requires exact object and canonical-byte equality
with the source baseline. The service returns the checked projection on success
and raises `export-verification-invalid` for every mismatch.

Focused export-service tests passed 59 tests, including omission, coherent
addition, duplication, reorder, target mutation, assignment and leakage-group
substitution, objective/source-scope drift, repartitioning, stale-model,
read-only, and API-control cases. Remaining full, release, parity, tracking,
Mac, Ruff, structure, link, diff, and independent-review gates are in progress.

This increment performs no filesystem or destination-byte verification, creates
no destination binding or receipt, exposes no public surface, and registers no
container or consumer profile. Phase 4.6 may begin only after the Phase 4.5 PR
passes every GitHub check, merges, and clean local `main` equals `origin/main`.

**Next action:** Complete the remaining Phase 4.5 local gates and independent
review, then open the Phase 4.5 PR.

## 2026-08-21 — Phase 4.5 local gates complete

**Status:** Ready for pull-request review

Focused export-service tests passed 59 tests and the combined export/contract
selection passed 114. The full Python suite passed 878 tests; the standalone
release gate passed 866 with 1 deselected. Both emitted only the expected
transport durability-warning regression warning. Clean-wheel installation,
both objective goldens, external-digest verification, deterministic transport,
38 XCTest tests, CLI/workbench parity, tracking, Ruff, JSON and shell structure,
329 changed-document local links, and diff checks passed.

Independent review found that the initial candidate boundary validated but
retained caller-owned models, including a mutable payload mapping. The service
now strict-serializes and reloads every candidate row and provenance value
before constructing the row set. A regression proves the checked row, nested
payload, and provenance objects are fresh snapshots; re-review found no
remaining blocker.

**Next action:** Open the Phase 4.5 PR, require every GitHub check to pass,
merge, and synchronize clean local `main` before Phase 4.6 begins.

## 2026-08-21 — Phase 4.5 merged and synchronized

**Status:** Complete

PR #47 passed every required GitHub check and was squash-merged as
`1675c1a22830d506bdf27e45150170befc984bdf`. Local `main` was clean and exactly
equal to `origin/main` before the Phase 4.6 branch was created.

## 2026-08-21 — Phase 4.6 exact-byte atomic publication started

**Status:** Implementation in progress; local gates pending

The export service now has a Python-composition-only publication boundary for
one test-injected exact-byte conformance renderer. Publication fresh-validates
the plan, re-verifies the source with separately retained trust evidence,
rebuilds the plan from that immutable source, and validates both the complete
renderer file set and normalized semantic membership before staging.

The in-progress publisher uses a private descriptor-anchored sibling, writes a
canonical receipt, independently rewalks the exact closed tree, and performs
one atomic no-replace promotion with explicit cancellation and visible-warning
semantics. The default service has no renderer, no renderer-selection argument,
and no supported container. `semantic_content_only` publication, deterministic
rerendering, semantic replay, `PipelineService` methods, and all adapter
surfaces remain deferred.

No focused, full, release, parity, tracking, Mac, Ruff, structure, link, diff,
or independent-review gate is recorded for Phase 4.6 yet.

**Next action:** Complete the Phase 4.6 implementation and adversarial review,
then run and record every required local gate before opening its pull request.

## 2026-08-21 — Phase 4.6 local gates complete

**Status:** Ready for pull-request review

The private Phase 4.6 exact-byte publisher now fresh-reloads its plan,
re-verifies source trust from separately retained evidence, reconstructs the
complete plan, validates exact renderer bytes and normalized membership before
staging, writes the canonical receipt inside staging, independently verifies
the closed tree, and uses one atomic no-replace promotion. Cancellation stops
before visibility; parent-sync and later bookkeeping failures report visible
outcomes honestly.

The publication-only suite passed 36 tests and the combined export/contract
selection passed 150. The full Python suite passed 914 tests; the standalone
release gate passed 902 with 1 deselected. Both emitted only the established
transport durability-warning regression warning. Clean-wheel installation,
both objective goldens, external-digest verification, deterministic transport,
38 XCTest tests, CLI/workbench parity, tracking, Ruff, JSON and shell structure,
347 changed-document local links, and diff checks passed.

Independent adversarial review found and verified corrections for source-trust
self-anchoring, pre-staging verification claims, staged-name and cleanup
ownership races, FIFO blocking, receipt bounds, cancellation ordering, target
substitution, typed verifier I/O, and post-visibility reporting. The contract
now states the integrity-controlled destination-parent boundary shared with the
finished-bundle publisher. Re-review found no remaining Phase 4.6 blocker.

The default service still has no renderer. Exact rerender proof and semantic
reconstruction remain Phase 4.7; public `PipelineService`, CLI, MCP, and Mac
surfaces remain Phase 4.8; the exhaustive closeout harness remains Phase 4.9.

**Next action:** Open the Phase 4.6 PR, require every GitHub check to pass,
merge, and synchronize clean local `main` before Phase 4.7 begins.

## 2026-08-21 — Phase 4.6 merged and synchronized

**Status:** Complete

PR #48 passed every required GitHub check and was squash-merged as
`3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`. Local `main` was clean and exactly
equal to `origin/main` before the Phase 4.7 branch was created.

## 2026-08-21 — Phase 4.7 deterministic evidence implemented

**Status:** Implementation complete; every required local gate passes;
pull-request review pending

Publication now invokes the private conformance renderer twice from independent
strict reloads of the same plan and source row set, validating complete
membership for each result. `portable_exact_bytes` requires identical
normalized path-to-bytes trees before destination access and publishes only the
first result.

`semantic_content_only` permits different physical encodings but privately
replays both byte trees into complete profile-versioned canonical semantic
preimages and normalized membership evidence. The service computes every
semantic digest, requires both preimage trees and both memberships to match the
plan, publishes only the first physical tree, and replays descriptor-reread
staged bytes again before verification and promotion. Missing private render or
replay support and every byte, preimage, digest, membership, or staged-replay
mismatch fail closed.

The conformance fixtures freeze deterministic plan, receipt, verification, and
closed-tree evidence. This increment changes none of the ten persisted v1
schemas or public `publish` arguments, records no durable rerender transcript,
and adds no renderer/replayer registry, taxonomy or support-registry entry,
public surface, generic container, or consumer profile.

Observed implementation and release evidence:

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
- Independent source review found no blocker after confirming the trusted
  private-hook boundary and documenting whole-file semantic replay plus the
  resource limits required before a semantic profile can ship.

**Next action:** Open the Phase 4.7 pull request. Phase 4.8 may begin only after
every GitHub check passes, the PR merges, and clean local `main` equals
`origin/main`.

## 2026-08-21 — Phase 4.7 merged and synchronized

**Status:** Complete

PR #49 passed all 14 GitHub checks and was squash-merged as
`6c3f0aff2e35edaa7920a0964270c410bf53f47b`. Local `main` was fetched, clean,
and exactly equal to `origin/main` before the Phase 4.8 branch was created.

## 2026-08-21 — Phase 4.8 export surfaces implemented

**Status:** Implementation complete; local gates in progress

The export service now owns a private immutable catalog selected by exact
container and optional consumer identifiers and versions. Production discovery
is truthfully empty; only tests inject a conformance implementation. Dry run
derives a source-anchored plan without destination access. Execute re-derives
the plan and requires the operator-confirmed plan identity before rendering or
destination access. Inspect proves only self-described physical closure, while
verify separately re-verifies source authority and re-derives the plan.

`PipelineService`, CLI, MCP, and the CLI-backed Mac bridge share strict bounded
canonical request and response envelopes. The Mac process bridge captures
stdout and stderr separately and decodes only stdout. No surface accepts a
caller-built plan, profile, dependency graph, membership projection, renderer,
semantic replayer, force, or replacement control; overwrite remains the
literal `refuse`. The ten persisted v1 schemas, taxonomy, and support registry
are unchanged, and no production container or consumer profile is advertised.

**Next action:** Complete focused, full, release, Mac, parity, tracking,
structure, link, diff, and independent-review gates before opening Phase 4.8
PR. Phase 4.9 may begin only after every GitHub check passes, the PR merges, and
clean local `main` equals `origin/main`.

## 2026-08-21 — Phase 4.8 local gates complete

**Status:** Implementation complete; every required local gate passes;
pull-request review pending

The strict production-empty implementation catalog and shared discovery, dry-
run, inspect, execute, and verify protocol now pass end-to-end Python, CLI,
MCP, and CLI-backed Mac conformance. Request authority remains source-derived,
overwrite remains `refuse`, inspect remains self-described rather than source-
verified, and execute requires the re-derived plan identity before rendering
or destination access.

Focused API/adapter (29), complete export (187), combined export/contract
(192), full Python (956), standalone release (944 with 1 deselected), and Mac
XCTest (54) gates passed. Full and release Python runs emitted only the
expected exercised transport durability-warning regression warning. Clean-
wheel installation, both objective goldens, external-digest verification,
deterministic transport, parity, tracking, Ruff, lock integrity, 15 JSON files,
10 shell files, 373 changed-document local links, and diff checks passed.

Independent adversarial review found invalid-Unicode response serialization
and recursive deep-tree traversal blockers. Error text is now safely bounded
and sanitized, tree inspection is iterative and depth-bounded, adapters fail
canonically, and executable plans prove the depth and response bounds before
rendering. Re-review found no remaining Phase 4.8 blocker.

The production catalog remains empty; no generic container, consumer profile,
renderer, semantic replayer, registry API, force option, persisted-schema
change, taxonomy change, or support promotion is included.

A final public-boundary audit also found that typed Python execution exposed
its success and visible-partial types only through an underscore module. Those
two runtime types are now public exports, matching the honest execution API;
render, replay, registration, and filesystem hooks remain private.

PR #50 review then found and verified corrections for failure-safe
visible-partial reporting, concurrent large-receipt inspection memory,
cancellation around source admission and planning, duplicated root anchoring,
private MCP test dispatch, lossy taxonomy decoding, and the Mac-side UTF-8 path
bound. `CancellationCheck` is now a public type alongside the two runtime
publication types; no execution hook or registry became public.

**Next action:** Wait for every GitHub check and review on the Phase 4.8
corrective PR to pass. Phase 4.9 may begin only after that PR merges and clean
local `main` equals `origin/main`.
