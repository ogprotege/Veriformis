# Phase 9 Risk Register

**Status:** Open

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P9-R1 | Controlled for 9.1 | High | High | Discovery or export implies Parquet/Arrow/HF Dataset support before emission | Taxonomy stays planned; selectors refuse with the later item |
| P9-R2 | Controlled for 9.1 | High | High | PyArrow or datasets leak into core install or core pytest | Empty extra; lock has no columnar packages; 9.8 optional CI |
| P9-R3 | Open | High | High | Claiming portable exact bytes across PyArrow versions | ADR-0013 splits semantic fingerprint from receipt bytes |
| P9-R4 | Open | Medium | High | A container curates, resplits, or changes membership | ADR-0004; 9.4–9.6 bind to the source row-set |
| P9-R5 | Open | Medium | High | Null or nested incompatibles reach the library | Fail closed in Veriformis; 9.8 harness |
| P9-R6 | Open | Medium | Medium | Unmeasured storage or speed claims | 9.8 requires measured JSONL versus columnar before any recommendation |
| P9-R7 | Controlled for 9.1 | Low | High | Hub upload or network dataset fetch | Explicit non-goal; no Hub client in extra |
