# Group 4 Pipeline Service Implementation Plan

**Status:** Complete

**Roadmap scope:** Steps 17 through 19

**Starting point:** M1 core plus merged Groups 1 through 3

**Last reviewed:** 2026-08-05

## Outcome

Move complete stage orchestration into a typed, surface-neutral
`PipelineService`, reduce the CLI to an adapter, and prove dual-objective
M1.1 acceptance through both the Python API and CLI with identical semantic
digests.

## Delivered

1. `src/veriformis/pipeline/service.py` owns stage policy, workspace
   transactions, loader replay, and adapter-facing outcome types.
2. `src/veriformis/cli.py` translates arguments, messages, exit codes, and
   durability warnings only.
3. Dual-objective acceptance covers `full_text` and `continuation` on the
   multi-source acceptance corpus through API and CLI with matching recipe,
   construction, plan, curation, split, rows, validation, seal, and bundle
   bytes.
4. Existing CLI and regression suites continue to pass after redirecting
   monkeypatches to the service module.

## Exit gate

The same raw multi-source corpus produces both required dataset objectives
through the Python API and CLI with identical canonical digests, evidence
graphs, split assignments, validation facts, and verified bundles.
