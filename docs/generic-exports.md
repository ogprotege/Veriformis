# Generic Export Operator Guide

Veriformis publishes trainer-neutral derivatives of a verified finished
bundle: split JSONL, canonical JSON, constrained CSV, Parquet, Arrow IPC,
and a local Hugging Face DatasetDict. Choose among them for the file
shape a downstream tool can faithfully read. The choice does not create
or change the training objective, row schema, curation result, or
train/evaluation split.

**Status:** Implemented in development alpha `0.1.0`

**Last reviewed:** 2026-08-24 (independent-product Phase 10.1 packet; candidates remain non-executable)

Imported dataset-row bundles use the same generic containers. Mapping
does not add a trainer profile. Named TRL, MLX-LM, Axolotl, LLaMA-Factory, and Aptus adapters are
optional split-JSONL profiles; generic selectors stay `consumer_id`
null. Columnar v1 does not claim portable exact bytes. There is no Hub
upload.

**Next review:** Any generic-export selector, row-schema compatibility,
consumer-profile, request, receipt, or transport change

## Decide the semantics before the container

Four separate decisions are involved:

| Decision | Question it answers | When it is fixed |
| --- | --- | --- |
| Training objective | What source-grounded relationship is the model meant to learn? | `construct --objective` |
| Row schema | Which semantic fields represent that relationship? | `construct --target-row-schema`, then bound by the recipe and finished-dataset plan |
| Physical container | How should those already-finished rows and partitions be encoded as ordinary files? | Verified export selection after seal |
| Consumer profile | Has a named downstream consumer contract accepted this schema and behavior? | Only when an implemented profile explicitly says so |

The generic exports have no consumer profile. A continuation dataset
remains continuation whether its `prompt` and `completion` rows are written as
JSONL, JSON, CSV, Parquet, Arrow, or a local DatasetDict. Export never turns
`full_text` into continuation, converts messages into prompt/completion,
invents instructions, changes loss policy, or resplits records.

## Choose a container

| Choose | Use it when | Row schemas | Important boundary |
| --- | --- | --- | --- |
| `split-jsonl-directory` v1 | The downstream reader works one JSON object per line, benefits from separate train/evaluation files, or needs nested `messages` rows | `text`, `prompt_completion`, `instruction_output`, `messages` | Payload files contain only row-schema keys. Provenance is a separate aligned sidecar, enabled by default. The only v1 options are `train_partition_name`, `evaluation_partition_name`, and `include_provenance`, supplied together only through surface request v2. |
| `json` v1 | The downstream reader wants one self-describing dataset object with explicit schema, objective, loss, counts, and train/evaluation arrays | `text`, `prompt_completion`, `instruction_output`, `messages` | The fixed `dataset.json` document is the sole membership-bearing file. It is one complete JSON document; v1 makes no scale, streaming, or memory claim. It has no options. |
| `constrained-csv` v1 | A strictly checked tabular reader requires flat named columns and can preserve the frozen CSV dialect exactly | `text`, `prompt_completion`, `instruction_output` | Nested `messages` is refused. CSV is fully quoted UTF-8/LF with mandatory provenance. Formula-looking strings are preserved, not sanitized; spreadsheet display or safety is not claimed. It has no options. |
| `parquet` v1 | A Parquet reader needs columnar train/evaluation files and can tolerate `semantic_content_only` identity | `text`, `prompt_completion`, `instruction_output`, `messages` | Nested `messages` is a list of role/content structs. Null is unrepresentable. Execute requires optional extra `columnar`. Receipt bytes are this-run, not portable across PyArrow versions. |
| `arrow` v1 | An Arrow IPC reader needs uncompressed train/evaluation files under the same identity as Parquet | `text`, `prompt_completion`, `instruction_output`, `messages` | Same semantic fingerprint as Parquet for the same rows. Execute requires optional extra `columnar`. |
| `hugging-face-dataset` v1 | A local Hugging Face `DatasetDict` directory is the needed layout | `text`, `prompt_completion`, `instruction_output`, `messages` | Splits are `train` and `evaluation`. There is no Hub upload. Execute requires optional extra `columnar`. |

