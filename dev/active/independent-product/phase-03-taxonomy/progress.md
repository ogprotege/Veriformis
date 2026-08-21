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
