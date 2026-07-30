# Group 3 Finished Dataset Implementation Plan

**Status:** Complete

**Roadmap scope:** Steps 11 through 16

**Contract:** [Finished Dataset Contract v1](../../../docs/contracts/finished-dataset-v1.md)

**Starting point:** M1 core plus merged Groups 1 and 2

**Last reviewed:** 2026-07-29

**Next review:** Any Group 3 contract change or regression

## Outcome

Complete the deterministic compiler path from supported raw source material to
one curated, leakage-safe, objective-preserving, exactly validated, atomically
sealed dataset. Group 3 consumes immutable Group 2 records. It does not bypass
construction with legacy chunk formatting.

## Runtime completion record

The Group 3 implementation completes sections 1 through 11 of this plan:

- public contracts, strict models, and accepted known-gap regressions;
- revision schema v3 and the v2 to v3 migration;
- deterministic curation, coverage, leakage grouping, and split assignment;
- construction-aware product rows and aligned provenance;
- exact snapshots and all 17 ordered validation gates;
- the exact six-file `minimal-v1` bundle;
- atomic publication with manifest and attestation receipts;
- independent `self_consistent` and `external_digest` verification; and
- direct stage-command CLI integration without `PipelineService`.

The complete repository test run is green with `606 passed`. A supported
two-source raw-input demonstration reached a sealed bundle and
`external_digest` verification. The independent
[architecture and security review](group-3-finished-dataset-code-review.md)
found no unresolved Critical, High, or Important defect. Active product
documentation now describes Group 3 as complete.

## Fixed decisions

- Preserve `DatasetRecipe v1`, `ConstructionResult v1`, and `DatasetRecord v1`.
- Add `FinishedDatasetPlan v1` to compose one exact recipe and result with
  executable curation, split, serialization, validation, and retention policy.
- Persist the complete composite as `curate.plan` before curation. Keep split
  and serialization policies nested rather than duplicating policy artifacts.
- Add workspace revision schema v3 with explicit `curate` and `split` stages.
- Retire active legacy format, validation, and seal state during v2 to v3
  migration. Preserve it only in immutable historical revisions.
- Validate Group 2 construction by exact replay before curation.
- Run minimum-target filtering, conflict quarantine, exact deduplication,
  optional balancing, and coverage closure in that order.
- Define conflicts as one objective, exact `source_ids` scope, and exact context
  with multiple exact targets.
- Define duplicates by objective ID plus exact ordered field names and Unicode
  values. Keep the minimum `record_id`.
- Support only balance mode `none` or deterministic `primary_source_cap` in v1.
- Build train and evaluation leakage groups from shared source IDs, equal raw
  digests, multi-source joins, and inherited exact-dedup-family relations.
  Assign whole groups only.
- Lower one included record into one product row. Fan-out is not a v1 feature.
- Require exact plan-bound instruction text only for `instruction_output`.
  `messages` uses the exact source-derived context and target.
- Emit payload-only Aptus JSONL and one combined aligned provenance NDJSON.
- Validate one exact snapshot that directly binds the six semantic stage
  artifacts and emitted bytes, with broader replay state bound transitively.
- Seal a deterministic minimal closed file set through a verified temporary
  sibling and atomic directory promotion.
- Keep the manifest self-hash-free. Bind it to co-located `attestation.json`,
  and require a caller-supplied expected manifest digest for external trust.
- Claim Aptus row-shape compatibility only. Shared bundle intake and
  authoritative split enforcement remain Step 23.
- Make no network call, model call, summary objective, or semantic PII or
  contradiction claim in deterministic v1.

## Workspace revision schema v3

The active stage order becomes:

```text
parse -> clean -> chunk -> construct -> curate -> split -> format -> validate -> seal
```

Direct dependencies are fixed by the contract. `split` reads construct and
curate. `format` reads construct, curate, and split. Validation and seal bind all
required upstream outputs directly.

The new fixed stage outputs are:

| Stage | Output key | Artifact kind | Producer | Version |
| --- | --- | --- | --- | --- |
| `curate` | `plan` | `finished-dataset-plan` | `veriformis.curation.plan` | `1` |
| `curate` | `result` | `curation-result` | `veriformis.curation.result` | `1` |
| `split` | `result` | `split-result` | `veriformis.splitting.result` | `1` |
| `format` | `row-set` | `formatted-row-set` | `veriformis.dataset-serializer.row-set` | `1` |
| `format` | `train` | `training-partition` | `veriformis.dataset-serializer.train` | `1` |
| `format` | `evaluation` | `evaluation-partition` | `veriformis.dataset-serializer.evaluation` | `1` |
| `format` | `provenance` | `row-provenance` | `veriformis.dataset-serializer.provenance` | `1` |
| `validate` | `snapshot` | `dataset-snapshot` | `veriformis.dataset-validation.snapshot` | `1` |
| `validate` | `report` | `dataset-validation-report` | `veriformis.dataset-validation.report` | `1` |
| `seal` | `manifest` | `finished-bundle-manifest` | `veriformis.bundle.manifest` | `1` |
| `seal` | `attestation` | `finished-bundle-attestation` | `veriformis.bundle.attestation` | `1` |

These are new artifact kinds. Do not silently reuse legacy
`formatted-records`, `records-metadata`, or the unbound M1 validation report.
Every stage config and artifact binds the same `plan_id`.

## Ordered implementation

### 1. Pin contracts, constants, and known failures

1. Add Group 3 contract, schema, stage-output, gate, reason, verification-grade,
   and error registries.
2. Add strict factory and persisted-loader tests for every new model.
3. Convert the current known-gap tests into finished-pipeline acceptance tests.
4. Add negative tests for fabricated rows, stale validation, empty partitions,
   manifest mutation, undeclared files, and unsafe paths before changing
   behavior.
5. Preserve historical M1 and Group 2 contracts through explicit legacy APIs or
   version dispatch. Never weaken them to make new tests pass.

**Exit:** Tests and public constants agree with the contract, and every known
failure is pinned against the correct Group 3 boundary.

### 2. Introduce workspace revision schema v3

1. Add `curate` and `split` to the v3 stage set and install the exact dependency
   graph.
2. Add fixed v3 output schemas, source-scope checks, producer checks, and
   semantic commit validation for curate, split, format, and validate.
3. Implement one explicit v2 to v3 migration.
4. Preserve parse, clean, chunk, and construct states and artifacts exactly.
5. Add curate and split as absent.
6. Reset legacy format, validate, and seal to absent. Remove their artifacts
   only from the new active registry, never from object storage or history.
7. Generalize migration validation without weakening the v1 to v2 contract.
8. Test interruption, stale expected heads, idempotence, corrupt histories,
   active and failed legacy validation, and exact parent transitions.

**Exit:** Migration atomically exposes one valid v3 head or leaves v2 current.
No legacy chunk row or saved gate flag becomes a Group 3 artifact.

### 3. Implement finished-dataset contracts

1. Implement strict immutable models for the complete finished plan, curation
   values, coverage ledger, leakage groups, split result, product rows, one
   provenance stream, row set, snapshot, validation, manifest, attestation, and
   verification result.
2. Recompute every identity and cross-reference at public boundaries.
3. Reject duplicate JSON keys, floats, non-finite numbers, noncanonical bytes,
   unknown fields, wrong types, duplicate identities, and unsupported versions.
4. Bind a plan to one exact recipe and result. Require result-to-recipe agreement
   and fresh construction replay.
5. Keep audit time, revision IDs, host paths, and randomness outside portable
   identities.

**Exit:** Identical semantic inputs reproduce every Group 3 model identity, and
unchecked copies or `model_construct` values fail public-boundary revalidation.

### 4. Implement deterministic curation

1. Compute target length from the objective's exact target tuple and apply the
   non-negative integer `minimum_target_characters`.
2. Build source-scoped objective-specific exact context and target tuples.
3. Quarantine every member of a context class with distinct targets.
4. Compute exact dedup fingerprints from objective ID and ordered field
   `(name, value)` pairs.
5. Keep the minimum record ID per duplicate class and explicitly exclude every
   other member.
6. Apply mode `none` or a positive integer primary-source cap. Use the first
   canonical source ID and retain records in lexicographic record-ID order.
7. Emit exactly one decision per Group 2 dataset record.
8. Build selected-source coverage, including multi-source candidate and
   contribution counts and exact blocker codes.
9. Replay the complete curation result before commit.

Pin the policy literals to
`keep-lexicographically-smallest-record-id`,
`quarantine-all-distinct-targets`, and `disabled`. Pin the decision reasons to
`quality-passed`, `target-too-short`, `exact-duplicate`, `conflicting-target`,
and `primary-source-cap`. Persist every applicable
`no-constructed-candidates`, `no-dataset-records`, and
`no-included-contribution` blocker. Blockers remain auditable in a curation
result, but validation and seal fail closed while any remains.

