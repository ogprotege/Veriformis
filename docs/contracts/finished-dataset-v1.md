# Finished Dataset Contract v1

**Contract ID:** `veriformis.finished-dataset`

**Contract version:** `1`

**Execution profile:** `offline-deterministic-v1`

**Workspace layout schema:** `1`

**Workspace revision schema:** `3`

**Roadmap scope:** Steps 11 through 16

**Implementation status:** Implemented. The Group 3 exit gate in this document
passed on 2026-07-29.

**Last reviewed:** 2026-08-11 (active implementation reconciliation)

**Next review:** Any finished-dataset schema or Group 4 service-boundary change

## Purpose

This contract defines how Veriformis completes the work begun by Integrity
Contract v1 and Dataset Construction Contract v1. Veriformis takes heterogeneous
raw source material through faithful recovery, replayable cleaning, truthful
dataset construction, explicit curation, leakage-safe splitting,
objective-preserving serialization, exact validation, and a verified seal.

The cleaned corpus is an accountable intermediate compiler state. It becomes a
training target only when a `full_text` recipe selects it. The product boundary
is the finished, curated, split, validated, and sealed dataset.

This contract governs:

- composition of immutable Group 2 recipes, construction results, and records;
- deterministic quality filtering, conflict quarantine, exact deduplication,
  coverage accounting, and optional balancing;
- authoritative train and evaluation assignments over leakage groups;
- one-to-one lowering of included `DatasetRecord` values into product rows;
- payload-only trainer-facing JSONL in one declared product row schema and one
  aligned provenance stream;
- validation of one exact dataset snapshot;
- atomic publication of one normalized closed file set; and
- independent verification with explicit verification grades.

## Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` are normative terms.
Persisted values and executable checks control behavior. Explanatory prose does
not permit a weaker interpretation.

## Product boundary

The governed flow is:

```text
captured raw source
  -> canonical recovery and parser diagnostics
  -> replayable cleaning and source evidence
  -> DatasetRecipe v1 and ConstructionResult v1
  -> immutable DatasetRecord values
  -> FinishedDatasetPlan v1
  -> deterministic curation and coverage ledger
  -> leakage groups and authoritative train/evaluation assignment
  -> objective-preserving product rows and aligned provenance
  -> exact dataset snapshot validation
  -> atomic closed-set seal and independent verification
```

Veriformis owns every stage in this flow. Any trainer begins with a finished
dataset and does not replace Veriformis curation, balancing, split assignment,
or validation. Aptus is an optional consumer integration implemented through a
versioned sibling descriptor; it is not part of the canonical bundle.

## Composition with Group 2

Group 3 MUST preserve these Group 2 contracts unchanged:

- `veriformis.dataset-recipe/v1`;
- `veriformis.construction-result/v1`; and
- `veriformis.dataset-record/v1`.

A `FinishedDatasetPlan` composes one exact `recipe_id` and one exact
`construction_result_id`. The result MUST name that recipe, load through its
strict v1 loader, and match a fresh construction replay before curation begins.

Group 3 MUST NOT:

- reinterpret either Group 2 `deferred` policy literal as an executed policy;
- add curation or split fields to a `DatasetRecord`;
- mutate a record, its evidence, or its identity;
- promote a rejected or pending Group 2 candidate;
- use chunk text in place of the accepted records; or
- describe a `ConstructionResult` alone as a finished dataset.

The finished-dataset plan supplies the executable policies that Group 2
deliberately deferred. Changing any plan policy changes `plan_id` without
changing the Group 2 recipe or record identities.

## Contract and schema identifiers

The following identifiers are exact:

