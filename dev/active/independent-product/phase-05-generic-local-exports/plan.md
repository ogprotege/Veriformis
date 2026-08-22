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

- [ ] Admit only flat text, prompt/completion, and
      instruction/input/output mappings that remain lossless.
- [ ] Freeze quoting, encoding, newline, null, empty-string, and Unicode rules.
- [ ] Refuse nested values before publication with an actionable JSONL or JSON
      alternative.

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

**Result:** Phases 5.1 and 5.2 are implemented, and 5.2's independent code,
security, and documentation reviews found no blocker. Its remote-green merge
gate remains before 5.3 begins. Later checklist items and the phase-wide exit
proof remain open.

## Non-goals

- Calling a generic JSONL, JSON, or CSV derivative compatible with every
  trainer.
- Adding or changing construction, curation, balancing, or split semantics.
- Creating a second deterministic archive or bundle-transport contract.
- Adding public plugin APIs, network publication, replacement-by-force,
  signing, notarization, or a maturity promotion.
