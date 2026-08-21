# Verified Export Contract v1

**Contract ID:** `veriformis.verified-export`

**Contract version:** `1`

**Execution profile:** `offline-deterministic-v1`

**Roadmap scope:** Independent-product Phase 4

**Implementation status:** Phase 4.2 implements the strict persisted models in
this contract, and Phase 4.3 implements fail-closed read-only source-trust
admission. It does not implement an export writer, publisher, independent
export verifier, CLI or MCP export commands, workbench export controls, or a
supported product export container. Plan population also remains deferred.

**Last reviewed:** 2026-08-21 (Phase 4.3 source-trust admission)

**Next review:** Phase 4.4 complete source/output binding or any export schema
change

## Purpose

This contract defines the portable identities and persisted evidence graph for
derivatives of one verified Veriformis finished bundle. The sealed
`minimal-v1` bundle remains the canonical product artifact. An export is a
receipt-bound derivative; it is not a second construction, curation,
balancing, splitting, or validation pipeline.

The Phase 4.2 implementation is models only. It establishes exact plans,
profiles, dependency bindings, file expectations, membership projections,
receipts, and successful-verification evidence so later Phase 4 increments can
implement one shared service without inventing incompatible persistence.
Phase 4.3 adds only the read-only source admission policy described below; it
does not populate a plan or create derivative files.

## Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` are normative terms.
Persisted values and executable model checks control behavior. Prose does not
permit a weaker interpretation.

## Product boundary

The governed relationship is:

```text
verified minimal-v1 bundle + explicit source-trust policy
  -> immutable export plan
  -> planned derivative files
  -> receipt-bound closed derivative tree
  -> independent export verification
```

The source bundle remains unchanged. Exporters MAY rename, map, package, or
emit approved sidecars under an exact profile. They MUST NOT construct targets,
curate, balance, filter, resplit, repartition, infer new semantics, or silently
change record membership. A membership or target change requires a new
compiled dataset plan and canonical bundle.

This contract does not change the finished-dataset schemas, the strict
six-file `minimal-v1` set, the dataset taxonomy, or any existing bundle digest.
An export receipt lives in the derivative tree, never in the source bundle or
workspace.

## Contract and schema identifiers

The following identifiers and identity domains are exact:

| Persisted value | Schema identifier | Identity field | Identity kind |
| --- | --- | --- | --- |
| Export container profile | `veriformis.export-container-profile/v1` | `container_profile_id` | `export-container` |
| Export consumer profile | `veriformis.export-consumer-profile/v1` | `consumer_profile_id` | `export-consumer` |
| Export dependency binding | `veriformis.export-dependency-binding/v1` | `dependency_id` | `export-dependency` |
| Export file plan | `veriformis.export-file-plan/v1` | `file_plan_id` | `export-file-plan` |
| Export destination file binding | `veriformis.export-destination-file-binding/v1` | `destination_file_id` | `export-file` |
| Export membership entry | `veriformis.export-membership-entry/v1` | `membership_entry_id` | `export-membership-entry` |
| Export membership projection | `veriformis.export-membership-projection/v1` | `membership_projection_id` | `export-membership` |
| Export plan | `veriformis.export-plan/v1` | `export_plan_id` | `export-plan` |
| Export receipt | `veriformis.export-receipt/v1` | `export_receipt_id` | `export-receipt` |
| Export verification | `veriformis.export-verification/v1` | `export_verification_id` | `export-verification` |

The derivative receipt path is exactly `export-receipt.json` in v1.

Every identity uses the existing domain-separated `derive_id()` substrate over
the complete exact model value except its own identity field. Nested models are
included in their parent identity payloads. Loaders MUST recompute every nested
and parent identity before accepting a value.

Two persisted digest fields use exact non-model domains. Both apply SHA-256 to
the lossless canonical JSON bytes of the stated object:

- `assignment_projection_sha256` uses
  `{"schema_version":"veriformis.export-assignment-projection/v1","entries":[...]}`.
  Each ordered entry object contains exactly `record_id`, `assignment_id`,
  `leakage_group_id`, `partition`, and `ordinal`.
- `output_content_root_sha256` uses
  `{"schema_version":"veriformis.export-content-root/v1","files":[...]}`.
  `files` contains each complete `ExportDestinationFileBinding` JSON object in
  exact path order.

These are digest-domain identifiers, not additional persisted model schemas,
so they are not members of the ten-entry schema registry.

## Canonical serialization and strict loading

Every persisted export model is strict, frozen, exactly fielded, and versioned.
Its unique byte representation is lossless UTF-8 JSON with:

- object keys sorted lexicographically;
- compact `,` and `:` separators;
- exact Unicode strings with `ensure_ascii=false`;
- no byte-order mark and no trailing line feed; and
- no floating-point or non-finite values.