| Persisted value | Schema identifier |
| --- | --- |
| Finished dataset plan | `veriformis.finished-dataset-plan/v1` |
| Curation policy | `veriformis.curation-policy/v1` |
| Quality finding | `veriformis.quality-finding/v1` |
| Curation decision | `veriformis.curation-decision/v1` |
| Coverage ledger entry | `veriformis.coverage-ledger-entry/v1` |
| Coverage ledger | `veriformis.coverage-ledger/v1` |
| Curation result | `veriformis.curation-result/v1` |
| Exact record fingerprint payload | `veriformis.exact-record-fingerprint/v1` |
| Split policy | `veriformis.split-policy/v1` |
| Leakage group | `veriformis.leakage-group/v1` |
| Record assignment | `veriformis.record-assignment/v1` |
| Split result | `veriformis.split-result/v1` |
| Serialization plan | `veriformis.serialization-plan/v1` |
| Product row | `veriformis.product-row/v1` |
| Row provenance | `veriformis.row-provenance/v1` |
| Row set | `veriformis.row-set/v1` |
| Snapshot artifact binding | `veriformis.snapshot-artifact-binding/v1` |
| Snapshot file binding | `veriformis.snapshot-file-binding/v1` |
| Snapshot validator binding | `veriformis.snapshot-validator-binding/v1` |
| Dataset snapshot | `veriformis.dataset-snapshot/v1` |
| Dataset gate result | `veriformis.dataset-gate-result/v1` |
| Dataset validation report | `veriformis.dataset-validation-report/v1` |
| Bundle file | `veriformis.finished-bundle-file/v1` |
| Finished bundle manifest | `veriformis.finished-bundle-manifest/v1` |
| Bundle attestation | `veriformis.bundle-attestation/v1` |
| Bundle verification | `veriformis.bundle-verification/v1` |

Every persisted model is strict, frozen, and versioned. Loaders MUST reject
missing fields, unknown fields, duplicate JSON keys, wrong primitive types,
unsupported versions, non-finite numbers, floating-point numbers, duplicate
identities, noncanonical bytes, and inconsistent references.

## Identity and canonical serialization

All semantic identities use the Group 1 domain-separated, content-derived
identity substrate. An object's own ID is excluded from its identity payload.
Every public loader recomputes the complete identity before accepting the
object.

Portable identities MUST NOT contain clocks, random values, absolute host
paths, process state, or workspace revision IDs. Audit revision IDs MAY appear
in a non-semantic local receipt, but they cannot change a portable dataset,
assignment, snapshot, or bundle identity.

Unicode field values remain exact. No target, context, instruction, or evidence
value is trimmed, normalized, case-folded, or otherwise rewritten implicitly.
Locator normalization remains limited to locator contracts. Character counts
use Unicode code points in the exact Python string value. JSON uses the
repository canonical writer. JSONL uses UTF-8 without a byte-order mark, one
canonical JSON object per line, LF line endings, and no blank lines. Every
non-empty JSONL file ends in one LF. A permitted zero-record evaluation file is
exactly zero bytes.

## FinishedDatasetPlan

A finished `FinishedDatasetPlan` contains exactly:

- `schema_version` and `plan_id`;
- `recipe_id` and `construction_result_id`;
- one complete `curation_policy`;
- one complete `split_policy`;
- one complete `serialization_plan`;
- the exact required validation-gate registry;
- the exact required partitions, fixed to `train` then `evaluation`; and
- the bundle retention profile, fixed to `minimal-v1`.

The plan's recipe and construction result are external immutable inputs, not
embedded mutable copies. Their complete artifact IDs and SHA-256 digests are
bound later by the dataset snapshot.

The complete plan MUST be persisted as the curate stage's `plan` output before
curation executes. `CurationPolicy`, `SplitPolicy`, and `SerializationPlan` stay
nested in it. They are not duplicated as standalone stage outputs. The
curation, split, format, validate, and seal artifacts MUST bind the same
`plan_id`.

The serialization row schema MUST equal `DatasetRecipe.target_row_schema`.
Selected source scope comes only from `DatasetRecipe.source_ids`. No unrelated
workspace source may enter curation, coverage, output rows, provenance, or the
bundle manifest.

## Curation and quality

`CurationPolicy` contains exactly `schema_version`, `policy_id`,
`minimum_target_characters`, `exact_duplicate_policy`, `conflict_policy`,
`near_duplicate_policy`, `balance_mode`, and
`maximum_records_per_primary_source`.

### Ordered policy

Curation MUST execute these operations in this exact order:

1. Reload and replay the Group 2 recipe, result, decisions, records, and field
   evidence.
2. Exclude records whose target character count is below the declared minimum.
3. Detect objective-specific exact-context conflicts among the records still
   eligible, then quarantine every member of each conflict class.
