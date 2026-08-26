# Phase 14 Risk Register

**Status:** Open

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P14-R1 | Controlled for 14.1 | High | High | Docs imply review queues before contracts exist | Isolation tests; 14.1 claims none |
| P14-R2 | Controlled for 14.1 | High | High | Default recipes require review and block the golden path | `review_policy` stays `none`; isolation proves it |
| P14-R3 | Controlled for 14.4 | High | High | A correction mutates accepted records in place | 14.4 owns transforms/mapping revisions; fail closed |
| P14-R4 | Controlled for 14.4 | High | High | Waiver silently changes bytes | Distinct waiver object in 14.2/14.4 |
| P14-R5 | Open | High | High | Phase 13 heuristics become default required-review | Lock 5; 14.7 stays opt-in |
| P14-R6 | Open | Medium | High | Mac Review invents policy in Swift | Lock 1; no Mac work in this packet |
| P14-R7 | Controlled for 14.1 | Low | High | Phase 15 scale work starts from this packet | Packet and ledger forbid it |
