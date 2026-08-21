# Phase 3 Risk Register

**Last reviewed:** 2026-08-21

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P3-R1 | Mitigated | Medium | High | A new taxonomy identifier silently reinterprets sealed recipes or rows. | Persisted v1 IDs and schemas stayed exact; frozen pre-taxonomy workspace and bundle bytes load and verify on current HEAD |
| P3-R2 | Mitigated | High | High | Public copy keeps using “format” for goal, row, container, or profile. | Public inventory completed; discovery names every axis; workbench uses display-only `Lower rows`; persisted stage IDs remain unchanged |
| P3-R3 | Active | Medium | High | Future families appear implemented because they are named in the contract. | Explicit `planned` / `explicitly_unsupported` states; support registry and tests |
| P3-R4 | Active | Medium | Medium | Aptus `text` refusal is mistaken for a core product rule. | Profile constraints stay separate from objective/row compatibility |
| P3-R5 | Active | Medium | Medium | Loss notes in the Aptus adapter become a second source of truth. | One registry; adapter must read or match the shared loss policy |
| P3-R6 | Active | Low | High | Opening Phase 3 absorbs deferred defect-closure findings and stalls taxonomy. | Those findings stay scheduled, not required for the taxonomy exit gate |

## Carried from pre-Phase-3 defect closure

These remain scheduled for Phase 3+ and are not absorbed into 3.1–3.2:

- macOS `F_FULLFSYNC` durability confirmation
- `Workspace.create` locking and atomicity
- Legacy M1 bundle-writer quarantine
- Sentence, paragraph, regex, CSV, and Markdown heuristic findings
- Transport fd-anchoring and `write_aptus_handoff` atomicity
- Tracking `baseline_commit` ancestry check and Swift `xcodebuild` CI gate
