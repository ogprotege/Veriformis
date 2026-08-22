# Phase 5 Risk Register

**Status:** Active

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P5-R1 | Controlled for 5.1–5.3 | Medium | High | A generic exporter mutates rows, filters records, or changes partition membership | All three admitted containers bind complete membership; their compatible-schema round trips preserve ordered partitions |
| P5-R2 | Controlled for 5.1 | Medium | High | Configurable filenames permit traversal, aliases, collisions, or reserved output names | Strict derived stems and portable full-tree validation pass pre-source refusal tests |
| P5-R3 | Controlled for 5.1 | Medium | High | Optional provenance is omitted, reordered, or misaligned without detection | Provenance defaults on, is all-or-nothing, and exact alignment/receipt/tamper tests passed |
| P5-R4 | Controlled for 5.1–5.3 | Medium | High | README or machine metadata is nondeterministic or makes unsupported claims | All three contracts freeze canonical metadata, trainer non-claims, closed trees, and exact two-render evidence |
| P5-R5 | Controlled for 5.1–5.3 | Medium | High | A shipped profile bypasses the Phase 4 source, publication, or verification boundary | All three production entries run through `ExportService`; cross-surface operations share its plans |
| P5-R6 | Controlled for 5.1–5.3 | Medium | High | Support or taxonomy is promoted before implementation evidence exists | Each promotion requires focused, full, round-trip, tamper, release, and Mac evidence before merge |
| P5-R7 | Controlled for 5.1–5.3 | Low | High | Container choice is presented as trainer compatibility | All three descriptors have no consumer profile; metadata, README, contracts, and current docs state no trainer claim |
| P5-R11 | Controlled for 5.2 | Medium | High | A single JSON document obscures partition identity or permits metadata/payload drift | Frozen split keys, fixed partition order, strict counts/schema/loss binding, and aligned provenance fail closed |
| P5-R8 | Controlled for 5.3 | Medium | High | CSV encodes nested, null, missing, or ambiguous values lossily | The strict loader admits only the three frozen flat string mappings, makes null unrepresentable, and fails `messages` and nested values before destination access or publication with exact JSONL/JSON guidance |
| P5-R9 | Open | Low | High | Archive work creates a second transport contract or verifier | Reuse ADR-0005 and the existing package/package-verify path in item 5.4 |
| P5-R10 | Open | Medium | Medium | Dry-run samples or trees diverge from execution | Generate previews from the same strict plan/profile semantics and assert cross-surface parity |
| P5-R12 | Controlled for 5.3 | Medium | High | Platform or standard-library CSV defaults change quotes, escaping, or record bytes | The codec supplies UTF-8/no-BOM, comma, quote-all, doubled-quote, and LF behavior explicitly; golden bytes are exercised locally and by the Python 3.11–3.13 CI matrix |
| P5-R13 | Controlled for 5.3 | Medium | High | A permissive reload appears to prove losslessness while trimming, normalizing newlines, dropping blank rows, or padding ragged records | A dedicated strict loader uses parse-then-exact-rerender closure and does not reuse the general ingest CSV recovery parser |
| P5-R14 | Controlled for 5.3 | Medium | Medium | Null, empty string, missing field, and zero-row evaluation collapse to the same CSV representation | V1 defines no null encoding, quotes empty strings exactly, rejects empty current product fields and ragged rows, and emits a header-only evaluation file with record count zero |
| P5-R15 | Controlled for 5.3 | Low | High | Discovery or errors imply nested-message or trainer compatibility that CSV does not provide | The descriptor omits `messages`, every selected operation gives actionable JSONL/JSON refusal, the consumer profile is null, and docs state no universal trainer or spreadsheet claim |