No general string normalization, trimming, case folding, or rewriting is
permitted. Fields whose contracts define restricted labels or paths apply only
their field-specific validation.

Public byte loaders MUST reject:

- a non-byte input or a JSON root other than one object;
- invalid UTF-8, duplicate JSON keys, floats, and non-finite numbers;
- missing fields, unknown fields, wrong primitive types, and Boolean/integer
  coercion;
- an unsupported schema identifier or closed literal;
- malformed, duplicate, or inconsistent identities and SHA-256 values;
- noncanonical key order, separators, escaping, or other byte encodings;
- invalid nested values or cross-references; and
- any identity mismatch or non-exact round trip.

`canonical_bytes()` MUST cross a fresh strict validation boundary.
`from_json_bytes()` MUST accept only the one canonical representation and MUST
report malformed persisted evidence as `export-verification-invalid`.
Strict constructors reject invalid in-memory values with validation failure.
`export-contract-invalid` is the typed envelope for canonical serialization
failure and for an invalid or unsatisfied source-trust policy.
`export-verification-invalid` covers an impossible mismatch between the
inspector result and the evidence supplied to the export service. Malformed,
mismatched, or tampered bundle evidence preserves the existing
`bundle-invalid` envelope; the service never retries without supplied evidence.

The closed verified-export v1 error-code registry is exactly:

- `export-contract-invalid`; and
- `export-verification-invalid`.

## Portable paths and identity exclusions

All persisted file paths are destination-root-relative POSIX paths. A path MUST
already be NFC-normalized and MUST NOT be rewritten silently. Both its exact
form and its NFKC compatibility form MUST remain safe. Validation rejects empty
paths, absolute paths, Windows drive paths, backslashes, compatibility
characters that introduce separator aliases, NUL, control and format
characters, empty segments, `.` and `..`,
Windows-forbidden filename characters, trailing spaces or periods, Windows
device names, file/ancestor conflicts, duplicate paths, and portable collisions
under NFKC plus case folding. The portable collision rule is NFKC plus case
folding.

The absolute destination root is a runtime argument and MUST NOT appear in a
portable model or identity. Clocks, random values, process IDs, workspace
revision IDs, temporary names, host-specific paths, cancellation state, and
durability warnings likewise MUST NOT enter a plan, receipt, verification, or
their identities.

## Profile and dependency models

### `ExportContainerProfile`

An export container profile contains exactly `schema_version`,
`container_profile_id`, `container_id`, `container_version`, and
`determinism_claim`.

`container_id` is a lowercase canonical selector and `container_version` is a
positive integer. `determinism_claim` is exactly one of:

- `portable_exact_bytes`: identical semantic inputs require the exact planned
  bytes; or
- `semantic_content_only`: exact bytes are bound for the produced instance,
  but portable reproducibility is claimed only for canonical semantic content.

Defining this model does not add its `container_id` to product taxonomy or
support discovery. The Phase 4 conformance container is injected by tests and
is not a supported product container.

### `ExportConsumerProfile`

An optional consumer profile contains exactly `schema_version`,
`consumer_profile_id`, `consumer_id`, `profile_version`, and
`accepted_row_schemas`.

`consumer_id` is a lowercase canonical selector and `profile_version` is a
positive integer.

The accepted row schemas MUST be non-empty, sorted, unique, and drawn from the
shipped taxonomy. A plan using the profile MUST use one of those schemas. This
model can express a restriction; it does not register, implement, or advertise
a trainer integration.

### `ExportDependencyBinding`

A dependency binding contains exactly `schema_version`, `dependency_id`,
`dependency_name`, `dependency_version`, and `dependency_role`. Names and roles
are lowercase canonical labels. The version is an exact non-empty string with
no leading or trailing whitespace, NUL, control, or Unicode format characters.
Plan dependencies are sorted by `dependency_id`, have unique identities, and MUST
not repeat a dependency name. Every plan MUST bind at least one dependency;
an empty tuple is ambiguous rather than evidence that no dependency exists.

## File plans and destination bindings

### `ExportFilePlan`

A file plan contains exactly `schema_version`, `file_plan_id`, `path`, `role`,
`media_type`, `membership_scope`, `record_count`,
`semantic_content_sha256`, `expected_sha256`, and `expected_byte_size`.

`membership_scope` is `none`, `train`, `evaluation`, or `all`. A
membership-bearing file requires an exact non-negative `record_count`.
`expected_sha256` and `expected_byte_size` are either both present or both
absent. A zero expected size MUST bind the SHA-256 of empty bytes, and a
positive record count cannot have a zero expected size.

The role is a lowercase canonical label and the media type is a lowercase
canonical MIME type.

For a `portable_exact_bytes` profile, every file plan MUST contain
`expected_sha256` and `expected_byte_size` and MUST set
`semantic_content_sha256` to null. For a `semantic_content_only` profile, every
file plan MUST contain `semantic_content_sha256` and MUST set both exact-byte
expectations to null.

