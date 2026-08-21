# Phase 3 Progress Log

This file is append-only by dated entry. Corrections are recorded in later
entries rather than deleting the earlier account.

## 2026-08-20 — Phase 3 started

**Status:** In progress

**Predecessor:** Phase 2 completed on 2026-08-11. Pre-Phase-3 defect closure
completed and merged on `main` as PR #30 (`f8dd1bf`). Phase 3 remained
`planned` with `packet: null` until this packet.

**Starting facts reviewed:**

- `TrainingObjective` is already distinct from product row schema.
- Implemented objective kinds are the five deterministic v1 kinds in
  `DETERMINISTIC_V1_OBJECTIVE_KINDS`.
- Implemented row schemas are `text`, `prompt_completion`,
  `instruction_output`, and `messages`.
- `full_text` requires `text`; every other objective forbids `text`.
- Physical publication is the canonical `minimal-v1` directory plus the
  Phase 2 deterministic `.vfbundle.zip` transport.
- Aptus handoff v1 is an optional consumer profile and already records
  supervised-boundary notes per row schema.
- ADR 0003 accepted the four-axis model; this phase persists the vocabulary
  and compatibility matrix.

**Next action:** Define the versioned taxonomy contract and a machine registry
that reuses those identifiers, then pin invalid combinations.

## 2026-08-20 — Taxonomy contract and registry opened

**Status:** In progress

Published `docs/contracts/taxonomy-v1.md` and `src/veriformis/taxonomy.py`.
The registry reuses the five deterministic objectives, four product row
schemas, `minimal-v1`, the Phase 2 transport container, and the optional Aptus
profile. Implemented families are only source-grounded language modeling and
source-grounded supervised fine-tuning. Planned and explicitly unsupported
families are named and excluded from implemented discovery. Loss policies
match the existing Aptus supervised-boundary strings. Invalid objective/row
pairs and UI aliases fail closed in the registry; surface wiring and the
public “format” inventory remain open.

**Next action:** Wire `assert_compile_combination` through `PipelineService`
and the remaining surfaces, then expose one discovery listing.

## 2026-08-20 — Opening verification observed

**Status:** In progress

Tracking PASS; Ruff clean; 24 taxonomy/contract tests passed; core suite 740
passed, 1 deselected; `git diff --check` clean. The catalog is test-verified.
Compile-surface wiring and discovery remain open.

## 2026-08-21 — Compile compatibility wired through every current surface

**Status:** In progress

`PipelineService.construct` now resolves defaults and validates the selected
objective, semantic row, and consumer profile through the taxonomy registry
before opening a workspace. CLI, MCP, YAML recipes, named recipe construction,
and the workbench compile plan delegate the same selection to that service.
The workbench selects `aptus-handoff-v1` when its optional handoff is enabled;
standalone compilation retains `veriformis-canonical-v1` by default. The
Aptus descriptor builder also reuses the registry's profile refusal and loss
boundary instead of maintaining adapter-local policy.

The profile remains validation-only and is not added to recipes, workspace
stage configuration, payload rows, manifests, or durable identity inputs.
The golden full-text and continuation manifests and transport digests remain
byte-for-byte unchanged.

**Observed verification:** Ruff passed; 55 focused tests passed; the full
Python suite passed (758 tests, one expected durability warning); all 29 macOS
tests passed; both golden compiles, external-digest verification, and
deterministic transport passed; the clean-wheel install smoke repeated both
golden compiles successfully; `git diff --check` passed.

**Next action:** Expose implemented taxonomy discovery from `PipelineService`
through CLI, MCP, and workbench help.

## 2026-08-21 — One taxonomy discovery source exposed on every surface

**Status:** In progress

`PipelineService.discover_taxonomy()` now returns a fresh adapter-safe copy of
the implemented registry. The read-only `veriformis taxonomy` command prints
that value as deterministic JSON, with contract metadata and all six taxonomy
axes named separately. The MCP `taxonomy` tool delegates to the same service
method and returns the same JSON semantics.

