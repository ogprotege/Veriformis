# Phase 5 Risk Register

**Status:** Active

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P5-R1 | Controlled for 5.1 | Medium | High | A generic exporter mutates rows, filters records, or changes partition membership | Exact four-schema round trips and Phase 4 complete-membership checks passed |
| P5-R2 | Controlled for 5.1 | Medium | High | Configurable filenames permit traversal, aliases, collisions, or reserved output names | Strict derived stems and portable full-tree validation pass pre-source refusal tests |
| P5-R3 | Controlled for 5.1 | Medium | High | Optional provenance is omitted, reordered, or misaligned without detection | Provenance defaults on, is all-or-nothing, and exact alignment/receipt/tamper tests passed |
| P5-R4 | Controlled for 5.1 | Medium | High | README/data-card output is nondeterministic or makes unsupported claims | Frozen canonical card and exact README/tree golden passed two-render evidence |
| P5-R5 | Controlled for 5.1 | Medium | High | A shipped profile bypasses the Phase 4 source, publication, or verification boundary | The only production entry runs through `ExportService`; cross-surface tests share its plans |
| P5-R6 | Controlled for 5.1 | Medium | High | Support or taxonomy is promoted before implementation evidence exists | Promotion followed focused, full, round-trip, tamper, release, and Mac evidence |
| P5-R7 | Controlled for 5.1 | Low | High | Container choice is presented as trainer compatibility | Descriptor has no consumer profile; card, README, contract, and current docs state no trainer claim |
| P5-R8 | Open | Medium | Medium | CSV encodes nested or ambiguous values lossily | Limit admission to frozen flat mappings and fail before publication with JSONL/JSON guidance |
| P5-R9 | Open | Low | High | Archive work creates a second transport contract or verifier | Reuse ADR-0005 and the existing package/package-verify path in item 5.4 |
| P5-R10 | Open | Medium | Medium | Dry-run samples or trees diverge from execution | Generate previews from the same strict plan/profile semantics and assert cross-surface parity |
