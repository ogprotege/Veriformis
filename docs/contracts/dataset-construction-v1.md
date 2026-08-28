# Dataset Construction Contract v1

**Contract ID:** `veriformis.dataset-construction`

**Contract version:** `1`

**Execution profile:** `offline-deterministic-v1`

**Workspace layout schema:** `1`

**Workspace revision schema:** `2`

**Roadmap scope:** Steps 7 through 10

**Implementation status:** Normative Group 2 contract. Current capability claims
require the Group 2 exit gate in this document to pass.

**Last reviewed:** 2026-08-11 (historical deferrals reconciled)

**Next review:** Any construction-schema change or taxonomy compatibility change

## Purpose

This contract defines how Veriformis turns faithfully recovered and cleaned raw
source material into evidence-bearing candidate records and immutable dataset
records. It governs:

- versioned training objectives and dataset recipes;
- ordered deterministic construction passes;
- text-range and IR-field evidence for every constructed field;
- candidate, decision, review, and accepted-record state;
- transactional construction inside a revision workspace; and
- deterministic replay and failure behavior.

The complete product still owns the path through curation, splitting,
formatting, exact validation, and sealing. Group 2 establishes the dataset
construction core. It does not reduce Veriformis to a cleaner, chunker, or row
serializer.

## Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` are normative terms.
Human-readable explanations are not substitutes for the persisted contracts.

## Product boundary

The governed flow is:

```text
captured raw source
  -> canonical recovery and parser diagnostics
  -> replayable cleaning and immutable source evidence
  -> versioned TrainingObjective and DatasetRecipe
  -> ordered ConstructionPass execution
  -> append-only CandidateRecord values
  -> PromotionDecision and optional ReviewEvidence
  -> immutable DatasetRecord values
```

A `full_text` recipe may select cleaned source text as its dataset objective.
That is an explicit construction result, not an implicit handoff of a cleaned
corpus. All other objectives MUST state and prove the source-grounded relation
between their context and target fields.

Group 2 makes no LLM calls, performs no remote generation, and defines no
`summary` objective. Copying source text into a field labeled as a summary is a
semantic error.

## Contract and schema identifiers

The following identifiers are exact:

| Persisted value | Schema identifier |
| --- | --- |
| Training objective | `veriformis.training-objective/v1` |
| Dataset recipe | `veriformis.dataset-recipe/v1` |
| Segmentation policy | `veriformis.segmentation-policy/v1` |
| Construction pass | `veriformis.construction-pass/v1` |
| Source-text field evidence | `veriformis.field-evidence/v1` |
| IR field evidence | `veriformis.ir-field-evidence/v1` |
| Candidate record | `veriformis.candidate-record/v1` |
| Promotion decision | `veriformis.promotion-decision/v1` |
| Review evidence | `veriformis.review-evidence/v1` |
| Dataset record | `veriformis.dataset-record/v1` |
| Construction diagnostic | `veriformis.construction-diagnostic/v1` |
| Construction result | `veriformis.construction-result/v1` |
| Construct-stage configuration | `veriformis.construction-stage/v1` |

Loaders MUST reject missing fields, unknown fields, wrong primitive types,
unsupported schema identifiers, duplicate object identities, and inconsistent
cross-references. Recipe and result artifact byte loaders also reject duplicate
JSON keys, invalid UTF-8, non-finite numbers, floating-point numbers, and any
noncanonical byte representation. An empty list is distinct from a missing
required list.

## Version and serialization rules

Persisted construction values and identity payloads MUST use the exact-string,
deterministic JSON rules established by Integrity Contract v1.

- Unicode string values and object-key sequences are preserved exactly.
- Object keys are emitted in the repository's canonical order.
- Arrays retain their declared semantic order.
- NFC normalization applies only to locator fields whose contracts declare NFC
  equivalence. Construction field values are not normalized implicitly.
- Floating-point values are forbidden in durable identity inputs unless a later
  schema defines an exact canonical representation.