4. Deduplicate the remaining eligible records by exact semantic fingerprint.
5. Apply the declared balance mode to the remaining representatives.
6. Produce one decision per input `DatasetRecord` and close the selected-source
   coverage ledger.

A record removed by an earlier operation does not participate in a later one.
In particular, a target already excluded for minimum length cannot create a
conflict that quarantines another record. Conflict quarantine occurs before
deduplication, so duplicate copies cannot hide a contradictory target.

### Target character filter

`minimum_target_characters` is a non-negative integer. Target fields are:

| Objective | Target field tuple |
| --- | --- |
| `full_text` | `text` |
| `continuation` | `completion` |
| `section_reconstruction` | `section` |
| `before_after_transformation` | `after` |
| `structured_field` | `fields` |

The target character count is the sum of the Unicode code-point counts of the
exact ordered target strings. A count below the threshold produces status
`excluded` with reason `target-too-short` and one matching `QualityFinding`.

### Exact conflicts

Conflict detection groups eligible records by `objective_id`, the exact ordered
`source_ids` scope, and the exact ordered objective context tuple:

| Objective | Context tuple | Target tuple |
| --- | --- | --- |
| `full_text` | `text` | `text` |
| `continuation` | `prompt` | `completion` |
| `section_reconstruction` | `heading` | `section` |
| `before_after_transformation` | `before` | `after` |
| `structured_field` | `input` | `fields` |

A conflict exists when one context class contains more than one distinct exact
target tuple. Every record in that class receives status `quarantined` with
reason `conflicting-target`. No member becomes a dedup representative
or split input. The full-text context equals its target, so full-text duplicates
are deduplicated and do not create false conflicts.

Identical prompts, headings, inputs, or before-values from different exact
source scopes do not form a conflict class. This prevents ordinary repeated
language in unrelated sources from causing false quarantine.

This is deterministic exact conflict detection. It does not claim semantic
contradiction detection across paraphrases or inferred meanings.

### Exact deduplication

The exact dedup fingerprint binds:

- `schema_version`, fixed to `veriformis.exact-record-fingerprint/v1`;
- `objective_id`; and
- every ordered record field as its exact `(name, value)` pair.

Evidence and lineage do not enter the fingerprint. They remain attached to each
audited record. Within each duplicate class, the lexicographically smallest
`record_id` is the representative. Other members receive status `excluded` and
reason `exact-duplicate`. The representative remains eligible.

### Balance policy

The closed v1 balance modes are:

- `none`; or
- `primary_source_cap`.

The exact policy literals are:

- `exact_duplicate_policy=keep-lexicographically-smallest-record-id`;
- `conflict_policy=quarantine-all-distinct-targets`; and
- `near_duplicate_policy=disabled`.

Mode `none` requires `maximum_records_per_primary_source=null`. Mode
`primary_source_cap` requires a positive integer
`maximum_records_per_primary_source`. A record's primary source is the first ID
in its already canonical, non-empty `source_ids` tuple. For each primary
source, records are ordered lexicographically by `record_id`; the first
declared maximum remain included. Later records receive status `excluded` with
reason `primary-source-cap`.

The cap does not erase multi-source provenance. Coverage counts an included
multi-source record as a contribution for every selected source named by that
record, although balance charges it only to its canonical primary source.

### Curation closure and coverage

The curation result contains exactly one ordered `CurationDecision` for every
`DatasetRecord` in the construction result. Valid statuses are `included`,
`excluded`, and `quarantined`. Every decision contains exactly one reason code.
Included records use `quality-passed`. Excluded records use
`target-too-short`, `exact-duplicate`, or `primary-source-cap`. Quarantined
records use `conflicting-target`. Every non-included decision binds one matching
`QualityFinding`.

`CurationResult` contains exactly `schema_version`, `result_id`, `plan_id`,
`recipe_id`, `construction_result_id`, `policy_id`, `input_record_ids`,
`decisions`, `findings`, `included_record_ids`, and `coverage_ledger`.

For every selected recipe source, the coverage ledger records these exact
integer fields:

- `candidate_count`, for all construction candidates whose `source_ids` contain
  the source;
- `record_count`, for all pre-curation records whose `source_ids` contain the
  source;
- `included_count`, `excluded_count`, and `quarantined_count`, counted once for
  every named source according to the record's decision; and
