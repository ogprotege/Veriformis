# Phase 3 Risk Register

**Last reviewed:** 2026-08-21

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P3-R1 | Mitigated | Medium | High | A new taxonomy identifier silently reinterprets sealed recipes or rows. | Persisted v1 IDs and schemas stayed exact; frozen pre-taxonomy workspace and bundle bytes load and verify on current HEAD |
| P3-R2 | Mitigated | High | High | Public copy keeps using “format” for goal, row, container, or profile. | Public inventory completed; discovery names every axis; workbench uses display-only `Lower rows`; persisted stage IDs remain unchanged |
| P3-R3 | Mitigated | Medium | High | Future families appear implemented because they are named in the contract. | Explicit `planned` / `explicitly_unsupported` states stay out of implemented discovery; support registry and contract tests pass |
| P3-R4 | Mitigated | Medium | Medium | Aptus `text` refusal is mistaken for a core product rule. | Profile constraints remain separate from objective/row compatibility and are covered at compile selection and descriptor construction |
| P3-R5 | Mitigated | Medium | Medium | Loss notes in the Aptus adapter become a second source of truth. | The adapter reads the shared registry loss policy; parity and focused tests pass |
| P3-R6 | Mitigated | Low | High | Opening Phase 3 absorbs deferred defect-closure findings and stalls taxonomy. | Phase 3 closed without absorbing the scheduled findings listed below |

## Carried from pre-Phase-3 defect closure

These remain scheduled beyond Phase 3 and were not absorbed into its exit gate:

- macOS `F_FULLFSYNC` durability confirmation
- `Workspace.create` locking and atomicity
- Legacy M1 bundle-writer quarantine
- Sentence, paragraph, regex, CSV, and Markdown heuristic findings
- Transport fd-anchoring and `write_aptus_handoff` atomicity
- Tracking `baseline_commit` ancestry check and Swift `xcodebuild` CI gate
