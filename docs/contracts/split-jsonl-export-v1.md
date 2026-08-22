# Veriformis Split JSONL Export v1

**Contract ID:** `veriformis.split-jsonl-export`

**Contract version:** `1`

**Container selector:** `split-jsonl-directory`, version `1`, no consumer
profile

**Options schema:** `veriformis.split-jsonl-options/v1`

**Data-card schema:** `veriformis.split-jsonl-data-card/v1`

**Determinism claim:** `portable_exact_bytes`

**Status:** Implemented in independent-product Phase 5.1

**Last reviewed:** 2026-08-21

## Purpose and authority

This contract defines the first consumer-neutral local derivative of a verified
Finished Dataset v1 bundle. It exposes the bundle's authoritative `train` and
`evaluation` semantic partitions as ordinary canonical JSONL files and adds a
deterministic README, machine-readable data card, optional aligned provenance,
and the receipt required by the Verified Export Contract v1.

The admitted `.vfbundle` remains authoritative. This container MUST NOT
construct, filter, balance, reorder, resplit, repartition, or rewrite semantic
rows. It does not select a training objective and does not claim compatibility
with Aptus, MLX-LM, TRL, or any other trainer.

## Executable profile

Production discovery contains exactly this selector for v1:

```text
container_id: split-jsonl-directory
container_version: 1
consumer_id: null
consumer_profile_version: null
determinism_claim: portable_exact_bytes
supported_row_schemas:
  instruction_output, messages, prompt_completion, text
overwrite_policies: refuse
```

The exact renderer dependency is
`veriformis-split-jsonl-renderer`, version `1`, role `renderer`. It is an
internal reviewed implementation, not a public registration or plugin API.
Discovery remains `veriformis.export-discovery/v1`; callers use this contract
to interpret the selector's options. Machine-readable option discovery is not
part of v1.

## Request compatibility and configuration

`veriformis.export-surface-request/v1` remains readable and selects these safe
defaults:

```json
{"evaluation_partition_name":"evaluation","include_provenance":true,"schema_version":"veriformis.split-jsonl-options/v1","train_partition_name":"train"}
```

A caller that configures the container MUST use
`veriformis.export-surface-request/v2` and supply `container_options` as the
complete canonical object above, with only the two names and Boolean changed as
needed. Missing fields, unknown fields, duplicate keys, noncanonical bytes,
floats, wrong primitive types, an empty object, and unsupported versions fail
before source or destination access. Request v1 has no `container_options`
field and retains its exact Phase 4 shape.

The v2 options MUST be repeated without change for dry run, execution, and
source-bound verification. The derived file paths and file bytes change the
v1 `ExportPlan` identity, so an option change after dry run fails the
operator-confirmed plan-ID gate.

### Partition-name grammar

Each configured name is a filename stem matching
`^[a-z0-9][a-z0-9_-]{0,63}$`. The two stems MUST differ. The implementation
derives only `data/<stem>.jsonl`; callers never supply a path.

The complete derivative path set, including `export-receipt.json`, MUST pass
the Verified Export Contract's portable relative-path, reserved-device,
case-fold, Unicode-compatibility, collision, and file/ancestor checks.
Absolute paths, drive prefixes, separators, dot segments, control characters,
format characters, Windows device aliases, case variants, and Unicode aliases
fail before source access.

Configured names change only destination filenames. Their semantic partitions
remain exactly `train` and `evaluation`.

## Closed output tree

With defaults, publication produces exactly:

```text
README.md
data/evaluation.jsonl
data/train.jsonl
export-receipt.json
metadata/dataset-card.json
metadata/row-provenance.jsonl
```

When `include_provenance` is `false`, only
`metadata/row-provenance.jsonl` is omitted. Configured partition names replace
only the two stems beneath `data/`. No other member is optional.

The receipt's planned file set excludes the receipt itself, as required by the
Verified Export Contract. The closed-tree verifier additionally validates the
canonical in-tree receipt and rejects every missing or unexpected member.

## Payload JSONL

The two partition files contain payload objects only. They MUST contain no
Veriformis row ID, record ID, leakage group, split group, provenance, evidence,
validation, or competing row-schema key.

