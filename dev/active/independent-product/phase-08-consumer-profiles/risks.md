# Phase 8 Risk Register

**Status:** Open

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P8-R1 | Controlled for 8.1 | High | High | Discovery or export implies TRL/MLX-LM support before emission | Taxonomy stays planned; selectors refuse with the later item |
| P8-R2 | Controlled for 8.2 | High | High | Trainer libraries leak into core install or core pytest | Empty extras; lock has no trainer packages; 8.5 optional CI |
| P8-R3 | Open | Medium | High | A profile curates, resplits, or changes membership | ADR-0012; 8.3/8.4 must bind to the source row-set |
| P8-R4 | Open | Medium | High | Incompatible rows reach the consumer | Fail closed in Veriformis; 8.5 harness |
| P8-R5 | Controlled for 8.2 | Medium | Medium | “Works with Hugging Face” or unpinned version claims | Section-5 pins in 8.2; no generic HF claim |
| P8-R6 | Controlled for 8.1 | Low | High | Aptus is silently rewritten as a Phase 8 profile | Phase 10 owns that migration; 8.1 leaves the handoff unchanged |
| P8-R7 | Controlled for 8.6 | Medium | High | Sidecars launch training or pick a model | Dataset-only JSON; `launches_training` false; no subprocess in renderers |
