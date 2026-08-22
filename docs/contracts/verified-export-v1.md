# Verified Export Contract v1

**Contract ID:** `veriformis.verified-export`

**Contract version:** `1`

**Execution profile:** `offline-deterministic-v1`

**Roadmap scope:** Independent-product Phase 4

**Implementation status:** Phase 4.2 implements the strict persisted models in
this contract, Phase 4.3 implements fail-closed read-only source-trust
admission, and Phase 4.4 implements read-only source-derived plan population.
Phase 4.5 implements read-only normalized semantic membership reconstruction
and exact comparison with the plan baseline. Phase 4.6 implemented
exact-byte-only atomic publication and descriptor-anchored independent tree
verification and merged as PR #48 at
`3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`. Phase 4.7 implements
private two-render evidence for both determinism claims and descriptor-anchored
semantic replay and merged as PR #49 at
`6c3f0aff2e35edaa7920a0964270c410bf53f47b`. Phase 4.8 implements the
strict Python, CLI, MCP, and CLI-backed Mac surface boundary over a private
production-empty catalog and merged as PR #50 at
`fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`; its review corrections merged as
PR #51 at `d91542fe12c5a492de578ad060836a7d65999e42`. Phase 4.9 completes the
consolidated adversarial harness and closeout without changing a persisted
schema. Phase 4 did not implement a public renderer or replayer registry or a
supported product export container. Phase 5.1 adds one reviewed internal
`split-jsonl-directory` v1 implementation and an additive configured request
v2 surface; the ten persisted models, discovery v1, and response v1 remain
unchanged.

**Last reviewed:** 2026-08-21 (Phase 5.1 split JSONL admission)

**Next review:** Phase 5.2 or any export schema change

## Purpose

This contract defines the portable identities and persisted evidence graph for
derivatives of one verified Veriformis finished bundle. The sealed
`minimal-v1` bundle remains the canonical product artifact. An export is a
receipt-bound derivative; it is not a second construction, curation,
balancing, splitting, or validation pipeline.

The Phase 4.2 implementation establishes exact models for plans,
profiles, dependency bindings, file expectations, membership projections,
receipts, and successful-verification evidence so later Phase 4 increments can
implement one shared service without inventing incompatible persistence.
Phase 4.3 adds only the read-only source admission policy described below; it
does not create derivative files. Phase 4.4 adds read-only plan population from
one admitted source and binds the source membership baseline; it does not
render, compare, or publish destination content. Phase 4.5 reconstructs
normalized candidate semantic rows and provenance in memory and requires exact
equality with that baseline; it does not inspect or publish destination bytes.
Phase 4.6 re-verifies the source and plan, accepts bytes only from a private
test-injected conformance renderer, repeats the semantic membership check,
independently verifies a staged exact-byte tree, and publishes it with one
no-replace atomic promotion. Phase 4.7 invokes that private renderer twice from
fresh strict inputs. Exact-byte profiles require equal normalized byte trees;
semantic-only profiles require equal profile-versioned canonical semantic
preimages reconstructed by a private replayer. Semantic publication replays
the descriptor-reread staged bytes again before promotion.

## Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` are normative terms.
Persisted values and executable model checks control behavior. Prose does not
permit a weaker interpretation.

## Product boundary

The governed relationship is:

```text
verified minimal-v1 bundle + explicit source-trust policy
  -> immutable export plan
  -> normalized candidate semantic membership check
  -> two-render deterministic evidence
  -> planned and replayed derivative files
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
failure, an invalid or unsatisfied source-trust policy, invalid publication
arguments, an unsupported publication evidence mode, or a destination already
present before staging. `export-verification-invalid` covers an impossible
mismatch between the inspector result and supplied evidence, invalid renderer
evidence, or a malformed, altered, incomplete, or substituted derivative tree.
Malformed, mismatched, or tampered bundle evidence preserves the existing
`bundle-invalid` envelope; the service never retries without supplied evidence.
An atomic no-replace race may preserve the platform `FileExistsError`.
Cancellation-check exceptions propagate before visibility, and the runtime
partial-publication exception is outside this persisted error-code registry.

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

Generic filesystem verification directly observes file type, path, SHA-256,
and byte size. Role, media type, membership scope, and record count remain
logical plan-and-receipt facts until a container-specific semantic replay can
derive them from produced bytes. Exact-byte publication MUST NOT describe those
logical facts as independently counted or parsed destination evidence.

File plans and destination bindings are sorted by exact path. Their complete
path set MUST be portable and collision-free. `export-receipt.json` is reserved
and cannot collide with a planned output.

### Canonical semantic preimages

For `semantic_content_only`, `semantic_content_sha256` is exactly the SHA-256
of the canonical semantic preimage reconstructed for one planned file. It is
not a digest supplied by a renderer or replayer and MUST NOT be copied from the
plan into a destination binding without replaying the produced bytes. The
export service computes the digest from the returned preimage bytes.

Every semantic-capable container profile MUST define a versioned, independently
reproducible preimage format for every planned file. That definition MUST bind
the exact container profile and dependencies, path, role, media type,
membership scope, record count, row schema, logical partition interpretation,
sequence order, and canonical file content. It MUST also define exact Unicode,
duplicate-value, number, key-order, list-order, and invalid-input behavior. A
`membership_scope=none` file still requires a canonical profile-defined
preimage and matching digest; it contributes no row membership. The Phase 4.7
conformance fixture is statically bounded. Before any semantic profile is
shipped or publicly exposed, its versioned contract MUST define and enforce
explicit byte, record, nesting, and other applicable resource limits and fail
closed when content cannot be reconstructed uniquely. The private Phase 4.7
callback does not expose a configurable resource-limit argument.

The Phase 4 conformance profile uses a versioned lossless canonical JSON
preimage. A profile MAY use another canonical byte representation only when its
container version and exact renderer/replayer dependency bindings define that
representation without ambiguity. Changing canonicalization requires a new
container version or dependency identity. No unversioned, host-dependent, or
library-default serialization is semantic evidence under this contract.

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

The projection models the complete derivative-only boundary. Phase 4.4 derives
the source baseline from the verified row set. Phase 4.5 reconstructs a
candidate row set and projection from normalized semantic rows plus aligned
provenance and rejects every mismatch with that baseline. Actual destination-
byte reconstruction is a separate Phase 4.7 replay boundary; a semantic
replayer's reconstructed rows and provenance are candidate evidence and MUST
pass the same complete membership comparison.

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
Phase 4.4 plan population persists both the caller's exact policy and the
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

### Read-only plan population

`ExportService.create_plan` is the only implemented plan-population operation.
It MUST call `verified_source` exactly once and MUST derive every source fact
from the returned immutable `VerifiedFinishedBundle`. Beyond the source bundle
locator, callers supply only the container profile, optional consumer profile,
dependency bindings, file plans, and the source trust policy and evidence used
for admission. They MUST NOT supply or override source identities, row or
objective facts, split facts, or membership entries.

The service MUST re-close the manifest, verification result, validation report,
dataset snapshot, row set, and aligned provenance before creating a plan. It
derives the complete source membership baseline in authoritative partition and
ordinal order. Each entry binds the source record, row, provenance, assignment,
leakage group, partition, ordinal, and payload digest. The service also derives
the one objective identity and complete source-ID scope from that aligned
evidence. Missing, inconsistent, or substituted verified-source facts fail as
`export-verification-invalid`; invalid caller-supplied profile, dependency, or
file-plan evidence fails as `export-contract-invalid`.

This source projection is the immutable comparison baseline. Phase 4.5
independently reconstructs normalized candidate semantic membership and
compares it with this baseline. It does not claim that produced destination
bytes have been parsed or independently replayed.

For `portable_exact_bytes`, each populated file plan binds its expected byte
SHA-256 and byte size. For `semantic_content_only`, each populated file plan
binds the semantic-content SHA-256 and leaves exact-byte expectations null; the
actual produced-instance SHA-256 and byte size belong to the destination
binding and receipt after writing. Plan population accepts no absolute
destination root and performs no filesystem write, staging, promotion, receipt,
or destination verification operation.

### Read-only derivative membership enforcement

`ExportService.validate_derivative_membership` accepts exactly one strict
`ExportPlan`, candidate train rows, candidate evaluation rows, and one aligned
candidate provenance sequence. It returns an `ExportMembershipProjection` only
after exact validation succeeds. It accepts no membership projection, include,
exclude, filter, balance, ratio, seed, partition, resplit, target, destination-
root, overwrite, writer, or publication argument.

The candidate train and evaluation sequences define the logical partitions.
The provenance sequence MUST contain the train entries followed by the
evaluation entries and MUST agree with each sequence-derived partition and
zero-based ordinal. This rule remains exact when a later physical container
combines both logical partitions into one file.

The service MUST fresh-strict-load the plan and every candidate `ProductRow` and
`RowProvenance`. Using only identities already bound by the plan, it MUST build a
candidate `RowSet` whose canonical row and provenance bytes, counts, digests,
ordering, and identity close. The candidate objective and complete source-ID
scope MUST equal the plan. The computed candidate `row_set_id` MUST equal the
plan's `row_set_id`.

The service then MUST derive a complete candidate membership projection from
that checked row set. The candidate projection and its canonical bytes MUST
equal the plan's complete source membership projection. Counts or
`assignment_projection_sha256` alone are insufficient because the complete
comparison also binds row, provenance, and payload identities. Omission,
addition, duplication, reordering, filtering, coherent target mutation,
assignment or leakage-group substitution, balancing, repartitioning, and
resplitting all fail as `export-verification-invalid`; failure never returns a
persisted false result or a partial projection.

Candidate rows and provenance are normalized in-memory semantic evidence, not
caller selection controls and not produced-file evidence. Phase 4.5 performs no
filesystem read or write, creates no destination binding or receipt, and does
not prove that arbitrary destination bytes encode the checked semantics. Phase
4.6 owns filesystem publication and Phase 4.7 owns exact-byte rerendering or
semantic reconstruction of actual destination content.

## Deterministic publication evidence

`ExportService.publish` accepts one strict `ExportPlan`, the source bundle
locator, one runtime destination root, an optional separately retained expected
source-manifest SHA-256, and an optional cancellation checkpoint callable. It
has no renderer-selection, overwrite, filter, membership, resplit, or semantic-
mapping argument. The default service has no installed renderer. Only a private
test conformance subclass may override the internal rendering and semantic-
replay hooks. The renderer receives a strict plan and freshly reconstructed
source row set, not a destination or staging path. The semantic replayer
receives a strict plan and one immutable complete `(path, bytes)` tree, not a
destination path, separately supplied digest, or caller-selected membership.

Before rendering or destination creation, the service MUST fresh-strict-load
the plan and reverify the named source bundle under the plan's exact trust
policy. An `external_digest` plan requires the caller to supply the separately
retained matching manifest digest again. The digest copied into the plan
MUST NOT be used as its own external trust anchor. Supplying external evidence for a
`self_consistent` plan cannot silently upgrade it; the caller must create a new
plan. Every reconstructed source, profile, dependency, file-plan, and complete
membership fact MUST equal the supplied plan exactly.

The internal renderer returns exact `(path, bytes)` pairs plus normalized train
rows, evaluation rows, and aligned provenance. The service MUST snapshot and
validate the complete renderer file set before creating staging: paths are
exact strings, contents are exact bytes, every planned path appears once, and
no other path appears. It MUST run the Phase 4.5 membership operation over the
returned semantic evidence. Renderer-supplied rows and provenance remain
separate from the byte tree and do not prove that arbitrary bytes encode them.

The service MUST invoke the renderer twice before destination access. Each
invocation receives independently strict-reloaded plan and source-row-set
objects reconstructed from the same canonical bytes. It MUST normalize both
complete trees into exact plan-path order and validate the returned membership
from each invocation. Renderer sequence order is not meaningful after path
normalization; path identity and file contents remain exact.

For `portable_exact_bytes`, every rendered file MUST match its planned SHA-256
and byte size, and the two normalized `(path, bytes)` trees MUST be identical.
Only the first tree proceeds to staging. A second-render difference fails as
`export-verification-invalid` before destination access and MUST NOT downgrade
to semantic-only evidence. This proves repeatable bytes under the bound profile
and dependencies; it does not independently decode those bytes into rows.

For `semantic_content_only`, exact bytes, SHA-256 values, and sizes MAY differ
between the two renders. The private profile-specific replayer MUST reconstruct
the complete canonical semantic-preimage tree and normalized train rows,
evaluation rows, and aligned provenance from each produced byte tree. Each
reconstructed membership view MUST pass the Phase 4.5 comparison, every
service-computed preimage digest MUST equal its file plan, and the two complete
canonical semantic-preimage trees MUST be identical. Only the first physical
tree proceeds to staging. Missing replay support, an incomplete or ambiguous
replay, or any semantic, membership, path, or digest difference fails closed.

Semantic publication MUST replay independently reread staged bytes through the
same profile-bound private replayer before receipt verification and promotion.
The staged replay MUST reproduce the complete preflight semantic-preimage tree
and membership evidence. A hook cannot attest success by returning a digest:
the service hashes its canonical preimage bytes. The exact renderer and
replayer dependencies MUST remain bound by the plan.

Publication MUST:

1. reject an invalid destination, a symlink parent, a destination inside the
   source bundle, and every pre-existing destination object;
2. create one private mode-0700 sibling on the destination filesystem;
3. create directories and files through anchored descriptors with exclusive,
   no-follow writes, checking cancellation before and during fallible work;
4. write and fsync every planned file and the canonical
   `export-receipt.json`, then fsync every staged directory;
5. independently enumerate the staged tree through its root descriptor and
   require the exact planned directories and files plus the receipt, and for a
   semantic-only plan replay descriptor-reread staged bytes before constructing
   successful verification evidence;
6. reject aliases, collisions, symlinks, hard links, shared inodes, special
   files, substitutions, noncanonical receipt bytes, or any observed
   digest/size/plan/receipt mismatch;
7. construct successful `ExportVerification` evidence only from that
   independently reloaded receipt and observed byte bindings;
8. repeat the closed-tree check and cancellation checkpoint immediately before
   publication; and
9. use one platform atomic no-replace directory promotion, with no unsafe
   fallback and no adoption or overwrite of an existing target.

These atomicity and cleanup guarantees assume that the destination parent is
an integrity-controlled namespace. No uncooperative process with the same
owner privileges may continuously rename or replace entries in that parent
during publication. Veriformis anchors work to directory descriptors, checks
name-to-inode identity, promotes with no-replace semantics, and removes only
objects whose identities it recorded as service-owned. If a name is replaced,
cleanup fails closed and may preserve staging residue rather than adopting or
recursively deleting the replacement. OS permission isolation defines this
security boundary; a separately retained source-manifest digest and the
out-of-band expected export plan detect later source or derivative
substitution.

A cancellation-check exception before promotion propagates after cleanup of
only the descriptor-anchored staging tree. The destination remains absent
unless another process won the no-replace race.
There is no cancellation checkpoint after promotion, and visible output MUST
NOT be deleted or reported as rolled back. Cleanup refuses a replaced staging
name rather than following or recursively deleting it.

`ExportPublicationOutcome` is a frozen runtime value containing the absolute
destination root, strict receipt, strict verification, and an optional
durability warning. The absolute path and warning are not persisted identity.
If parent-directory fsync fails after promotion, publication remains successful
and visible; the outcome carries a warning that warning filters cannot turn
into false rollback. `ExportPartialPublicationError` is a runtime exception
carrying the visible outcome and original cause if later bookkeeping fails. It
is not a persisted model or an additional verified-export v1 error code. Phase
4.8 exports both runtime types from `veriformis.exports` so Python callers can
type successful execution and catch visible-partial publication without
depending on an underscore-private module; publication hooks remain private.

The independently callable filesystem verifier requires an out-of-band
expected plan. It opens the visible root without following links, enforces the
same closed-tree rules, reloads canonical receipt bytes, recomputes every
actual file digest and size, and returns the matching receipt and verification.
For semantic-only output, the private conformance verifier additionally
requires the exact profile-bound replayer and recomputes canonical semantic
preimages from descriptor-read bytes; absent replay support fails closed. It
does not re-open the source bundle or rerender container bytes. Source
reverification is part of publication; source-bound standalone verification
and public inspect/verify surfaces are implemented by the Phase 4.8 service
boundary described below.

## `ExportReceipt`

An export receipt contains exactly `schema_version`, `export_receipt_id`,
`export_plan_id`, the complete nested `export_plan`,
`output_content_root_sha256`, and ordered destination `files`.

The explicit plan ID MUST equal the embedded plan identity. Destination
bindings MUST cover the complete planned file set exactly once and match every
logical and evidence expectation. The output content root is a
domain-separated digest over the complete ordered destination bindings.

The receipt does not bind its own bytes. The closed derivative tree is
the exact destination file set plus one canonical `export-receipt.json`; this
avoids an impossible self-hash while keeping the receipt inside the portable
wrapper. Publication writes and independently reloads this receipt inside
staging before the atomic promotion. No normal receipt-writing step follows
visibility.

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
strictly loads this evidence model. Publication creates it only after
independent filesystem enumeration, canonical receipt reload, closed-tree
enforcement, and actual file digest and size replay. Semantic-only publication
additionally requires descriptor-read semantic replay and comparison with the
planned and preflight canonical preimages. Creating the model from an in-memory
receipt alone is not evidence that a filesystem tree was inspected.

The service re-verifies the source while publishing. The private filesystem
verifier accepts an independently supplied plan and does not reopen the source
bundle; the Phase 4.8 public verification operation first re-derives that plan
from the selected internal implementation and independently verified source.

The persisted `determinism_claim` binds the container profile's claim; it is not
a persisted attestation that two renderer invocations occurred. The ten v1
schemas contain no rerender count, cross-render digest, or replay transcript.
Phase 4.7's two-render and staged-replay evidence is a runtime publication
admission procedure. Adding a durable rerender attestation would require a new
contract version. For semantic-only output, differing physical encodings can
therefore share one plan and semantic-content digests while producing different
actual file digests, output content roots, receipt identities, and verification
identities.

Successful verification requires positive `output_file_count` and
`declared_record_count` values. Counts of zero do not describe a successful v1
derivative. The verification MUST independently recompute
`source_verification_id` from its complete flattened source bindings and reject
an unrelated source-verification identity.

## Phase 4.2–4.9 implementation boundary

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

Phase 4.4 additionally implements:

- one read-only `ExportService.create_plan` operation over the existing trusted
  source-admission boundary;
- internally derived source, objective, row, split, and complete source
  membership-baseline bindings;
- caller-supplied container, optional consumer, dependency, and output-file
  planning evidence under the strict persisted models; and
- plan identity replay without destination-root or filesystem state.

Phase 4.5 additionally implements:

- one read-only normalized semantic membership operation in `ExportService`;
- fresh strict candidate row, provenance, row-set, and projection
  reconstruction;
- exact candidate row-set and complete projection comparison with the plan
  baseline; and
- fail-closed omission, addition, duplication, reordering, target mutation,
  assignment, leakage-group, partition, ordinal, balancing, and resplit tests.

Phase 4.6 was additionally implemented and merged as PR #48 at
`3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`:

- one Python-composition-only exact-byte publication operation with no shipped
  renderer or renderer-selection argument;
- source and plan re-verification before renderer or destination mutation;
- renderer file-set and normalized semantic membership validation before
  staging;
- descriptor-anchored private staging, cancellation, cleanup, fsync, exact
  closed-tree verification, and one atomic no-replace promotion;
- canonical in-tree receipts, successful verification evidence, an independent
  exact-byte directory verifier, and honest visible-publication outcomes; and
- fail-closed deferral of `semantic_content_only` publication to Phase 4.7.

Phase 4.7 was additionally implemented and merged as PR #49 at
`6c3f0aff2e35edaa7920a0964270c410bf53f47b`:

- two private renderer invocations from independent strict plan and source-row-
  set reconstructions, with complete membership validation for each;
- normalized complete-tree byte equality for `portable_exact_bytes` plans;
- private profile-versioned semantic replay for both independently rendered
  `semantic_content_only` trees, with service-computed digests and exact
  canonical-preimage and membership equality;
- descriptor-reread staged semantic replay before verification and promotion;
- deterministic plan, receipt, verification, and closed-tree conformance
  fixtures without a product renderer or support claim; and
- explicit persisted-evidence limits: v1 verification binds the profile claim
  and one published instance, not a durable rerender transcript.

Phase 4.8 additionally implements:

- a private, immutable, default-empty implementation catalog selected by exact
  container and optional consumer identifiers and versions;
- `PipelineService` export operations for discovery, destination-free dry run,
  self-described physical inspection, operator-confirmed execution, and source-
  bound verification;
- strict canonical `veriformis.export-surface-request/v1` and
  `veriformis.export-surface-response/v1` transport envelopes for CLI, MCP, and
  the CLI-backed Mac bridge; and
- cooperative cancellation and explicit `ok`, `error`, `cancelled`, and
  `visible_partial` runtime statuses without changing persisted evidence.

Phase 4.9 additionally implements one consolidated adversarial harness over a
private, test-injected exact conformance implementation. It proves canonical
contract and identity replay; tamper and unexpected-file rejection; traversal,
Unicode/case-alias, link, special-file, and destination-race refusal; source-
digest and source-tamper refusal before visibility; complete membership-mutation
failure including ordinal mutation; final cancellation ordering; and honest,
independently verifiable visible-partial reporting. Balancing has no independent
export representation: it necessarily changes the exact membership projection
or order and fails the same gate. Production discovery remained empty
throughout Phase 4.

Phase 5.1 additionally installs the first reviewed production implementation:

- selector `split-jsonl-directory`, version 1, with no consumer profile;
- all four current row schemas under a `portable_exact_bytes` claim;
- v1 requests using the fixed safe default layout and additive
  `veriformis.export-surface-request/v2` selected requests carrying one strict
  container-options object;
- canonical split payload JSONL, optional aligned provenance, deterministic
  README/data card, receipt-bound atomic publication, and source-bound
  verification; and
- the normative rules and admission evidence in
  [Split JSONL Export v1](split-jsonl-export-v1.md).

The request envelope is operation-discriminated. Selected operations name only
the source bundle path, exact catalog selector, source-trust policy and retained
digest, and the literal overwrite policy `refuse`. Execute and verify also
require the operator-confirmed dry-run `export_plan_id`; inspect names only a
destination and returns `self_described_physical` evidence. No request may
supply a profile, dependency graph, file plan, membership projection, renderer,
semantic replayer, replacement policy, or force flag. Surface responses are
bounded summaries and are not additional durable evidence schemas.

Request v2 preserves every v1 selected-operation field and adds only
`container_options`, a flat canonical JSON object whose complete meaning and
strict schema are owned by the selected container contract. It applies to dry
run, execute, and verify; inspect remains v1 because it reads the self-described
receipt. V2 options MUST be validated before source or destination access, MUST
be repeated across the three source-bound operations, and MUST NOT supply a
profile, dependency graph, file plan, membership projection, renderer,
replayer, replacement policy, or force flag. A v2 request for an implementation
without a reviewed options parser fails even when the object is empty.

The canonical UTF-8 bytes of one request MUST NOT exceed 1 MiB (1,048,576
bytes). Every runtime bundle or destination path MUST be non-empty, contain no
NUL, and occupy at most 32 KiB (32,768 bytes) in UTF-8. The canonical bytes of
one response object MUST NOT exceed 1 MiB before transport framing. CLI stdout
contains exactly those response bytes followed by one LF; diagnostics are
written separately to stderr. The Mac process bridge retains up to 2 MiB for
each stream independently, decodes only complete untruncated canonical stdout,
and therefore retains the maximum response plus its one-byte CLI framing. MCP
returns the same canonical response object without adding a durable evidence
schema. An executable plan whose canonical dry-run response exceeds 256 KiB is
refused before rendering or destination access; this reserves bounded room for
the receipt and verification summaries of any later execute outcome. Plan
admission separately refuses a planned file whose parent path contains more
than 128 directory segments, before rendering or destination access. Public
tree inspection and verification use an iterative descriptor walk and refuse
an observed directory depth greater than 128 rather than entering unbounded
recursion.

Phase 4 does **not** implement a public registration or plugin API or a shipped
export implementation.

## Support and discovery

Persisted profile selectors and a test-injected conformance implementation are
not support claims. Phase 4 MUST NOT add a generic export container or consumer
profile to taxonomy discovery or the support capability lists, and it did not
do so.
Production export discovery was therefore empty through Phase 4. Phase 5.1 now
ships exactly one consumer-neutral implementation,
`split-jsonl-directory` v1, under its separate container contract. The existing
`minimal-v1` bundle and deterministic bundle transport remain canonical and
transport containers respectively. Generic JSON and CSV remain Phase 5 work;
named trainer profiles remain later work. Shipping generic JSONL does not
create or imply a consumer profile.

## Version and migration

Unknown schemas and versions fail closed. Changing the meaning, field set,
identity payload, ordering rule, trust literal, evidence claim, membership
projection, or receipt boundary of any v1 model requires a new schema version
and migration tests. Historical finished-bundle, transport, and handoff
contracts remain readable through their own loaders and are not reinterpreted
by this contract.

## Non-goals

- Adding another generic production export container without its own admitted
  contract and evidence.
- Claiming Aptus, MLX-LM, TRL, or another trainer profile.
- Changing `minimal-v1`, its six-file closed set, or its verifier contract.
- Adding an export workspace stage or mutating workspace history.
- Force replacement, in-place replacement, network publication, signing, or
  notarization.
- Declaring beta, public-ready, or production maturity.
