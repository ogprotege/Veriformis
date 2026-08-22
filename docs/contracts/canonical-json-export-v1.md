# Veriformis Canonical JSON Export v1

**Contract ID:** `veriformis.canonical-json-export`

**Contract version:** `1`

**Container selector:** `json`, version `1`, no consumer profile

**Dataset schema:** `veriformis.canonical-json-dataset/v1`

**Provenance schema:** `veriformis.canonical-json-provenance/v1`

**Determinism claim:** `portable_exact_bytes`

**Status:** Implemented in independent-product Phase 5.2

**Last reviewed:** 2026-08-22 (Phase 5.5 consolidated semantic round-trip)

## Purpose and authority

This contract defines a consumer-neutral canonical JSON derivative of a
verified Finished Dataset v1 bundle. It places both authoritative semantic
partitions in one explicit JSON object, binds their row schema, objective,
loss policy, row-set identity, and split identity, and emits a separate aligned
provenance object plus the receipt required by the Verified Export Contract v1.

The admitted `.vfbundle` remains authoritative. This container MUST NOT
construct, filter, balance, reorder, resplit, repartition, or rewrite semantic
rows. It does not select a training objective and does not claim compatibility
with Aptus, MLX-LM, TRL, or any other trainer.

## Executable profile

Production discovery contains this selector for v1:

```text
container_id: json
container_version: 1
consumer_id: null
consumer_profile_version: null
determinism_claim: portable_exact_bytes
supported_row_schemas:
  instruction_output, messages, prompt_completion, text
overwrite_policies: refuse
```

The exact renderer dependency is
`veriformis-canonical-json-renderer`, version `1`, role `renderer`. It is an
internal reviewed implementation, not a public registration or plugin API.
Discovery remains `veriformis.export-discovery/v1`.

## Request compatibility and configuration

Canonical JSON v1 has no container options. Dry run, execution, and source-
bound verification use the exact historical
`veriformis.export-surface-request/v1` selected-operation shape. A configured
`veriformis.export-surface-request/v2` request is refused for this selector,
including when `container_options` is empty.

The fixed file set and file bytes bind the v1 `ExportPlan` identity. The
operator-confirmed dry-run plan ID is therefore required unchanged for
execution and source-bound verification.

## Closed output tree

Publication produces exactly:

```text
README.md
dataset.json
export-receipt.json
metadata/row-provenance.json
```

No member is optional or configurable. The receipt's planned file set excludes
the receipt itself, as required by the Verified Export Contract. The closed-
tree verifier additionally validates the canonical in-tree receipt and rejects
every missing or unexpected member.

## Canonical dataset object

`dataset.json` is canonical UTF-8 JSON with no byte-order mark and no trailing
LF. Its exact top-level fields are:

- `schema_version`, fixed to `veriformis.canonical-json-dataset/v1`;
- `container_id`, fixed to `json`, and `container_version`, fixed to `1`;
- `row_schema`, `objective_id`, and the taxonomy-derived `loss_policy`;
- `row_set_id` and `split_result_id`;
- `partition_order`, fixed to `["train", "evaluation"]`;
- `train_row_count` and `evaluation_row_count`;
- `splits`, an object with exactly `train` and `evaluation` arrays;
- `provenance_path`, fixed to `metadata/row-provenance.json`;
- `provenance_alignment`, fixed to `train_then_evaluation`;
- `consumer_profile`, fixed to null; and
- `trainer_compatibility_claimed`, fixed to false.

The train count is positive. The evaluation count may be zero when the source
contract permits an empty evaluation partition. Each count MUST equal the
length of its corresponding array. `loss_policy` MUST be the policy defined by
the stated current row schema, not caller-supplied metadata. The objective MUST
be the one objective shared by every source provenance value.

`dataset.json` is the only membership-bearing planned file. Its file-plan
membership scope is `all`, and its record count is the exact train plus
evaluation total.

## Payload arrays

`splits.train` and `splits.evaluation` contain payload objects only, in that
fixed logical partition order. Payload values MUST contain no Veriformis row
ID, record ID, leakage group, split group, provenance, evidence, validation,
or competing row-schema key.

Rows and partitions are copied semantically without change from the verified
source row set. JSON uses the repository canonical lossless writer. Unicode
strings, nulls, empty strings permitted by a row schema, nested message arrays,
record order, and partition membership remain exact. The arrays MUST decode
strictly as the stated current row schema: `text`, `prompt_completion`,
`instruction_output`, or `messages`.

The explicit `partition_order` is descriptive and normative. It does not
combine the two partitions or turn evaluation rows into training rows.

## Aligned provenance object

`metadata/row-provenance.json` is canonical UTF-8 JSON with no byte-order mark
and no trailing LF. It has exactly these top-level fields:

- `schema_version`, fixed to `veriformis.canonical-json-provenance/v1`;
- `container_id`, fixed to `json`, and `container_version`, fixed to `1`;
- `row_schema` and `objective_id`;
- `row_set_id` and `split_result_id`;
- `train_row_count` and `evaluation_row_count`;
- `alignment`, fixed to `train_then_evaluation`; and
- `rows`, the complete Finished Dataset v1 `RowProvenance` sequence.

`rows` has exactly one value per payload row, ordered as every train row
followed by every evaluation row. Partition, ordinal, row identity, payload
digest, record binding, source, objective, leakage group, assignment, split,
and evidence checks remain those of the Finished Dataset Contract v1. The
object-level schema, container, row-schema, objective, row-set, split-result,
count, and alignment metadata MUST match `dataset.json` and the verified
source. Validation MUST reconstruct the strict Finished Dataset v1 `RowSet`
from the payload arrays and provenance. The reconstructed `row_set_id` MUST
equal the top-level dataset/provenance identity, the internal export plan, and
the verified source, so top-level metadata cannot self-consistently drift away
from row/provenance content.

The provenance file is an evidence sidecar with file-plan membership scope
`none`. Its total record count does not make it a second membership-bearing
payload.

## README

`README.md` is deterministic UTF-8 Markdown with LF line endings and a final
LF. It names the container version, row schema, loss policy, fixed paths and
counts, provenance alignment, row-set identity, and split identity. It states
that the partition arrays contain canonical payload objects only and that the
container neither selects an objective nor claims universal trainer
compatibility. It contains no clock, host path, username, random value, or
environment-derived text.

## Planning, rendering, and verification

Dry run verifies the source under the selected trust policy, reconstructs the
strict source row set, and plans exact SHA-256 and byte size for every
derivative file. It does not render or touch a destination.

Execution re-verifies the source and plan, renders twice from fresh strict
inputs, requires identical complete byte trees, validates exact source
membership and semantics for both renders, stages privately, verifies the
descriptor-reread tree, and publishes with atomic no-replace `refuse` policy.
The receipt binds every planned derivative path, byte count, digest, role,
media type, record count, membership scope, source identity, and plan identity.

Source-bound verification re-derives the same plan from the separately trusted
source and verifies the visible closed tree and receipt. Self-described
inspection reports physical receipt evidence without upgrading source trust.
Tampering, missing or unexpected paths, source-digest mismatch, receipt
forgery, plan mismatch, links, special files, path races, partial publication,
or a configured request fail closed.

## Round-trip and admission evidence

Admission requires fixtures for all four current row schemas. Reloading the
two arrays with the strict schema decoder MUST reproduce identical ordered
semantic payloads and partitions. Reloading `rows` MUST reproduce the source's
identical ordered provenance sequence. Tests cover Unicode, empty evaluation,
nested messages, repeated rendering, metadata and count mutation, payload and
provenance mutation, reconstructed row-set and split closure, request-version
refusal, every-file tamper, missing and unexpected files, and
receipt/source/plan mismatch.

Phase 5.5 adds a test-only consolidated semantic round-trip fixture matrix. It
reloads this container's ordinary files for all four current row schemas and
reconstructs the identical ordered train and evaluation payloads, complete
provenance, and source `RowSet` identity. The shared matrix also exercises one
canonical semantic tamper for this container. It does not add a product
importer, semantic replayer, API, taxonomy entry, support promotion, or trainer
claim, and it does not weaken the container-specific admission evidence above.

## Dependency, license, security, and resource boundary

The renderer uses only Veriformis's canonical row and export services and adds
no third-party serialization dependency. It does not infer or grant a content
license. Source license and trust facts remain governed by the authoritative
bundle and aligned provenance.

All operation remains local and offline. The shared request, response, plan,
tree-depth, descriptor-walk, no-link, no-replace, cancellation, and partial-
publication bounds remain normative. The two-render exact-byte proof can hold
two byte trees in memory; the single dataset and provenance objects can each
hold all rows in memory. V1 makes no large-scale performance or memory claim.

## Versioning, migration, and deprecation

The ten persisted `veriformis.verified-export` v1 models, request v1, response
v1, discovery v1, Finished Dataset v1, and source bundle are unchanged.

Changing row encoding, the fixed tree, top-level fields, split-object shape,
partition order, provenance alignment, determinism claim, selector meaning, or
trainer-compatibility statement requires a new container, dataset, or
provenance contract version and migration fixtures. V1 remains readable and
verifiable while supported. Any future deprecation requires an announced
replacement and a retained verifier; silent reinterpretation is forbidden.

## Non-goals

- Choosing a recipe, objective, tokenizer, prompt template, masking policy, or
  trainer.
- Combining evaluation with train or creating a recitation-gold subset.
- Adding `split_group` or any other provenance field to payload rows.
- Offering configurable filenames, optional provenance, or split JSONL
  behavior; those are separate container semantics.
- Mutating the source bundle or workspace.
- Network publication, replacement, signing, or notarization.
