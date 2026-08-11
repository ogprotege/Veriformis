# Phase 0 Risk Register

**Last reviewed:** 2026-08-11

| ID | State | Likelihood | Impact | Risk | Control / evidence | Owner phase |
| --- | --- | --- | --- | --- | --- | --- |
| P0-R1 | Open | Medium | High | Human status prose drifts from code. | Support registry comparisons and pytest drift check | Phase 0 |
| P0-R2 | Open | Medium | High | A planned feature is reported as implemented. | State vocabulary, support registry, completion rule, review | Every phase |
| P0-R3 | Open | Medium | Medium | WIP and machine ledger disagree. | Marker-delimited phase table checked by script | Phase 0 |
| P0-R4 | Mitigated | High | Medium | Format priority is based on popularity rather than owner corpus evidence. | Governed matrix ranks only the smallest source-verified generic JSONL step and leaves other containers/trainers unranked | Phase 0 |
| P0-R5 | Open | Medium | High | Test results are overstated as retained evidence. | Evidence grades distinguish recorded-local from retained-artifact | Every phase |
| P0-R6 | Open | Low | High | A phase is closed with unresolved debt or without migrations/docs. | Standard closeout and multi-record completion rule | Every phase |
| P0-R7 | Accepted | High | Medium | The tracking system adds maintenance cost. | Keep JSON schemas small; automate literal checks; require changes only when truth changes | Every phase |

Accepted risks remain visible. “Accepted” does not mean disproven; it means the
named control and tradeoff are deliberate.