If the row schema is `messages`, use split JSONL, canonical JSON, Parquet,
Arrow, or a local Hugging Face DatasetDict. Do not flatten, stringify, or
otherwise encode the nested value into CSV outside the contract and call
it the same verified export.

If more than one container is compatible, prefer the simplest exact reader the
downstream system already has:

- choose split JSONL for one-record-per-line consumption;
- choose canonical JSON for explicit dataset-level metadata and partition
  structure in one document;
- choose constrained CSV only for a flat-schema system that requires columns
  and has been checked against the exact dialect; or
- choose Parquet, Arrow IPC, or a local Hugging Face DatasetDict when that
  file shape is the actual reader contract, knowing identity is
  `semantic_content_only` rather than portable exact bytes.

Measured tree sizes on the Phase 3 full-text fixture (one train row, two
evaluation rows, this pinned extra) were 24,073 bytes for split JSONL,
25,162 for Parquet, 25,386 for Arrow IPC, and 31,733 for the local
DatasetDict. Those numbers are this-run sizes for that fixture. They are
not a storage or speed recommendation across datasets or library versions.

File-extension familiarity is not consumer compatibility. A tool that says it
accepts “JSONL,” “JSON,” or “CSV” may still expect different field names,
message structure, loss masking, partition conventions, or metadata. Validate
those expectations before training or analysis.

## What every export preserves

Every supported pairing is derived from the same verified `minimal-v1` bundle
and preserves:

- the exact payload values and row schema;
- row order within train and evaluation;
- the authoritative train/evaluation assignment and zero leakage-group
  overlap;
- complete derivative membership; and
- receipt-bound verification evidence.

Keep train and evaluation separate. Do not append evaluation rows to the train
file or treat the evaluation partition as a named training subset. Provenance
files explain row origin and assignment; they are not payload files to feed to
a trainer.

The sealed `.vfbundle` remains the canonical product. An export is a verified
derivative for ordinary-file use, not a replacement source of authority.

## Safe operator sequence

1. Retain the canonical bundle's `manifest.json` SHA-256 outside the bundle.
2. Run `veriformis export discover` and confirm the selector supports the
   bundle's row schema.
3. Run `veriformis export dry-run --request-json REQUEST` with
   `source_trust_policy` set to `require_external_digest` and the retained
   manifest digest. Review the exact plan ID, sample rows, omission labels, and
   relative destination tree.
4. Copy the dry-run result's `export_plan_id` into the execute request's
   `expected_export_plan_id`. Run
   `veriformis export execute --request-json REQUEST` with the same selector,
   options, trust evidence, and a new destination root. Publication is
   no-replace: the only overwrite policy is `refuse`.
5. Run `veriformis export-verify --request-json REQUEST` with those same plan
   bindings and the published destination.

The request JSON is a strict canonical protocol object, not a loose CLI
configuration document. The one-line templates below enumerate the exact
fields in canonical key order. Replace each zero digest or ID and each example
path with the value retained or returned by the preceding step. For canonical
JSON or constrained CSV, change only `container_id` to `json` or
`constrained-csv` in these request-v1 templates.

Dry run, request v1:

```json
{"bundle":"/path/to/source.vfbundle","consumer_id":null,"consumer_profile_version":null,"container_id":"split-jsonl-directory","container_version":1,"expected_manifest_sha256":"0000000000000000000000000000000000000000000000000000000000000000","operation":"dry_run","overwrite_policy":"refuse","schema_version":"veriformis.export-surface-request/v1","source_trust_policy":"require_external_digest"}
```

Execute the exact returned plan into a new destination:

```json
{"bundle":"/path/to/source.vfbundle","consumer_id":null,"consumer_profile_version":null,"container_id":"split-jsonl-directory","container_version":1,"destination_root":"/path/to/new-export","expected_export_plan_id":"export-plan-v1-0000000000000000000000000000000000000000000000000000000000000000","expected_manifest_sha256":"0000000000000000000000000000000000000000000000000000000000000000","operation":"execute","overwrite_policy":"refuse","schema_version":"veriformis.export-surface-request/v1","source_trust_policy":"require_external_digest"}
```