- Timestamps, random values, process IDs, absolute paths, and workspace revision
  IDs MUST NOT enter portable semantic identities.

A schema version changes when fields, field meanings, required ordering, or
validation rules change incompatibly. A constructor version changes whenever
the same declared inputs could produce different semantic output. The recipe
schema version and content-derived recipe identity together version a recipe.
Changing any recipe field changes `recipe_id`.

Historical values remain readable through their versioned loaders. They are
never silently reinterpreted under a newer schema.

## Identity rules

Construction identities use the Group 1 domain-separated identity substrate.
Each persisted identity-bearing object carries its own ID, and its loader
recomputes that ID from the object's semantic payload before accepting it.

| Object | ID kind | Required identity inputs |
| --- | --- | --- |
| Training objective | `obj-v1` | schema, objective version, kind, and exact field specification |
| Dataset recipe | `rcp-v1` | complete canonical recipe except `recipe_id` |
| Construction pass | `pas-v1` | schema, sequence, objective kind, constructor identity and version, and exact sorted parameters |
| IR field evidence | `evd-v1` | source, immutable IR artifact, RFC 6901 pointer, source-value digest, encoding, output digest, and context digest |
| Candidate record | `cand-v1` | ordinal, recipe, objective, pass, source, chunk and transform lineage, and exact ordered fields |
| Promotion decision | `dec-v1` | candidate, status, sorted reason codes, and optional review evidence |
| Review evidence | `rvw-v1` | candidate, reviewer reference, verdict, and rationale |
| Dataset record | `rec-v1` | accepted candidate, decision, recipe, objective, pass, source lineage, and unchanged fields |
| Construction diagnostic | `dia-v1` | code, message, pass, deterministic input key, and canonical source and chunk scope |
| Construction result | `run-v1` | recipe, portable input digest, executed passes, candidates, decisions, records, and diagnostics |

An identity-bearing object's own ID is excluded from its identity payload.
Review evidence is semantic input and therefore changes its decision and result
identities. Duplicate IDs fail with `duplicate-identity`, even when duplicate
payloads are byte-identical.

Dataset-record identity does not include a train or evaluation assignment.
Roadmap Step 12 creates a separate authoritative split assignment so later
partitioning cannot mutate an accepted record.

## TrainingObjective

A `TrainingObjective` states what the model should learn. It is not a row shape,
a serializer name, or a model-family template. Family, container, consumer
profile, and loss policy are separate axes in
[Dataset Taxonomy Contract v1](taxonomy-v1.md).

Each value contains exactly:

- `schema_version`;
- `objective_id`;
- `objective_version`, fixed to integer `1`;
- `kind`, one of the five kinds below; and
- `field_names`, the exact ordered tuple declared below.

Every constructed field is a non-empty string. The table defines its semantic
role. Group 3 serializers later map these construction fields into product row
schemas.

### Objective field semantics

| Objective kind | Required fields and roles | Truth condition |
| --- | --- | --- |
| `full_text` | `text` as target text | The retained sequence is the target. Its complete value resolves through source evidence and declared cleaning derivations. |
| `continuation` | `prompt` as context text; `completion` as target text | Prompt and completion are ordered, non-overlapping segments from one declared source unit. Completion follows the prompt under the recipe's boundary rule. |
| `section_reconstruction` | `heading` as context text; `section` as target text | The heading identifies the exact source section whose body is the target. The constructor does not invent missing prose. |
| `before_after_transformation` | `before` as context text; `after` as target text | `after` is produced by replaying the named deterministic transform over `before`. The transform and all edits are bound into field evidence. |
| `structured_field` | `input` as context text; `fields` as target encoded scalar text | The target is copied from one explicit strict-IR scalar and encoded under the evidence contract. No value is inferred from an absent field. |

Additional payload fields are forbidden unless a new objective schema version
declares them. A constructor MUST reject empty required targets, overlapping or
reversed continuation boundaries, missing section structure, unreplayable
transformations, and unbound structured-field leaves.

`summary` is not an alias for any objective. A later model-assisted generator
cannot be introduced through this contract.

