# Phase 10 Risk Register

**Status:** Open

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P10-R1 | Controlled for 10.1 | High | High | Discovery or export implies Axolotl / LLaMA-Factory / Unsloth support before admission | Taxonomy stays candidate; selectors refuse as Phase 10 |
| P10-R2 | Controlled for 10.1 | High | High | Trainer libraries leak into core install or core pytest | Empty extras; lock has no those packages; later optional CI |
| P10-R3 | Open | High | High | Shipping a profile whose official contract is unstable | Section-5 pins in 10.2; skip emit if the pin fails |
| P10-R4 | Open | Medium | High | A profile curates, resplits, or changes membership | ADR-0004 and ADR-0012; 10.3–10.6 bind to the source row-set |
| P10-R5 | Open | Medium | High | Preference or tools rows reach a trainer | Fail closed in Veriformis; 10.7 harness |
| P10-R6 | Open | Medium | High | Aptus keeps special product authority after 10.6 | Explicit 10.6 item; default seal still does not write the sibling |
| P10-R7 | Controlled for 10.1 | Low | High | Hosted OpenAI or network training from this packet | Explicit non-goal |