**Exit:** No record disappears silently. Reordered inputs produce the same
decisions, representatives, reasons, counts, and result identity.

### 5. Implement leakage-safe splitting

1. Admit only curation-included record IDs.
2. Give each included representative the union of source IDs and raw digests
   from its complete exact-dedup family, including excluded duplicates.
3. Build graph edges for shared source IDs, equal raw digests, multi-source
   joins, and inherited dedup-family relations.
4. Compute complete transitive groups and derive IDs from exact canonical
   membership and leakage bases.
5. Order groups by `SHA256(policy_id + seed + group_id)`, then `group_id`.
6. Compute
   `min(N-1, max(1, (N * evaluation_ratio_ppm + 500000) // 1000000))`.
7. Choose the non-empty proper prefix whose cumulative record count is closest
   to that target. Break ties with the shorter prefix. Assign it to evaluation
   and assign the remainder to train.
8. Raise `split-invalid` for fewer than two groups when evaluation is required.
   When it is explicitly optional, keep a sole group in train.
9. Emit one assignment per included record, requested and realized counts, and
   one assignment digest.
10. Reject missing, duplicate, unknown, excluded, quarantined, or
    cross-partition membership.
11. Replay assignment from reordered inputs before commit.

**Exit:** No leakage-connected record family crosses partitions. Exact bounded
prefix replay reproduces membership and the assignment digest without a subset
search.

### 6. Replace legacy formatting with record lowering

1. Make format depend on construct, curation, and split outputs.
2. Load the target row schema from the recipe. Remove authoritative legacy
   `completion`, `instruction`, and `chat` format selection.
3. Apply the contract's exact objective context and target map.
4. Require one exact plan instruction only for `instruction_output`. Set it to
   null for `text`, `prompt_completion`, and `messages`.
5. Emit exactly one payload row and one provenance row per included record.
6. Write separate train and evaluation payload files containing only Aptus
   schema keys.
7. For `messages`, emit exact source context as the user turn and exact target
   as the final assistant turn. Add no generic or instruction prefix.
8. Write one combined aligned provenance stream with complete record, evidence,
   curation, group, assignment, partition, partition ordinal, and
   payload-digest binding.
9. Order each partition by record ID. Order the combined row set and provenance
   as train, then evaluation, and derive one row-set identity over exact
   sequences and bytes.
10. Keep model-family rendering on an unsealed preview path only.

**Exit:** Serializers cannot invent a target, instruction, review state, split,
or source claim. Every output byte maps back to one unchanged Group 2 record.

### 7. Implement exact snapshot validation

1. Replace the legacy row/chunk `run_gates` boundary with a finished-dataset
   snapshot validator. Preserve the old helper only under an explicitly legacy
   name if compatibility requires it.
2. Build one immutable snapshot from exact active artifacts and planned bundle
   bytes.
3. Run the exact gates `construction-replay`, `record-lifecycle`, `curation`,
   `deduplication`, `quality`, `balance`, `coverage`, `split`, `leakage`,
   `row-binding`, `objective`, `schema`, `encoding`, `masking`,
   `partition-nonempty`, `aptus-row-shape`, and `snapshot` in that order.
   Persist structured findings for every gate.
4. Re-run construction, curation, split, lowering, evidence, encoding, Aptus
   row-shape, combined-provenance alignment, and file binding checks.
5. Persist valid failing reports with failed stage status.
6. Bind gate implementation versions and reject a report from another validator
   version.
7. Test every upstream rerun, post-validation mutation, stale report,
   reordered row, missing provenance, duplicate row, extra row, and altered
   target.

**Exit:** A report proves one exact byte snapshot. A passing Boolean detached
from those bytes has no authority.

### 8. Implement the minimal bundle and atomic seal

1. Define the exact six-file minimal bundle:
   `data/train.jsonl`, `data/evaluation.jsonl`,
   `metadata/row-provenance.jsonl`, `validation.json`, `manifest.json`, and
   `attestation.json`.
2. Normalize and validate every relative path before filesystem access.
3. Build in a private temporary sibling on the target filesystem.
4. Copy already validated bytes. Do not parse and reserialize them during seal.
5. Write a deterministic manifest without UUID, timestamp, absolute path, or
   self-hash in its semantic content.