- `primary_included_count`, for included records whose canonical first source
  is this source.

Multi-source values contribute once to each named source's applicable counts.
The blocker registry is exactly `no-constructed-candidates`,
`no-dataset-records`, and `no-included-contribution`. Every applicable blocker
is recorded in lexicographic order, so a source with no candidates carries all
resulting zero-stage blockers. Curation may persist a result with blockers for
audit. The coverage validation gate MUST fail, and seal MUST remain unavailable,
while any blocker exists.

## Leakage-safe splitting

Only curation decisions with status `included` become emitted vertices.
Excluded and quarantined records receive no assignment. Leakage grouping MUST
nevertheless retain every relation that can reveal shared origin:

- shared source IDs;
- equal raw-source SHA-256 values from selected `SourceDescriptor` values;
- multi-source records, which join every source and raw digest they name; and
- exact dedup families, including the source IDs and raw digests of excluded
  duplicates.

For an included dedup representative, its leakage basis is the union of source
IDs and raw-source digests across the complete exact-duplicate family. Thus an
excluded duplicate can still connect its retained representative to another
included record from the duplicate's source. Included records share an
undirected edge when their leakage bases intersect. A `LeakageGroup` is the
complete transitive connected component under those edges.

Each group contains sorted unique included record IDs and its complete leakage
basis. Its identity is derived from that exact membership. Every included
record belongs to exactly one group and receives exactly one assignment to
`train` or `evaluation`. No group may cross partitions.

The split policy contains an integer `evaluation_ratio_ppm` in `1..999999`, a
non-empty deterministic `seed`, and an exact `evaluation_required` Boolean.
For `N` included records, the rounded and clamped target is:

```text
min(N - 1, max(1, (N * evaluation_ratio_ppm + 500000) // 1000000))
```

Groups are ordered by
`SHA256(UTF-8(policy_id + seed + group_id))`, then by `group_id`. Among every
non-empty proper prefix, the algorithm chooses the prefix whose cumulative
record count is closest to the target. A tie chooses the shorter prefix. That
prefix becomes `evaluation`; all remaining groups become `train`. This is a
bounded deterministic prefix selection, not a subset search.

When `evaluation_required=true`, fewer than two leakage groups raises
`split-invalid`. When `evaluation_required=false` and fewer than two groups
exist, all included records remain in `train` and `evaluation` is empty. With
two or more groups, the same prefix algorithm applies. The split result records
the requested and realized counts, sorted group membership, one ordered record
assignment per included record, and an assignment digest.

## Construction-aware serialization

Serialization consumes only:

- the exact Group 2 recipe and result;
- curation-included records;
- the authoritative split result; and
- the exact serialization plan.

It MUST NOT consume chunks as substitute rows, create a training objective,
change target text, infer an instruction, reopen curation, or resplit records.
Version 1 is one record to one product row. Fan-out and row merging require a
new contract version.

### Objective field mapping

The exact context and target mapping is:

| Objective | Context field | Target field |
| --- | --- | --- |
| `full_text` | none | `text` |
| `continuation` | `prompt` | `completion` |
| `section_reconstruction` | `heading` | `section` |
| `before_after_transformation` | `before` | `after` |
| `structured_field` | `input` | `fields` |

### Product row schemas

`text` is valid only for `full_text` and emits exactly:

```json
{"text":"<exact target>"}
```

`prompt_completion` emits exactly:

```json
{"prompt":"<exact context>","completion":"<exact target>"}
```

`instruction_output` requires one non-empty exact `instruction_text` in the
serialization plan and emits exactly:

```json
{"instruction":"<plan instruction>","input":"<exact context>","output":"<exact target>"}
```

`messages` emits exactly a two-turn conversation. The user content is the exact
source-derived context and the assistant content is the exact target:

```json
{"messages":[{"role":"user","content":"<exact context>"},{"role":"assistant","content":"<exact target>"}]}
```

The serialization plan MUST set `instruction_text` to null for `text` and
`prompt_completion` and `messages`. It MUST supply a non-empty value only for
`instruction_output`. That instruction is an explicit, content-addressed plan
literal. The CLI requires it when the recipe selects `instruction_output`. It
is not source evidence and is never represented as source-derived target text.