### `ExportDestinationFileBinding`

A destination binding contains exactly `schema_version`,
`destination_file_id`, `file_plan_id`, `path`, `role`, `media_type`,
`membership_scope`, `record_count`, `semantic_content_sha256`, `sha256`, and
`byte_size`.

The role is a lowercase canonical label and the media type is a lowercase
canonical MIME type.
It always binds the actual SHA-256 and byte size of one produced file. Its
logical descriptors and record count MUST match its named file plan. An
exact-byte receipt requires actual bytes to equal the plan expectations. A
semantic-only receipt requires the observed semantic-content digest to equal
the planned semantic-content digest; the actual instance byte digest remains
bound without being called portably reproducible. An observed zero-byte file
MUST bind the SHA-256 of empty bytes, and a positive record count cannot occupy
zero bytes.

File plans and destination bindings are sorted by exact path. Their complete
path set MUST be portable and collision-free. `export-receipt.json` is reserved
and cannot collide with a planned output.

## Complete membership projection

### `ExportMembershipEntry`

One membership entry contains exactly `schema_version`,
`membership_entry_id`, `record_id`, `row_id`, `provenance_id`,
`assignment_id`, `leakage_group_id`, `partition`, `ordinal`, and
`payload_sha256`.

The entry binds one source record and product row to its aligned provenance,
authoritative assignment, complete leakage group, exact `train` or
`evaluation` partition, zero-based partition ordinal, and canonical source-row
payload digest.

### `ExportMembershipProjection`

A membership projection contains exactly `schema_version`,
`membership_projection_id`, `split_result_id`, `row_set_id`, `row_schema`,
`assignment_projection_sha256`, and `entries`.

The projection is non-empty and requires a non-empty train partition. Entries
are ordered as every train ordinal followed by every evaluation ordinal, with
each partition contiguous from zero. Membership-entry, record, row,
provenance, and assignment identities are each globally unique. The assignment
projection digest binds the ordered `(record_id, assignment_id,
leakage_group_id, partition, ordinal)` sequence.

Every occurrence of one `leakage_group_id` MUST remain in one partition. A
leakage group that appears in both train and evaluation fails closed.

The projection models the complete derivative-only boundary. Phase 4.2 makes
that boundary representable and identity-checked; Phase 4.5 will reconstruct it
from source and destination content and reject every membership mutation.

## Source-trust admission

`ExportService.verified_source` is the only implemented export-source
admission operation. Its default `source_trust_policy` is exactly
`require_external_digest`. Under that policy, the caller MUST supply the
separately retained expected manifest SHA-256; absence fails before the source
path is resolved or inspected.

Self-consistent admission requires the caller to select exactly
`allow_self_consistent`. With no expected digest, successful inspection records
the exact `self_consistent` grade in the returned `VerifiedFinishedBundle`.
Supplying an expected digest under either policy keeps that evidence
authoritative: a match records `external_digest`, while malformed or mismatched
evidence fails without retry, downgrade, trimming, or coercion.

The returned grade MUST correspond exactly to whether external evidence was
supplied. When a digest was supplied, the returned manifest digest MUST equal
it. Any impossible inspector result that violates either postcondition fails
as `export-verification-invalid`; the service never relabels the result.

The verified source records the observed grade, not the requested policy.
Phase 4.4 plan population will persist both the caller's exact policy and the
observed grade in `ExportPlan`. Ordinary bundle inspection and verification
remain capable of explicitly graded self-consistent operation; the secure
default here applies only to export-source admission.

## `ExportPlan`

An export plan contains exactly:

- `schema_version` and `export_plan_id`;
- source `bundle`, manifest, content-root, and verification identities or
  SHA-256 values;
- `source_trust_policy` and the observed `source_trust_grade`;
- dataset snapshot, validation report, finished-dataset plan, recipe,
  objective, construction, curation, serialization, split, and row-set
  identities;
- non-empty sorted unique source identities, the exact row schema, and its shipped loss
  policy;
- `derivative_policy`, fixed to `preserve_membership_and_semantics`;
- one container profile and an optional consumer profile;
- ordered dependency bindings;
- one complete membership projection;
- ordered file plans; and
- `overwrite_policy`, fixed to `refuse`.

The source identifiers are bindings to existing immutable finished-dataset
semantics, not copies that an exporter may reinterpret. The plan row schema
MUST match its membership projection and the shipped taxonomy loss policy. Its
split and row-set identities MUST match the projection. A consumer profile, if
present, MUST accept the row schema.

The plan MUST recompute the shipped `veriformis.bundle-verification/v1`
identity from its bundle, snapshot, validation-report, manifest, content-root,
trust-grade, four-payload-file, and complete record-count facts. The persisted
`source_verification_id` MUST equal that recomputed identity; copying an
unrelated but well-formed verification ID fails closed.