## Product row-schema declarations

`DatasetRecipe.target_row_schema` uses exactly one of:

- `text`;
- `prompt_completion`;
- `instruction_output`; or
- `messages`.

The legacy CLI mode names `completion`, `instruction`, and `chat` are not recipe
row schemas and MUST NOT appear in a `DatasetRecipe`.

Group 2 records the target row-schema declaration and checks that it is a known
product value. Roadmap Steps 13 and 14 define the actual lowering of accepted
records into those row schemas. A Group 2 construction result is not proof that
the declared row serialization has occurred.

`full_text` requires `text`. The other four objectives require one of
`prompt_completion`, `instruction_output`, or `messages`. This compatibility
check does not perform serialization.

## DatasetRecipe

A `DatasetRecipe` binds construction meaning and future dataset policy. It
contains exactly:

- `schema_version` and `recipe_id`;
- one complete `objective` value;
- `source_ids`, sorted, unique, and non-empty;
- `cleaning_config_digest`, binding the cleaned input policy;
- one strict `segmentation` policy;
- `passes`, an ordered non-empty tuple;
- `target_row_schema`;
- `review_policy`, either `none` or `required`;
- `curation_policy`, fixed to `deferred` in Group 2;
- `split_policy`, fixed to `deferred` in Group 2; and
- `required_gates`, exactly `field-evidence` then `objective-shape`.

The segmentation policy contains exactly `schema_version`, `strategy`, `size`,
and `overlap`. Strategy is one current chunking strategy. Size is positive.
Overlap satisfies `0 <= overlap < size`.

`section_reconstruction` requires the `structure` segmentation strategy. Its
constructor groups every contributing structure chunk against exact cleaned-IR
heading boundaries before it can claim a complete section body. Other
objectives may use any declared v1 strategy that satisfies their truth
conditions.

`cleaning_config_digest` MUST equal the configuration digest of the complete
clean stage supplying the selected inputs. It prevents a recipe from replaying
against text cleaned under a different rule configuration.

The literal deferred policy fields keep later ownership visible and identity
bound. They do not claim that curation or splitting ran. New executable policy
values require their owning roadmap step and a schema-version decision.

The recipe's pass sequence is semantic. Reordering passes changes `recipe_id`
even when the individual pass IDs remain unchanged.

## ConstructionPass

A `ConstructionPass` is a pure, deterministic operation over declared cleaned
IR, chunk, transform, and evidence inputs. It contains exactly:

- `schema_version` and `pass_id`;
- `sequence`, positive and contiguous from one within the recipe;
- `objective_kind`, matching the recipe objective;
- `constructor_id` and `constructor_version`;
- `parameters`, sorted by unique parameter name.

Parameter values are strings, booleans, integers, or null. Floating-point and
nested values are forbidden in v1. The constructor ID is the exact built-in ID
for the objective kind. Duplicate, missing, or reordered sequences fail closed.

| Objective kind | Exact constructor ID |
| --- | --- |
| `full_text` | `veriformis.constructor.full-text` |
| `continuation` | `veriformis.constructor.continuation` |
| `section_reconstruction` | `veriformis.constructor.section-reconstruction` |
| `before_after_transformation` | `veriformis.constructor.before-after-transformation` |
| `structured_field` | `veriformis.constructor.structured-field` |

A pass MAY consume an earlier pass result only through an explicit immutable
reference. It MUST NOT mutate a prior candidate, decision, evidence object, or
record. One pass may emit zero, one, or many candidates. Every input unit that
produces no candidate requires a typed construction diagnostic. Silent omission
is forbidden.

Passes cannot read the network, clock, random generator, process environment,
or undeclared filesystem state. Stable output order is by pass sequence, source
logical locator, source ID, input chunk ID, then candidate ordinal.

## RecordField and field evidence

Each objective field is stored as one `RecordField` containing exactly `name`,
non-empty string `value`, and `evidence`. Field names are unique and occur in
the objective's exact declared order. The evidence output digest MUST equal the
SHA-256 of the exact field value.

