# Phase 3 Evidence

**Evidence status:** Starting facts recorded; closeout evidence not yet observed

**Predecessor:** [Phase 2 closeout](../phase-02-reliability-artifact-boundary/closeout.md);
[pre-Phase-3 defect closure](../defect-closure-pre-phase-03/closeout.md)

## Source-verified starting facts

| Fact | Evidence | Limitation |
| --- | --- | --- |
| Objective is not a row schema | `TrainingObjective` and `DatasetRecipe.target_row_schema`; ADR 0003 | Docs and CLI still say “format” in places |
| Five deterministic objectives are implemented | `DETERMINISTIC_V1_OBJECTIVE_KINDS`; named recipe library | No preference or generated family |
| Four product row schemas are implemented | `V1_ROW_SCHEMA_KINDS`; finished-dataset contract | `text` is `full_text` only |
| `full_text` requires `text`; others forbid `text` | `DatasetRecipe` validator; `PipelineService.construct` | Error text is local to those call sites |
| Canonical bundle is `minimal-v1` | Bundle constants; support registry | Not a trainer profile |
| Transport is deterministic `.vfbundle.zip` | ADR 0005; bundle transport contract | Not a generic export container |
| Aptus is optional and records a supervised boundary per row | `handoff/aptus_v1.py` `_masking_expectation` | Adapter-local; not a shared registry |
| Legacy CLI mode names are not recipe schemas | Construction contract product-row declarations | Surfaces may still expose the aliases |
| Phase 3 had no packet while `planned` | `program.json` before this change | Packet now required for `in_progress` |

## Required final evidence

- Taxonomy contract with explicit axis, family, loss, and compatibility rules.
- Machine registry bound to existing objective, row, container, and profile IDs.
- Invalid-combination tests that fail before compile.
- Discovery parity across `PipelineService`, CLI, MCP, and workbench help.
- Proof that existing workspaces and sealed bundles still load.
- Tracking, status, support, evidence, and diff checks.

Exact results are appended only after observation.

## Observed opening results — 2026-08-20

| Gate | Result | Grade / limitation |
| --- | --- | --- |
| Project tracking | PASS | Test-verified; Phase 3 packet and WIP table agree |
| Ruff | All checks passed | Recorded local |
| Taxonomy and contract tests | 24 passed | Test-verified |
| Core pytest | 740 passed, 1 deselected | Test-verified; +12 taxonomy tests over the 728 defect-closure baseline |
| `git diff --check` | Clean | Recorded local |

Surface discovery, compile-path wiring, and the public “format” inventory are
not claimed by this observation.