Rendered tokenizer or model-family chat text is not an authoritative product
row. It MAY be produced as an unsealed preview or conformance display.

### Payload and provenance separation

Trainer-facing payload JSONL contains only the exact declared schema keys
above. It contains no
Veriformis metadata, split group, record ID, evidence object, validation flag,
or competing row-schema key.

There is one canonical provenance artifact for the complete row set. Each line
contains `partition` and its zero-based partition ordinal, plus the row ID,
payload SHA-256, record, recipe, objective, pass, source, chunk, transform,
evidence, curation, leakage group, assignment, split, and plan identities. A
mismatch in count, ordinal, row ID, payload digest, record binding, or partition
fails validation.

Rows within each partition are ordered lexicographically by `record_id`. The
combined row-set and provenance order is all `train` rows followed by all
`evaluation` rows. The row-set identity binds both ordered payload sequences
and this one ordered provenance sequence.

### Generic row-shape boundary and optional Aptus compatibility

Row-shape validation pins these generic product facts:

- `text` is a non-empty full-supervision sequence;
- prompt and instruction shapes preserve a non-empty supervised target;
- `messages` ends in a non-empty assistant turn; and
- a row contains exactly one recognized top-level schema.

The registered gate name `aptus-row-shape` is a legacy contract ID retained for
version compatibility. The gate checks the generic declared product-row shape;
it does not require Aptus, prove handoff consumption, or establish backend
partition enforcement. The optional Aptus handoff contract separately reports
backend limitations; its current MLX capability profile rejects plain `text`
rows.

## Exact dataset validation

Validation operates on one immutable `DatasetSnapshot`. The snapshot binds the
exact schema and artifact IDs, SHA-256 digests, source scope, plan, recipe,
construction result, curation result, split result, row set, partition payload
bytes, provenance bytes, canonical file paths, and validator versions intended
for sealing.

The required v1 gates run in this order and all report:

1. `construction-replay`;
2. `record-lifecycle`;
3. `curation`;
4. `deduplication`;
5. `quality`;
6. `balance`;
7. `coverage`;
8. `split`;
9. `leakage`;
10. `row-binding`;
11. `objective`;
12. `schema`;
13. `encoding`;
14. `masking`;
15. `partition-nonempty`;
16. `aptus-row-shape` (legacy ID; generic declared row-shape validation); and
17. `snapshot`.

Validation MUST prove:

- the Group 2 result matches exact replay;
- every record has exactly one valid curation decision;
- curation order, source-scoped conflicts, fingerprints, representatives, caps,
  and counts reproduce exactly;
- coverage includes every selected source and every observed omission, and no
  coverage blocker remains;
- each included record appears once in one leakage group, one partition, one
  payload line, and one aligned provenance line;
- no excluded or quarantined record appears in a partition;
- `train` is non-empty, and `evaluation` is non-empty when the split policy
  requires it;
- source IDs, equal raw-source digests, multi-source joins, and inherited exact
  dedup-family relations never cross partitions;
- every row is the exact lowering of its unchanged record fields;
- every target field resolves through its original evidence;
- payload and provenance files use canonical UTF-8 JSONL bytes;
- current declared product row-shape requirements pass; and
- all snapshot artifact and file digests match the exact bytes being sealed.

A valid but failing report is persisted with failed status so every finding
remains inspectable. It cannot satisfy the seal dependency. An unreadable
critical input produces a failed load finding and explicit blocked results for
dependent gates rather than false passes.

Validation timestamps and workspace revision IDs do not enter the portable
snapshot or validation identity. A local audit receipt MAY record them
separately.

## Stale-snapshot rejection

Workspace revision schema v3 uses this dependency graph:

```text
parse -> clean -> chunk -> construct -> curate -> split -> format -> validate -> seal
```

The exact direct dependencies are:

| Stage | Direct dependencies |
| --- | --- |
| `parse` | none |
| `clean` | `parse` |
| `chunk` | `clean` |
| `construct` | `parse`, `clean`, `chunk` |
| `curate` | `construct` |
| `split` | `construct`, `curate` |
| `format` | `construct`, `curate`, `split` |
| `validate` | `parse`, `clean`, `chunk`, `construct`, `curate`, `split`, `format` |
| `seal` | `parse`, `clean`, `chunk`, `construct`, `curate`, `split`, `format`, `validate` |