Rows and partitions are copied semantically without change from the verified
source row set. JSON uses the repository canonical lossless writer. JSONL is
UTF-8 without a byte-order mark, one canonical JSON object per line, LF line
endings, no blank lines, and one final LF for every non-empty file. A permitted
zero-row evaluation partition is exactly zero bytes. Unicode strings, nulls,
empty strings permitted by a row schema, nested message arrays, record order,
and partition membership remain exact.

The train file has file-plan membership scope `train`; the evaluation file has
scope `evaluation`. README, data card, and provenance are evidence sidecars
with membership scope `none`. The provenance file may retain its total record
count without becoming a second membership-bearing payload.

## Optional provenance

When included, `metadata/row-provenance.jsonl` is the complete canonical
Finished Dataset v1 `RowProvenance` stream. It has exactly one value per
payload row, ordered as every train row followed by every evaluation row.
Partition, ordinal, row identity, payload digest, record binding, source,
objective, leakage-group, assignment, split, and evidence checks remain those
of the finished-dataset contract.

The option is all-or-nothing. A filtered, reordered, partition-local, renamed,
or partially aligned provenance stream is not valid v1 output.

## Data card

`metadata/dataset-card.json` is canonical UTF-8 JSON with no trailing LF. Its
exact fields are:

- `schema_version`, fixed to `veriformis.split-jsonl-data-card/v1`;
- `container_id` and `container_version`;
- `row_schema`, `objective_id`, and taxonomy `loss_policy`;
- `row_set_id` and `split_result_id`;
- `train_path`, `train_row_count`, `evaluation_path`, and
  `evaluation_row_count`;
- `provenance_path` and `provenance_row_count`, both present as values or both
  null;
- `provenance_alignment`, fixed to `train_then_evaluation`;
- `receipt_path`, fixed to `export-receipt.json`;
- `consumer_profile`, fixed to null; and
- `trainer_compatibility_claimed`, fixed to false.

The train count is positive. The optional provenance count, when present,
equals train plus evaluation. All paths must equal the configured closed tree.

## README

`README.md` is deterministic UTF-8 Markdown with LF line endings and a final
LF. It names the container version, row schema, loss policy, exact paths and
counts, provenance state and alignment, row-set identity, and split identity.
It states that payload files contain canonical payload objects only and that
the container neither selects an objective nor claims universal trainer
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
or changed options fail closed.

## Round-trip and admission evidence

Admission requires fixtures for all four current row schemas. Reloading the two
partition files with the strict schema decoder MUST reproduce identical
ordered semantic payloads and partitions. Included provenance MUST reload to
the source's identical ordered provenance sequence. Tests cover Unicode,
empty evaluation, nested messages, configurable names, provenance on/off, repeated rendering,
wrong-operation requests, strict request subclasses, traversal and alias
refusal, tamper, missing and unexpected files, and plan-option mismatch.

The shared Phase 5 round-trip matrix remains roadmap item 5.5; that later
consolidation does not weaken the container-specific admission evidence
required here.

## Dependency, license, security, and resource boundary

The renderer uses only Veriformis's canonical row and export services and adds
no third-party serialization dependency. It does not infer or grant a content
license. Source license and trust facts remain governed by the authoritative
bundle and optional provenance; omitting the provenance sidecar is not a
license claim.

All operation remains local and offline. The shared request, response, plan,
tree-depth, descriptor-walk, no-link, no-replace, cancellation, and partial-
publication bounds remain normative. The two-render exact-byte proof can hold
two byte trees in memory; v1 makes no large-scale performance or memory claim.

## Versioning, migration, and deprecation

The ten persisted `veriformis.verified-export` v1 models, response v1,
discovery v1, Finished Dataset v1, and historical request v1 are unchanged.
Configured operation is an additive request v2 surface.

Changing row encoding, default options, path grammar, path roles, metadata
fields, README bytes, provenance alignment, determinism claim, or selector
meaning requires a new container or options/data-card contract version and
migration fixtures. V1 remains readable and verifiable while supported. Any
future deprecation requires an announced replacement and a retained verifier;
silent reinterpretation is forbidden.

## Non-goals

- Choosing a recipe, objective, tokenizer, prompt template, masking policy, or
  trainer.
- Combining evaluation with train or creating a recitation-gold subset.
- Adding `split_group` or any other provenance field to payload rows.
- Mutating the source bundle or workspace.
- Network publication, replacement, signing, or notarization.
