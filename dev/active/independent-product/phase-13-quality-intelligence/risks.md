# Phase 13 Risk Register

**Status:** Closed

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P13-R1 | Controlled for 13.1 | High | High | Docs imply quality intelligence before a report exists | Isolation tests; 13.1 claims none |
| P13-R2 | Controlled | High | High | A heuristic blocks seal without calibration | `near_duplicate_policy` stays `disabled`; admitted-blocking-count is 0; `admitted_to_block=True` fails closed |
| P13-R3 | Controlled | High | High | Near-duplicates advertised as semantic identity | Explicit non-goal; 13.4 names the algorithm |
| P13-R4 | Controlled | High | High | Silent row deletion | Roadmap forbids it; findings only; no heuristic deletes rows |
| P13-R5 | Controlled | Medium | High | Detectors claimed as privacy or safety certification | Explicit non-goal; U6 / U7 |
| P13-R6 | Controlled | Medium | Medium | Tokenizer simulation without a pinned tokenizer | 13.6 requires an exact profile revision |
| P13-R7 | Controlled for 13.1 | Low | High | Phase 14 review work starts from this packet | Packet and ledger forbid it |
