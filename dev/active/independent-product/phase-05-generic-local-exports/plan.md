# Phase 5 Execution Plan

**Status:** Completed

**Last updated:** 2026-08-22

Each numbered roadmap work item is one sequential pull request. A pull request
must pass its focused and required repository gates, pass required GitHub
checks, merge, and leave clean local `main` equal to `origin/main` before the
next item begins.

## Checklist

### 5.1 Implement generic split JSONL export

- [x] Create the standard Phase 5 packet and mark the phase `in_progress`.
- [x] Freeze a strict versioned split JSONL profile and its configuration.
- [x] Implement the profile only through `ExportService` and the shared
      production implementation catalog.
- [x] Preserve all current row schemas and logical partitions as canonical
      JSONL with configurable but safe partition filenames.
- [x] Define optional aligned provenance, deterministic README/data-card
      output, destination bindings, dependencies, and receipt evidence.
- [x] Reject unsafe names, collisions, aliases, misaligned provenance,
      membership drift, tampering, and unexpected files before publication or
      verification succeeds.
- [x] Prove discovery, dry-run, inspect, execute, and verify parity across
      Python, CLI, MCP, and the CLI-backed Mac bridge.
- [x] Promote support claims only after focused, adversarial, round-trip, and
      required repository evidence pass and active records agree.

### 5.2 Implement canonical JSON export

- [x] Define canonical arrays/objects with explicit split and schema metadata.
- [x] Preserve every compatible current row schema and logical partition.
- [x] Bind deterministic output and semantic preservation to the verified export
      receipt.

### 5.3 Implement structurally lossless CSV export

- [x] Implement only selector `constrained-csv` version `1`, with no consumer
      profile, `portable_exact_bytes`, refuse-only overwrite behavior, and the
      internal renderer dependency frozen by the
      [Constrained CSV Export v1 contract](../../../../docs/contracts/constrained-csv-export-v1.md).
- [x] Admit exactly `text`, `prompt_completion`, and `instruction_output`, with
      the contract's exact schema-specific column order. Do not advertise or
      encode `messages` or any other nested value.
- [x] Emit the fixed closed tree: deterministic README, `data/train.csv`,
      `data/evaluation.csv`, canonical data card, mandatory complete aligned
      provenance, and the shared receipt. Accept no container options.
- [x] Freeze and enforce strict UTF-8 without a byte-order mark, comma
      delimiter, quote-all headers and values, doubled embedded quotes, LF
      record terminators and final LF, and exact embedded CR/LF/Unicode
      preservation without normalization.
- [x] Define null as unrepresentable and quoted empty field as the exact empty
      string encoding while retaining Finished Dataset v1's current non-empty
      product-field requirement. Reject missing, ragged, extra, coerced, and
      non-string values.
- [x] Refuse `messages` on dry run, execution, and source-bound verification
      before destination access or publication. Name the incompatible schema
      and direct the operator to `split-jsonl-directory` v1 or `json` v1.
- [x] Keep request, response, discovery, Finished Dataset, source bundle, and
      the ten persisted verified-export v1 models unchanged. Historical request
      v1 selects the fixed contract; configured request v2 fails before source
      or destination access.
- [x] Prove Python, CLI, MCP, and CLI-backed Mac plan parity, exact-byte
      determinism across supported Python versions, closed-tree publication,
      source-bound verification, and no trainer-compatibility claim.

#### Required item 5.3 admission evidence

- [x] Dedicated contract tests reload every supported schema and both logical
      partitions to identical payload rows, mandatory provenance, and the exact
      source `RowSet` identity.
- [x] Golden and adversarial fixtures cover commas, quotes, tabs, whitespace,
      NUL, embedded CR/LF/CRLF, formula-looking strings, non-ASCII/non-BMP text,
      and distinct NFC/NFD sequences without rewriting.
- [x] Negative fixtures reject null, missing and empty required data fields,
      wrong or reordered headers, ragged and over-wide rows, blank records,
      invalid UTF-8, byte-order marks, alternate dialects, noncanonical quoting,
      and missing final LF.
- [x] Empty evaluation emits the exact quoted header and final LF with payload
      record count zero; it is not represented as a zero-byte file.
- [x] Nested `messages` refusal is actionable and leaves the destination
      untouched for every selected operation.
- [x] Repeated rendering, every-file tamper, missing and unexpected members,
      payload/provenance disagreement, receipt/source/plan mismatch, membership
      mutation, and reconstructed row-set drift fail the applicable gate.
- [x] Focused, full, release, tracking, parity, Mac, lint, structured-file, and
      diff gates pass before any support, taxonomy, status, or evidence claim is
      promoted.

### 5.4 Integrate deterministic generic export-pack archives