`source_trust_policy` is exactly `require_external_digest` or
`allow_self_consistent`; `source_trust_grade` is exactly `external_digest` or
`self_consistent`. A plan requiring an external digest MUST already name an
`external_digest` verification grade. The service-level admission rule requires
lower trust to be intentionally requested before Phase 4.4 plan population.

The membership-bearing file layout is closed: it is either one `all` file, or
exactly one `train` file plus one `evaluation` file. Each planned record count
MUST equal the corresponding complete membership count. No plan field permits
filtering, balancing, target construction, partition selection, or resplitting.

## `ExportReceipt`

An export receipt contains exactly `schema_version`, `export_receipt_id`,
`export_plan_id`, the complete nested `export_plan`,
`output_content_root_sha256`, and ordered destination `files`.

The explicit plan ID MUST equal the embedded plan identity. Destination
bindings MUST cover the complete planned file set exactly once and match every
logical and evidence expectation. The output content root is a
domain-separated digest over the complete ordered destination bindings.

The receipt does not bind its own bytes. The intended closed derivative tree is
the exact destination file set plus one canonical `export-receipt.json`; this
avoids an impossible self-hash while keeping the receipt inside the portable
wrapper.

## `ExportVerification`

An export verification contains exactly `schema_version`,
`export_verification_id`, receipt and plan identities, complete source bundle
and trust bindings, dataset snapshot and validation identities, split and
row-set identities, row schema, profile identities, membership projection
identity, determinism claim, output content root, output file count, and
declared record count.

It represents successful verification evidence only. A failed, malformed,
altered, incomplete, unexpected, or untrusted derivative raises a typed error
instead of producing a persisted `verified=false` object. Phase 4.2 defines and
strictly loads this evidence model. Independent filesystem verification,
source re-verification, closed-tree enforcement, and exact/semantic replay are
implemented in later Phase 4 increments.

Successful verification requires positive `output_file_count` and
`declared_record_count` values. Counts of zero do not describe a successful v1
derivative. The verification MUST independently recompute
`source_verification_id` from its complete flattened source bindings and reject
an unrelated source-verification identity.

## Phase 4.2–4.3 implementation boundary

Phase 4.2 implements:

- the ten versioned models and exact schema/identity domains above;
- the two typed error codes in the closed Phase 4.2 error registry;
- canonical lossless JSON serialization and strict byte loading;
- portable relative-path and closed path-set validation;
- model-local identity, ordering, reference, trust-pairing, evidence-mode,
  membership, file-set, receipt, and count invariants; and
- malformed, unsupported-version, duplicate-key, float, Unicode, identity,
  ordering, and canonical round-trip contract tests.

Phase 4.3 additionally implements:

- trusted-by-default export-source admission in `ExportService`;
- an explicit `allow_self_consistent` lower-trust policy;
- exact observed trust-grade and retained-digest postcondition checks; and
- fail-closed missing, malformed, mismatched, tampered, and impossible trust
  evidence tests before any destination operation exists.

Phase 4.2–4.3 do **not** implement:

- selecting or registering an export implementation;
- verified-source-to-plan population and complete runtime binding checks
  (Phase 4.4);
- destination membership reconstruction (Phase 4.5);
- filesystem staging, writing, cancellation, promotion, cleanup, or independent
  export verification (Phase 4.6);
- deterministic rerendering or semantic-content replay (Phase 4.7);
- Python composition-root export operations, discovery, dry run, inspection,
  CLI, MCP, or Mac surfaces (Phase 4.8); or
- the complete tamper, traversal, race, cancellation, and partial-publication
  harness or Phase 4 closeout (Phase 4.9).

## Support and discovery

Persisted profile selectors and a test-injected conformance implementation are
not support claims. Phase 4.2–4.3 MUST NOT add a generic export container or
consumer profile to taxonomy discovery or the support registry. The existing
`minimal-v1` bundle and deterministic bundle transport remain the only shipped
physical containers. Generic split JSONL, JSON, and CSV remain Phase 5 work;
named trainer profiles remain later work.

## Version and migration

Unknown schemas and versions fail closed. Changing the meaning, field set,
identity payload, ordering rule, trust literal, evidence claim, membership
projection, or receipt boundary of any v1 model requires a new schema version
and migration tests. Historical finished-bundle, transport, and handoff
contracts remain readable through their own loaders and are not reinterpreted
by this contract.

## Non-goals

- Adding any generic production export container.
- Claiming Aptus, MLX-LM, TRL, or another trainer profile.
- Changing `minimal-v1`, its six-file closed set, or its verifier contract.
- Adding an export workspace stage or mutating workspace history.
- Force replacement, in-place replacement, network publication, signing, or
  notarization.
- Declaring beta, public-ready, or production maturity.
