# Phase 5 Risk Register

**Status:** Active

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P5-R1 | Controlled for 5.1–5.2 | Medium | High | A generic exporter mutates rows, filters records, or changes partition membership | Both admitted containers bind complete membership; their four-schema round trips preserve ordered partitions |
| P5-R2 | Controlled for 5.1 | Medium | High | Configurable filenames permit traversal, aliases, collisions, or reserved output names | Strict derived stems and portable full-tree validation pass pre-source refusal tests |
| P5-R3 | Controlled for 5.1 | Medium | High | Optional provenance is omitted, reordered, or misaligned without detection | Provenance defaults on, is all-or-nothing, and exact alignment/receipt/tamper tests passed |
| P5-R4 | Controlled for 5.1–5.2 | Medium | High | README or machine metadata is nondeterministic or makes unsupported claims | Both contracts freeze canonical metadata, trainer non-claims, closed trees, and exact two-render evidence |
| P5-R5 | Controlled for 5.1–5.2 | Medium | High | A shipped profile bypasses the Phase 4 source, publication, or verification boundary | Both production entries run through `ExportService`; cross-surface operations share its plans |
| P5-R6 | Controlled for 5.1–5.2 | Medium | High | Support or taxonomy is promoted before implementation evidence exists | Each promotion requires focused, full, round-trip, tamper, release, and Mac evidence before merge |
| P5-R7 | Controlled for 5.1–5.2 | Low | High | Container choice is presented as trainer compatibility | Both descriptors have no consumer profile; metadata, README, contracts, and current docs state no trainer claim |
| P5-R11 | Controlled for 5.2 | Medium | High | A single JSON document obscures partition identity or permits metadata/payload drift | Frozen split keys, fixed partition order, strict counts/schema/loss binding, and aligned provenance fail closed |
| P5-R8 | Open | Medium | Medium | CSV encodes nested or ambiguous values lossily | Limit admission to frozen flat mappings and fail before publication with JSONL/JSON guidance |
| P5-R9 | Open | Low | High | Archive work creates a second transport contract or verifier | Reuse ADR-0005 and the existing package/package-verify path in item 5.4 |
| P5-R10 | Open | Medium | Medium | Dry-run samples or trees diverge from execution | Generate previews from the same strict plan/profile semantics and assert cross-surface parity |
