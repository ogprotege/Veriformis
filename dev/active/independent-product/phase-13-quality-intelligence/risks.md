# Phase 13 Risk Register

**Status:** Open

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P13-R1 | Controlled for 13.1 | High | High | Docs imply quality intelligence before a report exists | Isolation tests; 13.1 claims none |
| P13-R2 | Controlled for 13.1 | High | High | A heuristic blocks seal without calibration | `near_duplicate_policy` stays `disabled`; 13.9 owns blocking |
| P13-R3 | Open | High | High | Near-duplicates advertised as semantic identity | Explicit non-goal; 13.4 names the algorithm |
| P13-R4 | Open | High | High | Silent row deletion | Roadmap forbids it; findings only until 13.9 |
| P13-R5 | Open | Medium | High | Detectors claimed as privacy or safety certification | Explicit non-goal; U6 / U7 |
| P13-R6 | Open | Medium | Medium | Tokenizer simulation without a pinned tokenizer | 13.6 requires an exact profile revision |
| P13-R7 | Controlled for 13.1 | Low | High | Phase 14 review work starts from this packet | Packet and ledger forbid it |