`evidence` is a discriminated union of `SourceTextEvidence` and
`IRFieldEvidence`. There is no bare provenance flag and no separate mutable
binding object.

### SourceEvidence

The existing `SourceEvidence` contract remains authoritative for visible text
and its replayable cleaning, slicing, and joining derivations. Group 2 reuses it
without weakening its range, region, source, artifact, or digest checks.

Text derived from cleaned content MUST retain the canonical source ranges and
ordered derivations needed to reconstruct its exact value. A chunk ID without
resolvable evidence is not field evidence.

`SourceTextEvidence` contains exactly:

- `schema_version`, fixed to `veriformis.field-evidence/v1`;
- `kind`, fixed to `source_text`; and
- one complete existing `SourceEvidence` value.

### IRFieldEvidence

`IRFieldEvidence` proves a value that exists in strict IR but is not necessarily
present in the canonical visible-text stream. Examples include link targets,
image source references, image titles, and other explicitly represented node
metadata.

Each value contains exactly:

- `schema_version` and `evidence_id`;
- `kind`, fixed to `ir_field`;
- `source_id` and immutable `artifact_id`;
- `artifact_kind`, either `document-ir` or `cleaned-document-ir`;
- `document_sha256`;
- `ir_schema_version`, fixed to `veriformis.ir/v1`;
- an RFC 6901 `json_pointer` resolving one scalar IR field;
- `source_value_digest`;
- `encoding`, either `identity-string` or `json-scalar-v1`;
- `output_sha256`; and
- `context_digest`, binding the constructor context that selected and encoded
  the field.

Verification reloads the identified immutable IR artifact, resolves the JSON
pointer, and recomputes the source-value, encoding, output, and construction-
context digests. A text range cannot stand in for IR-field evidence when the
field value is absent from that range. String leaves preserve their exact value.
Integer and Boolean leaves use canonical JSON scalar text. IR evidence uses the
same `evd` identity domain as source evidence because both are immutable
evidence values with distinct schema and kind discriminators.

The v1 `structured_field` constructor selects only its closed set of supported
strict-IR scalar fields. It constructs a value only through this verification
path. A selected source with no supported scalar, no strict-IR artifact, no
covering chunk, or an empty encoded value receives the corresponding typed
diagnostic. Unsupported or unverified metadata is never inferred or emitted.

| IR node | Supported scalar field |
| --- | --- |
| `Heading` | `level` |
| `CodeBlock` | `language` |
| `Link` | `href`, `title` |
| `Image` | `src`, `title` |
| `Math` | `display` |
| `Citation` | `key`, `locator` |
| `ListBlock` | `ordered` |
| `ListItem` | `checked` |
| `Table` | each scalar member of `alignments` |

Optional object fields produce a candidate only when the strict IR contains a
non-empty scalar value. A present list member, including JSON `null`, is an
explicit selected scalar and must be emitted or diagnosed. Changing this field
set or its encoding requires a constructor-version and contract-version
decision.

## Record lifecycle

Lifecycle objects are append-only. A status change creates a new decision or
record object. It never mutates the candidate.

### CandidateRecord

A `CandidateRecord` contains exactly:

- `schema_version` and `candidate_id`;
- positive `ordinal`;
- `recipe_id`, `objective_id`, and `pass_id`;
- `source_ids`, sorted and unique;
- non-empty sorted unique `chunk_ids`;
- sorted unique `transform_ids`, which may be empty; and
- `fields`, in the objective's exact field order.

Candidate construction validates objective fields and evidence but does not
claim later curation, split, formatting, validation, or seal completion.

### PromotionDecision

A decision contains exactly:

- `schema_version` and `decision_id`;
- `candidate_id`;
- `status`, one of `accepted`, `rejected`, or `pending_review`;
- sorted, unique, non-empty `reason_codes`; and
- optional embedded `review` evidence.

`accepted` requires the two Group 2 construction gates to pass. `rejected` is a
normal auditable outcome, not a transaction failure. `pending_review` carries
no completed review and prevents promotion.