The workbench invokes that CLI command asynchronously. It accepts only the
complete nine-key v1 discovery object, renders all six axes in the Compile
view, cancels and replaces stale discovery requests, and shows loading or
unavailable state without falling back to a second taxonomy catalog.

This step did not rewrite the public uses of “format,” add migration fixtures,
or close Phase 3.

**Observed verification:** lock check, Ruff, and project tracking passed; 5
focused discovery-parity tests and the full 761-test Python suite passed (with
the one expected transport durability warning); all 37 macOS tests passed;
the clean-wheel install, installed CLI, and standalone full-text/continuation
golden compile passed; `git diff --check` was clean. Both golden manifest and
transport digests remained unchanged.

**Next action:** Inventory and rewrite only ambiguous public “format” language,
then add migration and backward-compatibility proof before closeout.

## 2026-08-21 — Public taxonomy vocabulary reconciled

**Status:** In progress

The active product contract, README, CLI guide, install guide, current status,
roadmap, phase tracking, and workbench presentation now name objective, semantic
row, physical container, consumer profile, input type, and row lowering
separately. Generic target “formatting” prose is now target-row-schema lowering.
The workbench presents the persisted `format` stage as `Lower rows` in pipeline,
failure, cancellation, and history UI.

Compatibility names did not change. `WorkbenchStage.format.rawValue`, CLI argv,
workspace stages/config, raw diagnostic logs, Codable history/receipts, bundle
schemas, taxonomy identifiers, legacy M1 `format` fields/keywords, migration
fixtures, and deliberate contract warnings remain exact. Known persisted stage
IDs receive a display alias only at presentation boundaries; unknown future
stage strings pass through unchanged. Historical dated plans were not rewritten.

An adjacent install-guide error was corrected: `continuation` is an objective,
not a row schema; the supervised rows accepted by the Aptus profile are
`prompt_completion`, `instruction_output`, and `messages`.

**Observed verification:** lock check, Ruff, and project tracking passed; 13
focused taxonomy/tracking tests and the full 761-test Python suite passed (with
the one expected transport durability warning); all 38 macOS tests passed; the
clean-wheel install and both standalone golden compiles passed. The
`git diff --check` result was clean, and both golden manifest and transport
digests remained unchanged.

**Next action:** Add taxonomy catalog golden round-trip coverage and prove
existing workspace and bundle backward compatibility before closeout.

## 2026-08-21 — Taxonomy and persisted-v1 compatibility frozen

**Status:** In progress

The shipped nine-key discovery catalog now has a canonical v1 golden. Its
exact schema metadata, six axes, ordering, absence of a collapsed `format`
key, and canonical SHA-256 are pinned against the shared registry. The test
does not create a second serialization envelope for the internal catalog.

A complete schema-v3 parse-to-clean workspace was generated on 2026-08-21
with pre-taxonomy source revision `f8dd1bf` and is retained as exact bytes.
Current `Workspace.open` verifies its three-revision history and every
content-addressed object. Replaying the default `page-numbers` and `whitespace`
cleaning rules returns unchanged and preserves the exact HEAD, state digest,
and clean configuration digest.

The pre-taxonomy Group 9 `full_text` bundle is also retained as exact bytes.
The current strict manifest, attestation, validation, and bundle readers load
its v1 schemas, and verification reaches `external_digest` against the
historical manifest SHA-256. Test-only Base64 wrappers preserve metadata files
whose canonical bytes intentionally have no trailing newline; production
readers and artifact schemas are unchanged.

Two locally excluded August 6 workspaces also opened with their full
ten-revision histories, and two locally excluded sealed bundles verified on
current HEAD. This recorded-local check did not copy owner data into Git.

**Observed verification:** 15 focused taxonomy and compatibility tests passed;
the full Python suite passed with 764 tests and the one expected transport
durability warning. The exact local release gate passed with 752 core tests,
one deselected optional test, Ruff, lock validation, and clean-wheel install.
Both installed-CLI golden compiles retained their manifest and transport
digests. Project tracking and the governed corpus-fixture aggregate passed,
and `git diff --check` was clean.

**Next action:** Run the full Phase 3 exit gates, reconcile support/status and
the evidence index, then complete closeout only if every gate passes.
