# Phase 18 Risk Register

**Status:** Open for Phase 18

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P18-R1 | Controlled for 18.1 | High | High | Packet opening implies Review, Exports, or dataset-row are implemented | Isolation tests and explicit non-claims |
| P18-R2 | Controlled for 18.2 | High | High | Swift becomes a second policy engine | L3; ADR-0019 Decision A; `veriformis.workbench-adapter/v1` |
| P18-R3 | Controlled for 18.7 | High | High | Empty Review or Exports tabs imply later execute | Exports is wired; Review stays out until 18.8 |
| P18-R4 | Open | High | High | Dataset-row compile runs without a confirmed mapping | Confirm-then-map; isolation until 18.4 |
| P18-R5 | Open | High | High | Document-source compile invents Phase 17 family supervision | Family goals only on dataset-row |
| P18-R6 | Controlled for 18.7 | High | High | Export mutates membership or hides the receipt | L10; existing export contracts; identity panel |
| P18-R7 | Open | Medium | High | Review screens require review on every recipe | L8; default `none` |
| P18-R8 | Open | Medium | High | Quality findings block seal from the Mac | L9; preview-only |
| P18-R9 | Open | High | High | Generator or plugin UI appears | L12; ADR-0017 and ADR-0018 |
| P18-R10 | Open | Medium | High | Family-to-trainer chrome claims DPO or tools | L13; profiles still refuse family schemas |
| P18-R11 | Open | Medium | High | SFT or Phase 17 goldens change | L11; parity scripts |
| P18-R12 | Controlled | Low | High | Phase 19 publication starts from this packet | L15 |