### ReviewEvidence

Review evidence contains exactly:

- `schema_version` and `review_id`;
- `candidate_id`;
- an opaque local `reviewer_id`;
- `verdict`, either `accepted` or `rejected`; and
- non-empty `rationale`.

Review evidence never changes candidate identity. A required-review recipe may
promote only with matching accepted review evidence. A no-review recipe may
promote when its declared deterministic gates pass. Reviewer identifiers and
rationales MUST NOT contain credentials or unnecessary private source content.
The v1 reviewer identifier is an unauthenticated local attestation, not a
cryptographic signature or proof of reviewer identity.

### DatasetRecord

Promotion creates a new immutable `DatasetRecord`. It contains exactly:

- `schema_version` and `record_id`;
- `candidate_id` and accepting `decision_id`;
- `recipe_id`, `objective_id`, and `pass_id`;
- unchanged `source_ids`, `chunk_ids`, and `transform_ids`; and
- the unchanged candidate `fields`.

Promotion cannot rewrite record fields, evidence, or lineage. Any proposed
repair creates a new candidate and decision. A DatasetRecord is accepted under
the recipe's currently executable construction policy. It is not yet curated,
split, serialized, exactly validated, or sealed.

When later recipes require Group 3 policies, promotion MUST wait for those
policies rather than mutating an already accepted record.

## ConstructionResult

`ConstructionResult` is the complete semantic output of one construct-stage
execution. It contains exactly:

- `schema_version` and `result_id`;
- `recipe_id`;
- `input_digest`, binding the portable declared construction inputs;
- ordered non-empty `executed_pass_ids`;
- ordered `candidates`;
- exactly one ordered `decisions` entry per candidate;
- `records`, exactly matching candidates with accepted decisions; and
- ordered `diagnostics`.

Collections are present even when empty. All referenced identities resolve
within the result or through immutable workspace inputs. The result must be
self-consistent before it becomes visible through `HEAD`. Each diagnostic has a
deterministic `dia` identity and binds its pass plus canonical source and chunk
scope.

A bare result loader proves only strict structure, nested identities, and
internal cross-references. Contextual truth requires
`validate_construction_result(recipe, inputs, result)`, which replays the exact
recipe over the declared construction inputs and requires semantic equality.

## Transactional construct stage

Workspace revision schema v2 adds `construct` after `chunk`. Construct depends
on the current complete `parse`, `clean`, and `chunk` states. Any change to
those upstream states invalidates construct.

Group 2 does not make legacy `format`, `validate`, or `seal` depend on
construct. A construct commit leaves those legacy stage facts unchanged. Step
13 changes formatting to consume accepted records and establishes the later
downstream relationship.

The construct-stage configuration is exactly:

```json
{
  "schema_version": "veriformis.construction-stage/v1",
  "recipe_id": "rcp-v1-...",
  "selected_source_ids": ["src-v1-..."]
}
```

`selected_source_ids` is sorted, unique, non-empty, and MUST equal the recipe's
exact `source_ids`. The complete configuration is serialized canonically and
its digest binds every stage artifact.

The stage exposes exactly two logical outputs:

| Output key | Artifact kind | Producer | Producer version |
| --- | --- | --- | --- |
| `recipe` | `dataset-recipe` | `veriformis.construction.recipe` | `1` |
| `result` | `construction-result` | `veriformis.construction.result` | `1` |

Both artifacts are scoped to the complete selected-source set and bind the full
construct-stage configuration digest. The recipe artifact contains the exact
canonical `DatasetRecipe`. The result artifact contains the complete
`ConstructionResult`, including its lifecycle and evidence objects. No third
construct-stage output key is permitted in v1.

Before `HEAD` promotion, the transaction MUST:

1. verify the expected parent revision and all declared stage dependencies;
2. load and validate the exact recipe artifact;
3. verify selected-source scope against the current source registry;
4. replay every pass over the declared immutable inputs;
5. verify every record field, evidence object, candidate, decision, review, and
   dataset record;
