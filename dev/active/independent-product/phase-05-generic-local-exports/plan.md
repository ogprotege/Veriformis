# Phase 5 Execution Plan

**Status:** In progress

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

- [ ] Reuse ADR-0005 and the existing bundle transport/package verifier.
- [ ] Bind generic export-pack archives into export plans and receipts.
- [ ] Do not create a second bundle-transport contract.

### 5.5 Add semantic import-round-trip fixtures

- [ ] Reload each supported container to identical semantic rows and logical
      partitions.
- [ ] Cover every supported current row schema and incompatible-container
      refusal.

### 5.6 Expose exact dry-run previews

- [ ] Show exact sample rows and the normalized destination tree without
      writing a destination.
- [ ] Prove preview, plan, and execution use the same profile semantics.

### 5.7 Publish generic export operator guidance

- [ ] Explain when to use JSONL, JSON, or CSV.
- [ ] Keep container choice separate from training objective and consumer
      compatibility.
- [ ] Reconcile all current capability, support, evidence, and governance
      records before closeout.

## Exit gate

Every supported current row schema exports to every compatible generic
container, reloads to identical semantic rows and logical partitions, and
detects tampering. Unsupported nested CSV fails before publication with an
actionable alternative.

**Result:** Phases 5.1–5.3 are implemented and locally admitted. Item 5.3's
focused, full, release, parity, Mac, tracking, and independent-review gates are
green; its remote-green merge and clean-main synchronization gates remain
before item 5.4 begins. Later checklist items and the phase-wide exit proof
remain open.

## Non-goals

- Calling a generic JSONL, JSON, or CSV derivative compatible with every
  trainer.
- Adding or changing construction, curation, balancing, or split semantics.
- Creating a second deterministic archive or bundle-transport contract.
- Adding public plugin APIs, network publication, replacement-by-force,
  signing, notarization, or a maturity promotion.