The exact revision-v3 output contract is:

| Stage | Output | Artifact kind | Producer | Version |
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

Each stage config and semantic artifact MUST bind the same `plan_id`. Validation
loads the complete composite from `curate.plan` and rejects a partial or
contradictory plan shape.

Rerunning a stage invalidates every descendant. A seal MUST load one verified
revision, rebuild the snapshot identity from its exact artifacts, rerun the
required validator versions, and require byte-semantic equality with the saved
passing report. A changed `HEAD` before final publication fails the default
current-snapshot seal with `workspace-revision-conflict`.

The v2 to v3 migration preserves verified parse, clean, chunk, and construct
facts. It adds absent curate and split stages. It resets legacy format,
validate, and seal states to absent because their Group 1 and Group 2 meanings
do not satisfy this contract. Their artifacts remain immutable and readable in
historical v2 revisions. Migration never silently treats legacy chunk rows or
legacy gate flags as finished-dataset evidence.

## Minimal closed bundle

The `minimal-v1` bundle contains exactly:

```text
name.vfbundle/
├── data/train.jsonl
├── data/evaluation.jsonl
├── metadata/row-provenance.jsonl
├── validation.json
├── manifest.json
└── attestation.json
```

The declared payload mapping is exact:

| Path | Role | Media type | Record count |
| --- | --- | --- | --- |
| `data/train.jsonl` | `training-partition` | `application/jsonl` | Exact train rows |
| `data/evaluation.jsonl` | `evaluation-partition` | `application/jsonl` | Exact evaluation rows |
| `metadata/row-provenance.jsonl` | `row-provenance` | `application/jsonl` | Exact total rows |
| `validation.json` | `dataset-validation-report` | `application/json` | Not applicable |

`FinishedBundleManifest` contains `dataset_snapshot_id`,
`validation_report_id`, the content-root SHA-256, and one sorted `BundleFile`
entry for each declared payload. Each entry binds normalized relative path,
role, media type, byte size, SHA-256, and the exact record count for JSONL.
Plan, recipe, construction, curation, split, and row-set identities are bound
transitively by the snapshot and validation report.

The manifest does not contain a hash of itself. The co-located
`BundleAttestation` in `attestation.json` binds the exact manifest SHA-256,
content root, bundle, snapshot, and validation identities. Because an attacker
can replace both files together, this proves self-consistency rather than
external authenticity. External trust requires the caller to retain and later
supply the expected manifest SHA-256 through a separate trusted channel.

Raw files, canonical source streams, cleaned IR, complete construction values,
and model-family rendered chat are not copied into `minimal-v1`. The snapshot
directly binds the plan, recipe, construction result, curation result, split
result, row set, and emitted files. Those semantic artifacts transitively bind
the broader replay state retained in workspace history. A later retention
profile may include replay material under a new explicit closed file set.

## Atomic seal

Seal MUST:

1. capture and verify one complete passing workspace revision;
2. rebuild and revalidate the exact snapshot;
3. reject an existing destination for fresh publication, or recover only an
   independently verified byte-identical prior publication;
4. create a private temporary sibling on the destination filesystem;
5. copy the four declared, already validated payloads without reserialization;
6. write one canonical deterministic manifest and its co-located attestation;
7. fsync every file and directory;
8. run the independent verifier against the temporary bundle;
9. recheck the expected workspace revision for a default current seal;
10. atomically promote the verified directory;
11. fsync the parent directory, reporting a durability warning rather than a
    false rollback if visibility changed before the final sync failed; and
12. commit the exact manifest and attestation artifacts as seal-stage receipts
    against the expected workspace revision.

For fresh publication, failure before directory promotion leaves no
destination and preserves the previous workspace `HEAD`. Temporary files are
cleaned without deleting an existing destination. The caller-supplied expected
digest is outside the atomic directory boundary. Failure to retain it leaves
only `self_consistent` trust and MUST NOT be reported as external binding.

