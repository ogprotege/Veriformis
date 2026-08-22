# Veriformis Constrained CSV Export v1

**Contract ID:** `veriformis.constrained-csv-export`

**Contract version:** `1`

**Container selector:** `constrained-csv`, version `1`, no consumer profile

**Data-card schema:** `veriformis.constrained-csv-data-card/v1`

**Dialect identifier:** `veriformis.constrained-csv-dialect/v1`

**Determinism claim:** `portable_exact_bytes`

**Status:** Implemented and merged in independent-product Phase 5.3 (PR #55)

**Last reviewed:** 2026-08-22 (independent-product Phase 5 closeout)

## Purpose and authority

This contract defines a consumer-neutral CSV derivative of a verified Finished
Dataset v1 bundle. It is deliberately constrained to the three current product
row schemas whose payloads are flat exact strings. It preserves the source's
authoritative `train` and `evaluation` partitions, emits complete aligned
provenance and machine-readable metadata, and uses the receipt required by the
Verified Export Contract v1.

The admitted `.vfbundle` remains authoritative. This container MUST NOT
construct, filter, balance, reorder, resplit, repartition, normalize, trim,
coerce, or otherwise rewrite semantic values. It does not select a training
objective and does not claim compatibility with Aptus, MLX-LM, TRL,
spreadsheet software, or any other consumer.

## Executable profile

Production discovery contains exactly this selector:

```text
container_id: constrained-csv
container_version: 1
consumer_id: null
consumer_profile_version: null
determinism_claim: portable_exact_bytes
supported_row_schemas:
  instruction_output, prompt_completion, text
overwrite_policies: refuse
```

The exact renderer dependency is
`veriformis-constrained-csv-renderer`, version `1`, role `renderer`. It is an
internal reviewed implementation, not a public registration or plugin API.
Discovery remains `veriformis.export-discovery/v1`.

The selector MUST NOT advertise `messages`. The current flat schema and column
contracts are:

| Row schema | Exact ordered columns | Exact payload mapping |
| --- | --- | --- |
| `text` | `text` | `payload["text"]` |
| `prompt_completion` | `prompt`, `completion` | The two same-named payload strings |
| `instruction_output` | `instruction`, `input`, `output` | The three same-named payload strings |

Every value is an exact string. No competing schema key, row identity,
record identity, leakage group, split group, provenance, evidence, validation
fact, or derived consumer field is added to a CSV record.

## Request compatibility and configuration

Constrained CSV v1 has no container options. Dry run, execution, and
source-bound verification use the historical exact
`veriformis.export-surface-request/v1` selected-operation shape. A configured
`veriformis.export-surface-request/v2` request is refused for this selector,
including when `container_options` is empty, before source or destination
access.

The fixed output paths, schema-specific columns, and exact file bytes bind the
v1 `ExportPlan` identity. The operator-confirmed dry-run plan ID is required
unchanged for execution and source-bound verification.

## Nested-value refusal

The `messages` row schema is structurally nested and is unsupported. Once the
verified source row set reveals `row_schema=messages`, dry run, execution, and
source-bound verification MUST fail before destination inspection, staging, or
publication. The error MUST name `messages`, identify `constrained-csv` as the
incompatible selector, and direct the operator to `split-jsonl-directory` v1 or
`json` v1, both of which preserve nested message arrays.

Serializing a nested list or object as JSON text inside one CSV cell is not an
allowed fallback. A null, list, object, number, Boolean, missing value, extra
value, or non-string value in any otherwise flat row likewise fails closed at
the strict source-row or container boundary.

## Fixed CSV dialect and byte contract

The dialect identifier `veriformis.constrained-csv-dialect/v1` freezes all of
the following behavior. An implementation MUST set every behavior explicitly;
it MUST NOT inherit platform, locale, spreadsheet, or standard-library dialect
defaults.

- Encoding is strict UTF-8 without a byte-order mark.
- The delimiter is one ASCII comma, `,`.
- The quote character is one ASCII double quote, `"`.
- Every header and data field is quoted, equivalent to `QUOTE_ALL`.
- A double quote inside a field is escaped by doubling it. There is no separate
  escape character and backslash has no special meaning.
- The record terminator is exactly one LF byte. Every file ends in one LF after
  its final record.
- Each file begins with exactly one schema-specific header record in the exact
  column order above. Header fields follow the same quote-all rule.
- A non-empty train partition contains one record per source train row after
  the header. Evaluation contains one record per source evaluation row after
  the header. A permitted zero-row evaluation partition is the canonical
  quoted header plus its final LF, not a zero-byte file.

Commas, double quotes, tabs, leading or trailing whitespace, NUL, CR, LF, CRLF,
and other valid Unicode code points inside a field are data. They are preserved
exactly inside the quoted field. In particular, embedded CR, LF, and CRLF are
not normalized to the record terminator. A logical CSV record may therefore
occupy more than one physical line.

Unicode strings are encoded without NFC, NFD, NFKC, case, newline, whitespace,
or replacement-character normalization. Canonically equivalent but
code-point-distinct strings remain distinct. A string that cannot be encoded
as strict UTF-8 fails closed rather than being replaced.

## Null and empty-string semantics

CSV v1 defines no null token or null sentinel. JSON null / Python `None` is
unrepresentable and MUST fail before rendering. The strings `null`, `NULL`,
`None`, and `\\N` are ordinary exact string values and MUST NOT be interpreted
as null.

At the CSV codec layer, the empty string has exactly one encoding: the quoted
empty field `""`. It is a string, never null, and differs from a missing or
ragged column. Finished Dataset v1 currently requires every field in the three
admitted product row schemas to be non-empty, so a valid constrained CSV v1
export does not contain an empty data field. Strict schema reload MUST reject a
mutated empty data field even though the codec can identify it unambiguously.
Changing the current product-row empty-value rule would require explicit
migration and new admission evidence before this container could emit such a
row.

## Closed output tree

Publication produces exactly:

```text
README.md
data/evaluation.csv
data/train.csv
export-receipt.json
metadata/dataset-card.json
metadata/row-provenance.jsonl
```

No member is optional or configurable. The receipt's planned file set excludes
the receipt itself, as required by the Verified Export Contract. The closed-
tree verifier additionally validates the canonical in-tree receipt and rejects
every missing or unexpected member.

`data/train.csv` has file-plan role `training-partition`, media type `text/csv`,
membership scope `train`, and the exact train payload-row count.
`data/evaluation.csv` has role `evaluation-partition`, media type `text/csv`,
membership scope `evaluation`, and the exact evaluation payload-row count.
Header records do not increment those counts. README, data card, and provenance
are evidence sidecars with membership scope `none`; provenance retains the
total payload-row count without becoming a second membership-bearing file.

## Strict CSV loading and round trip

A contract loader MUST decode strict UTF-8, reject a byte-order mark, parse only
the fixed v1 dialect, require the exact header and column count, preserve every
field string without rewriting, and apply the stated product-row schema. It
MUST reject missing, extra, duplicate, reordered, unquoted, or unknown headers;
ragged or over-wide records; blank records; alternate delimiters, quote or
escape rules; non-LF record terminators; a missing final LF; invalid UTF-8; and
any value that violates the selected ProductRow contract.

Acceptance of merely semantically equivalent CSV bytes is not sufficient for
this exact-byte profile. After parsing and strict row validation, a loader MUST
re-render the decoded table under this contract and require byte-for-byte
equality with the input. That comparison distinguishes the one canonical
quote-all encoding from other CSV spellings that a permissive parser might
otherwise accept.

Reloaded train and evaluation records MUST recreate the exact ordered payloads
from their source partitions. With the aligned provenance described below,
they MUST reconstruct one strict Finished Dataset v1 `RowSet` whose
`row_set_id`, split identity, product rows, partition order, and provenance are
identical to the verified source.

The general-purpose structured-input CSV parser is not this contract loader.
An ingest recovery path that trims cells, normalizes embedded newlines, drops
blank rows, heuristically detects headers, or pads ragged rows MUST NOT be used
to prove this export's round trip.

## Data card

`metadata/dataset-card.json` is canonical lossless UTF-8 JSON with no byte-order
mark and no trailing LF. Its exact top-level fields are:

- `schema_version`, fixed to `veriformis.constrained-csv-data-card/v1`;
- `container_id`, fixed to `constrained-csv`, and `container_version`, fixed to
  `1`;
- `row_schema` and the exact ordered `columns` for that schema;
- `dialect`, fixed to `veriformis.constrained-csv-dialect/v1`;
- `encoding`, fixed to `utf-8`, and `byte_order_mark`, fixed to false;
- `delimiter`, fixed to `,`, `quote_character`, fixed to `"`, `quoting`, fixed
  to `all`, and `doublequote`, fixed to true;
- `record_terminator`, fixed to `lf`;
- `null_encoding`, fixed to null, and `empty_string_encoding`, fixed to
  `quoted-empty-field`;
- `objective_id` and the taxonomy-derived `loss_policy`;
- `row_set_id` and `split_result_id`;
- `train_path`, fixed to `data/train.csv`, and `train_row_count`;
- `evaluation_path`, fixed to `data/evaluation.csv`, and
  `evaluation_row_count`;
- `provenance_path`, fixed to `metadata/row-provenance.jsonl`, and
  `provenance_row_count`;
- `provenance_alignment`, fixed to `train_then_evaluation`;
- `receipt_path`, fixed to `export-receipt.json`;
- `consumer_profile`, fixed to null; and
- `trainer_compatibility_claimed`, fixed to false.

The train count is positive. The evaluation count may be zero. The provenance
count equals train plus evaluation. The schema, columns, loss policy, paths,
counts, and dialect literals are closed cross-field values rather than
caller-supplied descriptive metadata.

## Mandatory aligned provenance

`metadata/row-provenance.jsonl` is mandatory and is the complete canonical
Finished Dataset v1 `RowProvenance` stream. It is UTF-8 without a byte-order
mark, has one canonical JSON object and one final LF per row, contains no blank
lines, and is ordered as every train row followed by every evaluation row.

Partition, ordinal, row identity, payload digest, record binding, source,
objective, leakage group, assignment, split, and evidence checks remain those
of the Finished Dataset Contract v1. The stream has exactly one value per CSV
payload record. It MUST bind each strictly reconstructed payload to the source
row ID and payload digest, and the complete sequence MUST reconstruct the exact
source `RowSet` identity. A filtered, reordered, partition-local, renamed,
partially aligned, or self-consistently substituted provenance stream is not
valid v1 output.

## README

`README.md` is deterministic UTF-8 Markdown with LF line endings and a final
LF. It names the container version, row schema, exact ordered columns, fixed
dialect, paths and counts, provenance alignment, row-set identity, split
identity, null refusal, and nested-message refusal with the JSONL/JSON
alternatives. It states that the container neither selects an objective nor
claims universal trainer compatibility or spreadsheet safety. It contains no
clock, host path, username, random value, or environment-derived text.

Because exact formula-looking strings are not rewritten, an operator SHOULD
treat these files as data and apply destination-specific spreadsheet safety
controls before opening untrusted values in software that evaluates cells.

## Planning, rendering, and verification

Dry run verifies the source under the selected trust policy, reconstructs the
strict source row set, enforces the admitted flat schema, and derives exact
in-memory bytes, SHA-256, and byte size for every derivative file. It does not
touch, stage, or publish a destination.

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
a configured request, or an unsupported row schema fails closed.

## Round-trip and admission evidence

Admission requires all of the following evidence:

1. Discovery advertises only `instruction_output`, `prompt_completion`, and
   `text`, with no consumer profile, exact-byte determinism, and refuse-only
   overwrite behavior.
2. Each admitted schema round-trips both ordered partitions and complete
   provenance to the identical source `RowSet` and identities.
3. Golden bytes cover commas, doubled quotes, tabs, leading and trailing
   whitespace, NUL, CR, LF, CRLF, formula-looking strings, non-ASCII and
   non-BMP characters, and canonically equivalent but distinct Unicode forms.
4. Tests pin quoted headers, quote-all fields, comma delimiter, doubled-quote
   escaping, strict UTF-8 without a byte-order mark, LF record terminators, and
   the final LF.
5. Null, missing, ragged, over-wide, wrong-header, duplicate-header,
   empty-data-field, invalid-UTF-8, byte-order-mark, alternate-dialect, and
   noncanonical-equivalent CSV mutations fail closed.
6. A zero-row evaluation partition is an exact header-only CSV with record
   count zero, while train remains non-empty.
7. `messages` fails on dry run, execution, and source-bound verification before
   destination access or publication, and the actionable error names both
   `split-jsonl-directory` v1 and `json` v1.
8. Request v1 works across Python, CLI, MCP, and the CLI-backed Mac bridge;
   request v2 fails before source or destination access.
9. Repeated rendering produces the same exact tree and plan. Every-file tamper,
   missing and unexpected paths, receipt/source/plan mismatch, membership
   mutation, payload/provenance mismatch, and reconstructed row-set drift fail
   verification.
10. Python 3.11, 3.12, and 3.13 evidence demonstrates that explicit dialect
    configuration produces identical golden bytes.

The Phase 5.3 admission and PR #55 publication records satisfy the items above,
including GitHub's Python 3.11–3.13 matrix. The local Python 3.12, release,
parity, Mac, tracking, and review results are recorded in the completed Phase 5
evidence packet.

Phase 5.5 adds a test-only consolidated semantic round-trip fixture matrix. It
reloads this container's ordinary files for all three compatible flat row
schemas and reconstructs the identical ordered train and evaluation payloads,
complete provenance, and source `RowSet` identity. The same suite proves one
canonical semantic tamper fails and that nested `messages` remains the sole
incompatible current pairing, with actionable split-JSONL and canonical-JSON
alternatives before publication. It does not use the permissive ingest CSV
parser or add a product importer, semantic replayer, API, taxonomy entry,
support promotion, or trainer claim. This consolidation does not weaken the
container-specific admission evidence required here; Phase 5.3 was promoted
only after that evidence was recorded.

Phase 5.5 merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1`. Phase 5.6 adds only the shared
runtime preview defined by Verified Export Contract v1 for compatible flat
schemas: ordinal-zero samples for non-empty partitions and this unchanged
plan-derived tree plus `export-receipt.json`. Nested `messages` retains its
actionable refusal before preview success. Preview does not invoke this
renderer or change these bytes, paths, schemas, or support claims.

## Dependency, license, security, and resource boundary

The renderer uses the Python standard-library CSV machinery only with every
dialect value explicitly supplied, plus Veriformis's canonical row and export
services. It adds no third-party serialization dependency and does not infer or
grant a content license. Source license and trust facts remain governed by the
authoritative bundle and mandatory provenance.

All operation remains local and offline. The shared request, response, plan,
tree-depth, descriptor-walk, no-link, no-replace, cancellation, and partial-
publication bounds remain normative. The two-render exact-byte proof can hold
two complete byte trees in memory; v1 makes no large-scale performance or
memory claim.

## Versioning, migration, and deprecation

The ten persisted `veriformis.verified-export` v1 models, request v1, response
v1 for non-dry-run operations, discovery v1, Finished Dataset v1, and source
bundle remain unchanged. Dry run uses the shared runtime-only response v2 and
preview v1; they do not change this container contract or persisted evidence.

Changing the supported row schemas, field mapping or order, dialect, encoding,
byte-order-mark policy, quoting or escape rules, record terminator, null or
empty-string semantics, fixed tree, data-card fields, provenance alignment,
determinism claim, selector meaning, or trainer-compatibility statement
requires a new container, dialect, or data-card contract version and migration
fixtures. V1 remains readable and verifiable while supported. Any future
deprecation requires an announced replacement and a retained verifier; silent
reinterpretation is forbidden.

## Non-goals

- Encoding nested messages, arbitrary JSON, lists, or objects in CSV cells.
- Choosing a recipe, objective, tokenizer, prompt template, masking policy, or
  trainer.
- Claiming compatibility with a spreadsheet or trainer merely because it reads
  CSV.
- Rewriting formula-looking strings or other values for one spreadsheet.
- Configurable filenames, delimiter, quoting, encoding, line endings,
  provenance, or other container options.
- Combining evaluation with train or creating another logical partition.
- Adding row identity, split group, or provenance fields to payload records.
- Mutating the source bundle or workspace.
- Network publication, replacement, signing, or notarization.