6. Write co-located `attestation.json` binding the exact manifest SHA-256 and
   content root.
7. Fsync files and directories.
8. Verify the complete temporary bundle with the independent verifier and the
   expected manifest digest.
9. Recheck the expected workspace revision.
10. Promote the directory atomically without overwriting an existing target.
11. Persist the exact manifest and attestation bytes as seal-stage receipts.
12. Return the manifest digest so the caller can retain it outside the bundle.
13. Treat post-promotion directory-sync failure as a visible successful commit
    with a durability warning.

Directory promotion and workspace receipt commit cannot share one filesystem
primitive. If the bundle becomes visible but receipt commit fails, report the
published path and digest with the typed workspace failure. Never report a
false rollback or overwrite the visible bundle during recovery.

**Exit:** Failure before fresh promotion leaves no destination. Success produces
only the exact declared files, and changing any byte invalidates verification.
An exact retry may recover receipts without rewriting the visible bundle.

### 9. Implement independent verification grades

1. Verify the manifest through a strict versioned loader.
2. Walk the actual tree without following links and compare it to the exact
   permitted set.
3. Reject absolute, parent, backslash, Unicode-normalization, case-collision,
   reserved, symlink, hard-link-policy, and special-file violations.
4. Hash opened files and compare path, role, size, media type, and digest.
5. Cross-check payload and provenance counts, ordinals, row digests,
   identities, partitions, snapshot, validation, manifest, and attestation
   binding.
6. Return `self_consistent` without an external anchor.
7. Return `external_digest` only when the caller supplies an expected manifest
   SHA-256 and it matches.
8. Add fresh-process tests that have no workspace access.

**Exit:** Verification never trusts the producer process and never reports more
trust than the supplied evidence proves. Source replay remains a validation
responsibility, not a bundle verification grade.

### 10. Integrate commands without claiming Group 4

1. Add or update current CLI stage commands for plan creation, curate, split,
   format, validate, seal, and verify.
2. Infer the row schema from the bound recipe. Do not accept an independent
   format label that can contradict it.
3. Require explicit instruction text only for `instruction_output`.
4. Surface stable machine errors, failed gates, blocker codes, partition counts,
   snapshot ID, manifest digest, and verification grade.
5. Keep orchestration changes local to current commands. The surface-neutral
   `PipelineService` and thin CLI conversion remain Group 4.

**Exit:** The CLI reaches the same domain operations and canonical outputs as
the direct Python functions without expanding Group 3 into Group 4.

### 11. Close Group 3

1. Run supported raw multi-source fixtures through the complete Group 3 path.
2. Exercise all five objectives and every allowed row schema.
3. Prove deterministic curation, split, row, provenance, snapshot, validation,
   manifest, and bundle identities under input reordering and repeat execution.
4. Remove every Group 3 strict expected failure by making it an ordinary test.
5. Run all contract, migration, workspace, curation, split, serialization,
   validation, bundle, verifier, and end-to-end tests.
6. Update active product documentation only after runtime behavior passes.
7. Record an independent architecture and security review.

**Exit:** Every item in the contract acceptance matrix passes with no unresolved
Critical, High, or Important finding.

**Current state:** Complete. The raw-source demonstration, repository gates,
and independent review satisfy the Group 3 exit contract.

## Acceptance matrix

| Area | Required proof |
| --- | --- |
| Composition | Exact Group 2 recipe and result binding plus fresh replay |
| Versioning | Strict v1 Group 3 schemas and version-aware historical loading |
| Migration | Atomic v2 to v3 conversion and honest retirement of legacy downstream state |
| Curation | Ordered target, source-scoped conflict, dedup, balance, decision, and coverage closure |
| Leakage | Source IDs, raw digests, multi-source joins, and inherited dedup-family relations stay in one transitive group |
| Partitions | One assignment per included record; evaluation is non-empty exactly when required and feasible |
| Serialization | Five objective mappings, four row schemas, one-to-one lowering, and instruction text only for `instruction_output` |
| Provenance | Payload-only rows plus one exact combined evidence stream in train-then-evaluation order |
| Aptus boundary | Row-shape compatibility reported separately from handoff and backend split enforcement |
| Validation | One exact immutable artifact-and-byte snapshot with all required gates |
| Staleness | Every upstream change invalidates validation and prevents default current seal |
| Seal | Temporary verified build, fsync, atomic promotion, no overwrite, and failure recovery |
| Verification | Closed file set, path safety, digests, attestation, and exact `self_consistent` or `external_digest` grade |
| Determinism | Stable IDs and bytes independent of input order, clock, path, and process state |
| Product doctrine | Supported raw sources reach the complete verified seal without a cleaned-text shortcut |