This atomicity guarantee assumes that the destination parent is an
integrity-controlled namespace. No uncooperative process with the same owner
privileges may rename or replace entries in that parent during seal. Veriformis
uses an exclusive no-replace rename, anchors operations to open directory
descriptors, and cleans only through the verified staging descriptor. If the
staging name changes, cleanup fails closed and may leave a temporary directory.
It never recursively removes the replacement path. A same-owner process that
can mutate the parent can also mutate a published bundle. OS permission
isolation defines that security boundary, while a separately retained manifest
digest detects later bundle substitution.

The exact manifest and attestation bytes are also persisted as the `seal`
stage's `manifest` and `attestation` receipts. Directory promotion and workspace
revision commit are separate atomic operations. If publication becomes visible
but the receipt commit then conflicts or fails, Veriformis MUST report the
visible bundle path and exact manifest digest alongside the typed workspace
failure. It MUST NOT claim that publication rolled back. A retry may attach the
same exact receipts after external-digest verification, complete byte
comparison, and revalidation, but it MUST NOT overwrite the bundle.

## Path-safe independent verification

Manifest file paths MUST be normalized relative POSIX paths. Verification
rejects empty paths, absolute paths, `.` or `..` segments, backslashes,
noncanonical Unicode path forms, duplicate paths, case-fold collisions,
reserved-name collisions, symlinks, hard-link policy violations, sockets,
devices, FIFOs, missing files, unexpected files, and unexpected directories.
All resolved files MUST remain beneath the bundle root.

The verifier reads only bundle bytes plus an optional caller-supplied expected
manifest SHA-256. It does not trust workspace state or saved Boolean validation
flags. From payloads and row provenance it reconstructs product rows, included
curation decisions, exact-record and conflict classes, source and leakage-group
partition consistency, complete snapshot source coverage, and the full row set.
The reconstructed row-set identity and canonical bytes MUST match the snapshot
and its row-set artifact binding. Relations that require omitted raw digests,
excluded records, policies, or workspace artifacts remain validation replay
responsibilities.

Verification reports exactly one of these trust grades after every structural,
path, digest, attestation, record-count, and contract check succeeds:

1. `self_consistent`: the closed file and directory sets, strict manifest,
   co-located attestation, payloads, sizes, digests, record counts, and bound
   snapshot and validation identities agree internally.
2. `external_digest`: every `self_consistent` check passes and a caller-supplied
   expected manifest SHA-256 matches the canonical manifest bytes.

The verifier MUST state the exact grade. It MUST NOT convert a co-located
attestation into an external-trust claim. Source replay is a dataset validation
responsibility and is not a third bundle trust grade in v1.

The optional deterministic `.vfbundle.zip` companion does not change this
closed directory contract. It packages these exact six files only after
external-digest verification and reconstructs this directory for independent
verification. Its byte rules are defined by
[Deterministic Bundle Transport v1](bundle-transport-v1.md).

## Error and rejection semantics

The stable Group 3 error codes are:

- `curation-invalid` for an invalid or unreplayable curation plan, policy,
  finding, decision, ledger, or result;
- `split-invalid` for an invalid leakage group, split policy, assignment, or
  split result;
- `serialization-invalid` for an invalid serialization plan, product row,
  provenance value, row set, or emitted byte sequence;
- `dataset-validation-invalid` for an invalid snapshot, gate result, or
  validation report;
- `gate-failure` for a valid snapshot whose required validation gates fail;
- `seal-invalid` for a safe seal that cannot be prepared, verified, published,
  or receipted as required;
- `bundle-invalid` for a malformed, unsafe, incomplete, altered, or
  insufficiently bound bundle;
- `artifact-digest-mismatch` for bytes that do not match a bound artifact or
  file digest;
- `construction-invalid` for Group 2 replay failure;
- `workspace-revision-conflict` for a changed expected revision;
- `unsupported-workspace-version` when Group 3 is requested against revision
  schema v1 or v2;
- `workspace-corrupt` for an invalid migration, dependency graph, stage output,
  producer, scope, or revision;
- `missing-stage-input` for an absent required stage;
- `stale-stage` for a stale required stage;
- `source-evidence-invalid` for source-evidence replay failure;
- `duplicate-identity` for duplicate durable identities.

Human-readable messages may improve without changing these machine codes.
Curation status and reason codes are data, not exceptions. Validation findings
are report data. A failed required gate prevents seal but preserves the report.