Source-bound verification of that destination:

```json
{"bundle":"/path/to/source.vfbundle","consumer_id":null,"consumer_profile_version":null,"container_id":"split-jsonl-directory","container_version":1,"destination_root":"/path/to/new-export","expected_export_plan_id":"export-plan-v1-0000000000000000000000000000000000000000000000000000000000000000","expected_manifest_sha256":"0000000000000000000000000000000000000000000000000000000000000000","operation":"verify","overwrite_policy":"refuse","schema_version":"veriformis.export-surface-request/v1","source_trust_policy":"require_external_digest"}
```

Configured split JSONL uses request v2 and the complete options object. This
example retains the safe defaults; change only the two lowercase filename
stems or Boolean provenance choice:

```json
{"bundle":"/path/to/source.vfbundle","consumer_id":null,"consumer_profile_version":null,"container_id":"split-jsonl-directory","container_options":{"evaluation_partition_name":"evaluation","include_provenance":true,"schema_version":"veriformis.split-jsonl-options/v1","train_partition_name":"train"},"container_version":1,"expected_manifest_sha256":"0000000000000000000000000000000000000000000000000000000000000000","operation":"dry_run","overwrite_policy":"refuse","schema_version":"veriformis.export-surface-request/v2","source_trust_policy":"require_external_digest"}
```

Repeat the identical `container_options` for v2 execute and verify, adding the
same `destination_root` and dry-run `expected_export_plan_id` fields shown in
the v1 templates. Request v1 selects any current generic except configured
split JSONL. Request v2 is only for split JSONL; canonical JSON,
constrained CSV, Parquet, Arrow, and Hugging Face DatasetDict refuse it. The [CLI reference](cli.md#verified-export-commands) explains each
operation, options boundary, preview result, and output tree.

Dry run reads and verifies the source but does not invoke a renderer or access
a destination. Its preview is bounded operator information: a sample payload
may be omitted whole when it exceeds 65,536 canonical bytes or the response
budget. The digest and byte size remain present; an omission is not a truncated
row.

`export inspect` checks a destination's self-described physical receipt and
closed tree without proving source authority. `export-verify` is the
source-bound check and should be the final export gate.

## Optional deterministic transport

After a directory export verifies, `veriformis package` can wrap the unchanged
receipt-bound directory as `deterministic-export-pack-zip-v1` with suffix
`.vfexport.zip`. Supply the separately retained SHA-256 of the canonical
`export-receipt.json`; verify the archive with `package-verify` and the same
receipt digest.

This is transport after export. It is not a fourth semantic container, another
renderer, a trainer format, or source-bound export verification. Keep the
receipt digest separately if the archive must retain an external anchor.

## Downstream admission checklist

Before consuming an export, confirm all of the following outside Veriformis:

- the downstream loader accepts the exact row schema and field meanings;
- its objective and loss/masking behavior match the already-selected training
  objective and row loss policy;
- it keeps evaluation separate from training;
- it preserves nested messages where applicable and does not coerce strings,
  Unicode, controls, or embedded newlines;
- it ignores metadata/provenance as training payload unless its own explicit
  contract says otherwise; and
- any trainer-specific reshaping is treated as a new adapter boundary with its
  own validation, not as a property of the generic export.

Veriformis does not currently claim generic compatibility with Aptus, MLX-LM,
TRL, Axolotl, LLaMA-Factory, Unsloth, a spreadsheet application, or every tool
that recognizes one of these file extensions.

## Contract references

- [Verified Export Contract v1](contracts/verified-export-v1.md)
- [Split JSONL Export v1](contracts/split-jsonl-export-v1.md)
- [Canonical JSON Export v1](contracts/canonical-json-export-v1.md)
- [Constrained CSV Export v1](contracts/constrained-csv-export-v1.md)
- [Deterministic Archive Transport v1](contracts/bundle-transport-v1.md)
- [Dataset Taxonomy Contract v1](contracts/taxonomy-v1.md)