## Required tests

- Strict schema, identity, Unicode, canonical JSON, duplicate-key, float,
  unsafe-copy, and cross-reference tests for every model.
- Migration tests for every v2 stage-state combination and interruption point.
- Minimum-target boundary tests for all five objective target tuples.
- Conflict-before-dedup tests, including duplicate conflicting targets and
  excluded short targets that cannot poison a context class. Identical context
  from unrelated source scopes MUST NOT conflict.
- Exact dedup representative tests under reordered records and multi-source
  lineage.
- Primary-source cap tests for ties, multi-source records, null cap, invalid cap,
  and mode mismatch.
- Selected-source coverage tests for no candidates, no records, all excluded,
  all quarantined, multi-source contributions, and exact blocker order.
- Split tests for transitive source bridges, equal raw digests, multi-source
  joins, inherited excluded-duplicate sources, one group, uneven sizes, exact
  rounded targets, prefix ties, tampered membership, and optional evaluation.
- Objective-to-row matrix tests for all allowed combinations and every invalid
  combination.
- Exact instruction and messages composition tests. Instructions appear only
  in `instruction_output`; messages contain exact context and target without a
  generic prefix.
- Payload and provenance count, ordinal, digest, identity, evidence, curation,
  group, partition, missing, extra, duplicate, and reorder tests.
- Aptus row-precedence, non-empty target, final-assistant, plain-text MLX
  limitation, and non-claiming split-capability tests.
- Validation replay, all-gates-report, stale version, post-validation mutation,
  source evidence tamper, row tamper, and file-plan tamper tests.
- Seal failure-injection tests before every promotion phase and after visible
  promotion directory sync.
- Verification tests for extra and missing files, manifest or attestation
  mutation, traversal,
  absolute paths, backslashes, symlinks, hard links, case collisions, Unicode
  path collisions, devices, FIFOs, unexpected directories, and expected digest
  mismatch.
- Fresh-process, repeated-run, input-reordering, and raw-source end-to-end tests.

## Stable errors and reasons

Implementation MUST use the exact error and curation-reason registries in the
contract. New surfaces translate those typed values. They do not replace them
with command-specific strings.

Validation findings remain report data. Curation exclusion and quarantine
remain lifecycle data. Only malformed contracts, failed required gates, stale
state, unsafe bundles, and publication failures raise the corresponding typed
errors.

## Exact deferrals

- Step 17: surface-neutral `PipelineService` orchestration.
- Step 18: thin CLI conversion.
- Step 19: the dual-objective M1.1 API and CLI acceptance gate.
- Step 20: PDF, HTML, CSV, JSON, and JSONL input completion.
- Step 21: expanded deterministic recipes, quality policies, and balancing.
- Step 22: MCP automation.
- Step 23: versioned Aptus bundle handoff and backend partition enforcement.
- Step 24: SwiftUI workbench.
- Step 25: separately approved governed model-assisted construction.

## Required verification

```text
uv lock --check
uv run ruff check src tests
uv run pytest -q
git diff --check
```

Focused checks MUST cover contract tests, workspace v3 migration, curation,
coverage, leakage splitting, serializers, Aptus row conformance, exact snapshot
validation, atomic seal, path safety, external digest handling, verification
grades, known gaps, and the raw-source end-to-end acceptance path.

The final full repository test result is `606 passed`. The independent review
outcome is recorded in Section 11 and in the linked code-review report.

## Related documentation

- [Finished Dataset Contract v1](../../../docs/contracts/finished-dataset-v1.md)
- [Dataset Construction Contract v1](../../../docs/contracts/dataset-construction-v1.md)
- [Integrity Contract v1](../../../docs/contracts/integrity-v1.md)
- [Authoritative build roadmap](../../../docs/plans/2026-07-29-veriformis-roadmap.md)
- [Architecture](../../../docs/architecture.md)
- [Current implementation status](../../../docs/current-status.md)
- [Group 3 architecture and security review](group-3-finished-dataset-code-review.md)