6. reject duplicate identities and unresolved references;
7. verify both artifact identities, producer metadata, source scope, and full
   configuration digest; and
8. verify the complete `ConstructionResult` and replay digest.

A contract, evidence, replay, or integrity failure writes no partial construct
outputs and leaves the previous `HEAD` current. Candidate rejection is data
inside a successful result and does not abort the transaction.

## Workspace v1 to v2 migration

Adding `construct` changes the persisted revision stage set. Existing revision
schema v1 workspaces MUST NOT be interpreted as revision schema v2 without
migration. The workspace layout schema remains version 1.

The migration is explicit, versioned, and transactional:

1. Open and fully verify the v1 `HEAD`, parent chain, revisions, and objects.
2. Preserve all existing source descriptors, artifact descriptors,
   content-addressed object bytes, and IDs.
3. Append one immutable revision-schema-v2 migration revision whose parent is
   the verified v1 head.
4. Preserve every legacy `parse`, `clean`, `chunk`, `format`, `validate`, and
   `seal` stage fact exactly, including complete, failed, stale, and absent
   states, configurations, inputs, outputs, and invalidation evidence.
5. Add only `construct` with `absent` state and no outputs.
6. Record the migration through the v2 revision schema, `migration` committed
   stage, source v1 parent, destination revision ID, and before and after state
   digests.
7. Atomically replace `HEAD` only after the v2 revision and all cross-version
   checks pass. Do not rewrite workspace metadata or any historical revision.

Failure before the commit point leaves the v1 workspace current and readable by
the v1 loader. Construction against an unmigrated workspace fails with
`unsupported-workspace-version`. Repeating a completed migration is a no-op or
returns the existing v2 head. Historical v1 revisions remain immutable and are
read through version-aware loaders.

## Deterministic replay

Given the same verified semantic input state, canonical recipe bytes, selected
sources, constructor versions, and review evidence set, replay MUST reproduce:

- pass ordering and per-pass facts;
- IR-field evidence and evidence-bound record fields;
- candidate fields and IDs;
- deterministic decisions and rejection reasons;
- dataset-record IDs and digests; and
- construction-result replay and result digests.

Replay order cannot depend on filesystem enumeration, hash-map order, locale,
clock, random state, or worker scheduling. Parallel execution MAY occur only
when final ordering and output bytes remain identical.

Audit revision IDs are non-semantic. Human review is not recreated. A
required-review replay without the same immutable accepted review evidence
stops at `pending_review` and does not reproduce an accepted record falsely.

## Error and rejection semantics

Contract, schema, identity, objective-shape, recipe, pass, evidence, lifecycle,
and replay failures use `construction-invalid`. Existing workspace and evidence
codes remain authoritative where those layers detect the failure:

- `workspace-revision-conflict` for a stale expected head;
- `unsupported-workspace-version` when construct is requested against revision
  schema v1;
- `workspace-corrupt` for an invalid migration, stage transition, artifact
  scope, producer, configuration digest, or persisted revision;
- `missing-stage-input` when a required upstream stage is absent;
- `stale-stage` for incomplete upstream construct dependencies;
- `source-evidence-invalid` for invalid visible-text evidence; and
- `duplicate-identity` for duplicate durable identities.

Human-readable messages may improve without changing these machine codes. A
contract error aborts the construct transaction. `rejected` and
`pending_review` are candidate decision statuses, not transaction errors.

Constructor non-output facts use this exact closed v1 diagnostic-code registry:

- `continuation-boundary-unavailable`;
- `section-structure-unavailable`;
- `source-chunks-unavailable`;
- `structured-field-chunk-unavailable`;
- `structured-field-empty-value`;
- `structured-field-unavailable`;
- `structured-ir-artifact-unavailable`;
- `transformation-pair-empty-or-unchanged`;
- `transformation-pair-unavailable`;
- `mapped-label-unavailable`; and
- `mapped-preference-unavailable`.

