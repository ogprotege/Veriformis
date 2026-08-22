# Phase 6 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-22

## Exit-gate judgment

Passed. A non-developer can select each supported goal from plain
language and inspect exactly what receives training loss. Every surface
resolves to the same recipe identifiers and outputs. Instruction templates
are the only default instruction literals; an operator instruction is
admitted only when it names the goal's task and claims no transformation
the goal does not perform.

The seven Phase 6 items are complete within the goal-first boundary. The
catalog, contracts, seventh taxonomy axis, preview, presets, preflight,
acceptance matrix, and instruction-truthfulness closeout add no objective,
row schema, construction behavior, trainer claim, consumer profile,
generated text, or invented question, answer, summary, or target.

Item 6.7 passed all 14 GitHub checks and merged as PR #67 at
`6995d17bef0d09f235b1c464e947c38c63dd313d`; clean local `main` equals
`origin/main` there.

## Delivered scope

- Item 6.1 shipped the packaged `veriformis.goal-catalog/v1` data and
  read-only discovery on Python, CLI, MCP, and the Mac bridge, and
  predeclared usability criteria U1–U6.
- Item 6.2 extended every goal with evidence, family eligibility, and
  non-claims, and added `input_family` as the seventh taxonomy axis under
  ADR-0008.
- Item 6.3 shipped runtime-only `veriformis.goal-preview/v1` so every
  compatible representation shows the exact supervised span.
- Item 6.4 shipped `veriformis.recipe-preset/v1` as the single source of
  recipe defaults and put the named recipe library on every compile surface.
- Item 6.5 shipped runtime-only `veriformis.compile-preflight/v1` over raw
  sources with no workspace mutation.
- Item 6.6 froze the discovery-closed 74-cell acceptance matrix from raw
  source through seal and external-digest verify on every surface.
- Item 6.7 added per-goal instruction templates and the deterministic
  truthfulness check, judged U1–U6, and wrote this closeout.

## Verification summary

- Focused goal tests: 373 passed.
- Full Python: 1,910 collected; the only first-run failure was the matrix
  catalog digest after the additive catalog fields, then corrected by
  pinning `catalog_sha256`. Standalone release: 1,898 passed, 1 deselected,
  with only the intentional transport durability warning.
- Project tracking, lock, Ruff, structured JSON, fixture byte equality, and
  diff checks passed.
- This Linux cloud VM cannot run XCTest or the Mac parity script; those
  remain the macOS GitHub check.

Exact tables live in `evidence.md`.

## Exclusions and remaining constraints

- Phase 6 does not decide whether fine-tuning is appropriate.
- Phase 6 invents no question, answer, summary, or target.
- Phase 6 adds no objective, row schema, training family, construction
  behavior, consumer profile, trainer claim, or generated text.
- Dataset quality intelligence remains Phase 13; existing-dataset import
  remains Phase 7; the complete goal-first Mac workbench remains Phase 18.
- Generic exports still make no trainer or spreadsheet compatibility claim.
- Development alpha remains `0.1.0`.
- Documentation debts DOC-002, DOC-003, DOC-006, and DOC-007 remain open;
  none changes the Phase 6 exit judgment.

This closeout pull request passed every required GitHub check and merged as
PR #67 at `6995d17bef0d09f235b1c464e947c38c63dd313d`; clean local `main`
equals `origin/main` there. Phase 7 may begin under its own standard packet.