The closed v1 curation reason registry is:

- `conflicting-target`;
- `exact-duplicate`;
- `primary-source-cap`;
- `quality-passed`; and
- `target-too-short`.

The closed quality-finding registry is `conflicting-target`,
`exact-duplicate`, `primary-source-cap`, and `target-too-short`.

## Acceptance matrix

| Area | Required proof |
| --- | --- |
| Composition | `FinishedDatasetPlan` binds one exact replayed Group 2 recipe and result without changing any Group 2 object |
| Curation order | Minimum target, conflict, dedup, balance, and coverage execute in the exact declared order |
| Conflicts | Same objective, exact source scope, and exact context with distinct targets quarantines every class member before dedup |
| Dedup | Exact objective and field fingerprint retains only the minimum record ID and preserves excluded lineage |
| Balance | `none` and deterministic primary-source cap reproduce exact included IDs and reasons |
| Coverage | Every selected source has exact candidate, record, status, contribution, and blocker accounting, including multi-source contribution |
| Split | Source IDs, raw digests, multi-source joins, and inherited dedup-family relations remain whole; deterministic prefix assignment replays exactly |
| Serialization | All five objectives lower one-to-one into every allowed declared schema without invented targets or changed evidence |
| Instructions | Only `instruction_output` uses the exact plan-bound instruction; `messages` uses exact source context and target |
| Product rows | Payload files contain only one declared schema and preserve target-only boundaries where the schema declares them (`aptus-row-shape` remains the legacy gate ID) |
| Provenance | One combined artifact aligns one-to-one by partition ordinal, row identity, payload digest, record, evidence, curation, group, and assignment |
| Validation | One snapshot binds all upstream identities and exact emitted bytes; every required gate reports; failed or stale state cannot seal |
| Migration | Revision v2 to v3 is atomic, preserves Group 2 history, adds curate and split, and retires legacy downstream state without reinterpretation |
| Seal | Failure injection leaves no partial destination; success publishes one exact normalized closed file set |
| Verification | Missing, extra, altered, unsafe, symlinked, or traversal files fail; `self_consistent` and `external_digest` never overstate trust |
| Determinism | Identical semantic inputs reproduce curation, assignment, rows, provenance, snapshot, validation, manifest, and bundle identities |
| Product boundary | Raw sources, not pre-cleaned caller text, reach the finished sealed dataset; no LLM, summary claim, hidden omission, Aptus handoff claim, or backend split claim is introduced |

## Group 3 exit gate

Roadmap Steps 11 through 16 are complete only when every acceptance-matrix row
passes, every current Group 3 known-gap test is an ordinary passing test, the
complete repository checks pass, and an independent review finds no unresolved
Critical, High, or Important contract defect.

The exit demonstration MUST begin with supported raw multi-source material. It
MUST execute capture, recovery, cleaning, construction, curation, splitting,
serialization, validation, sealing, and independent verification. Inspecting a
prebuilt `DatasetRecord`, row file, or cleaned corpus alone does not satisfy the
product acceptance path.

## Historical later deferrals

The list below records the implementation allocation when Group 3 closed. It
is historical, not a statement of current missing behavior: Steps 17 through
24 were subsequently implemented. Consult [current status](../current-status.md)
and the [independent product roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md)
for current maturity and remaining work.

- Steps 17 through 19 added `PipelineService`, a thin CLI adapter, and the
  dual-objective M1.1 acceptance gate.
- Step 20 added the remaining declared source adapters.
- Step 21 expanded deterministic recipes and policy libraries.
- Step 22 added constrained MCP automation.
- Step 23 defined the optional Aptus sibling descriptor, partition
  consumption, masking contract, evidence handoff, and backend capability
  enforcement.
- Step 24 added the SwiftUI workbench.
- Step 25 governs optional model-assisted candidate generation under a separate
  owner-approved contract.

## Related documentation

- [Product contract](../product-contract.md)
- [Integrity Contract v1](integrity-v1.md)
- [Dataset Construction Contract v1](dataset-construction-v1.md)
- [Authoritative independent product roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md)
- [Architecture](../architecture.md)
- [Current implementation status](../current-status.md)
- [Group 3 implementation plan](../../dev/active/group-3-finished-dataset/plan.md)