Each `ConstructionDiagnostic` contains exactly `schema_version`,
`diagnostic_id`, one registered `code`, non-empty `message`, `pass_id`,
`input_key`, sorted unique `source_ids`, and sorted unique `chunk_ids`. At least
one source or chunk identifier is required. The deterministic `input_key` is
derived from the versioned canonical source and chunk scope. Separate facts may
produce separate diagnostics for the same input unit. A high diagnostic count
never becomes a silent omission.

Promotion decisions use this exact closed v1 reason-code registry:

- `construction-integrity-v1` for deterministic acceptance without review;
- `review-approved` for acceptance backed by matching review evidence;
- `review-rejected` for rejection backed by matching review evidence; and
- `review-required` for a pending required review.

## Group 2 exit gate

Roadmap Steps 7 through 10 are complete only when all of these are true:

- all schemas, public constants, persisted loaders, and this document agree;
- workspace revision v1 to v2 migration is atomic, preserves every verified v1
  fact, and adds only absent construct state;
- raw multi-source fixtures execute versioned recipes through an atomic
  construct stage;
- all five deterministic objective constructors have positive, negative,
  tamper, multi-source, and replay tests;
- every candidate `RecordField` verifies through `SourceEvidence` or
  `IRFieldEvidence` with an exact output digest;
- `structured_field` remains unavailable for any IR metadata kind lacking
  verifiable field evidence;
- candidates are append-only, promotion decisions and rejections are auditable,
  required review blocks promotion, and accepted candidates become immutable
  records;
- identical semantic inputs reproduce candidate, record, and construction
  result IDs and digests;
- duplicate IDs, stale inputs, unsupported objectives, a `summary` request,
  and fabricated or cross-source evidence fail closed;
- the construct revision exposes only the exact `recipe` and `result` outputs
  with the required producers, selected-source scope, and full configuration
  digest; and
- the complete repository checks pass with every Group 2-only defect as an
  ordinary passing test.

## Historical Group 3 deferrals

The numbered items below preserve the allocation boundary at Group 2 closeout.
They are not current missing-capability claims: Steps 11 through 24 were later
implemented. Current maturity and remaining work are governed by
[current status](../current-status.md) and the
[independent product roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md).

Group 2 does not claim the following work:

1. **Step 11, curation and quality:** corpus-wide deduplication, filtering,
   contradiction checks, coverage accounting, balancing, advanced quarantine,
   and quality policy remain deferred. Group 2 provides the lifecycle and
   baseline construction-integrity decisions they will use.
2. **Step 12, leakage-safe splitting:** leakage groups, authoritative train and
   evaluation assignments, assignment digests, and realized split statistics
   remain deferred.
3. **Step 13, construction and serialization separation:** current serializers
   are not yet required to consume `DatasetRecord`. Group 2 artifacts cannot be
   described as emitted training rows.
4. **Step 14, Aptus-native output records:** lowering to `text`,
   `prompt_completion`, `instruction_output`, and structured `messages`, with
   masking-preserving metadata, remains deferred.
5. **Step 15, exact dataset validation:** recipe, evidence, record, curation,
   split, row, encoding, and compatibility validation as one immutable snapshot
   remains deferred. Group 2 verifies construction integrity only.
6. **Step 16, atomic sealing and verification:** normalized closed-file-set
   sealing, external trust evidence, path-safe independent verification, and
   mutation closure remain deferred.

At that historical boundary, `PipelineService`, the thin CLI adapter, the
dual-objective M1.1 gate, broader ingest, YAML/MCP automation, the optional
Aptus integration, and the workbench were later steps. Those deterministic
capabilities are now implemented. Model-assisted construction remains outside
the offline deterministic v1 contract and still requires a separate
owner-approved contract and plan.

## Related documentation

- [Product contract](../product-contract.md)
- [Integrity Contract v1](integrity-v1.md)
- [Authoritative independent product roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md)
- [Current implementation status](../current-status.md)
- [Architecture](../architecture.md)
- [Group 2 implementation plan](../../dev/active/group-2-dataset-construction/plan.md)