- [x] Implement exactly transport profile
      `deterministic-export-pack-zip-v1` with suffix `.vfexport.zip` as an
      optional post-export wrapper, not a fourth export selector or request
      option.
- [x] Reuse ADR-0005's deterministic stored-ZIP codec and no-replace
      publication path under complementary ADR-0006 and the single existing
      deterministic archive contract.
- [x] Require a separately retained SHA-256 of canonical
      `export-receipt.json` bytes. Include exactly that receipt plus every path
      in its complete `files` sequence, with no wrapper or additional member.
- [x] Keep the ten persisted verified-export v1 models, their identities,
      request/discovery/response schemas, and the three production renderers
      unchanged. Bind the archive by consuming the existing embedded plan and
      receipt rather than adding an outer self-hash.
- [x] Admit only `portable_exact_bytes` plans in v1. Refuse
      `semantic_content_only` until an exact profile-bound semantic replayer is
      available to archive verification.
- [x] Extend `package` and `package-verify` through exactly one explicit,
      mutually exclusive `--manifest-sha256` or
      `--export-receipt-sha256` anchor. Preserve legacy `.vfbundle.zip`
      arguments, bytes, and verification behavior.
- [x] Reject unsafe, colliding, duplicate, missing, extra, compressed,
      encrypted, commented, noncanonical, corrupt, or receipt-disagreeing
      members; reconstruct only receipt-validated paths and prove canonical
      complete archive bytes before no-replace publication.
- [x] Preserve the source trust grade embedded by the export plan. Do not call
      receipt-anchored archive verification source-bound, upgrade
      `self_consistent` to `external_digest`, or treat the archive digest as a
      signature or trust anchor.
- [x] Prove all three current generic export directories package and verify
      deterministically, every relevant tamper and failure path fails closed,
      existing bundle transport is byte-compatible, and no MCP or Mac UI
      operation is introduced.
- [x] Record focused and required repository evidence before claiming item
      completion, publication, or merge.

### 5.5 Add semantic import-round-trip fixtures

- [x] Reload each supported container to identical semantic rows and logical
      partitions.
- [x] Cover every supported current row schema and incompatible-container
      refusal.

### 5.6 Expose exact dry-run previews

- [x] Show exact sample rows and the normalized destination tree without
      writing a destination.
- [x] Prove preview, plan, and execution use the same profile semantics.

The frozen runtime contract is `veriformis.export-dry-run-preview/v1` inside a
dry-run `veriformis.export-surface-response/v2` whose result is exactly
`plan` plus `preview`. It samples ordinal zero from each non-empty partition in
train-then-evaluation order, omits an exact payload whole when its canonical
UTF-8 JSON exceeds 65,536 bytes or the bounded response budget, and never
truncates or rewrites decoded values. Its destination tree is sorted,
root-relative, derived from the unchanged plan, and includes
`export-receipt.json`. Implementation and all required local admission evidence
passed. Item 5.6 then merged as PR #58 at
`cd017941090c7352cb1d10f9a383042b954d4f2e` before item 5.7 began.

### 5.7 Publish generic export operator guidance

- [x] Explain when to use JSONL, JSON, or CSV.
- [x] Keep container choice separate from training objective and consumer
      compatibility.
- [x] Reconcile all current capability, support, evidence, and governance
      records before closeout.

The [Generic Export Operator Guide](../../../../docs/generic-exports.md) chooses
split JSONL for one-record-per-line readers and nested rows, canonical JSON for
one explicit dataset object, and constrained CSV only for exact flat columns
under its frozen dialect. It states that export does not choose or
change the training objective or row schema and that consumer compatibility
requires a separately admitted named profile.

## Exit gate

Every supported current row schema exports to every compatible generic
container, reloads to identical semantic rows and logical partitions, and
detects tampering. Unsupported nested CSV fails before publication with an
actionable alternative.

**Result:** Passed locally. Items 5.1–5.6 are implemented, admitted, and merged;
item 5.6 merged as PR #58 at
`cd017941090c7352cb1d10f9a383042b954d4f2e`. Item 5.7's operator guidance and
the Phase 5 capability, support, evidence, governance, and packet reconciliation
are complete locally. Every compatible pair has the required round-trip and
tamper evidence, and nested CSV retains its actionable pre-publication refusal.
This result does not claim that the item 5.7 pull request has been published,
that GitHub checks passed, that it merged, or that post-merge local `main` was
synchronized. No later phase may begin until those sequential-PR gates occur.

## Non-goals

- Calling a generic JSONL, JSON, or CSV derivative compatible with every
  trainer.
- Adding or changing construction, curation, balancing, or split semantics.
- Creating a second deterministic archive or bundle-transport contract.
- Adding public plugin APIs, network publication, replacement-by-force,
  signing, notarization, or a maturity promotion.
