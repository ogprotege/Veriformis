# Phase 5 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| The verified `minimal-v1` bundle remains canonical; generic exports are derivatives | Accepted | ADR-0004; roadmap Phase 5 |
| Phase 5 executes as seven sequential green pull requests matching roadmap items 1–7 | Accepted | Phase 5 opening scope on 2026-08-21 |
| Item 5.1 ships only the trainer-neutral split JSONL container | Accepted | Roadmap work item 1 and later-item boundaries |
| All shipped semantic export implementations enter through `ExportService` and its production catalog; post-export transport remains a separate `PipelineService.package` operation | Accepted | Phase 4 exit boundary and roadmap item 5.4 |
| A generic container never implies trainer or consumer compatibility | Accepted | Roadmap non-goal and taxonomy claim discipline |
| Support remains unpromoted until implementation, admission, and reconciliation evidence pass | Accepted | Project-tracking claim discipline |
| Exported rows and logical partition membership must equal the verified source; configurable filenames are physical bindings only | Accepted | Derivative-only contract and roadmap exit gate |
| Split JSONL reuses canonical row serialization and Phase 4 publication, receipt, and verification machinery | Accepted | Avoid a second semantics or filesystem path |
| Item 5.4 reuses ADR-0005's deterministic ZIP envelope through complementary ADR-0006 and the single existing deterministic archive contract | Accepted | Roadmap work item 4; ADR-0006 |
| Split JSONL is container v1 with exact-byte determinism, request-v1 defaults, and complete strict request-v2 options | Accepted | `docs/contracts/split-jsonl-export-v1.md` |
| Request v1 defaults to `train` / `evaluation` filenames and included aligned provenance; request v2 may safely rename stems or omit provenance | Accepted | Loss-preserving default and explicit optional sidecar contract |
| Discovery stays v1; request v2 is additive; response v1 stays exact for non-dry-run operations while item 5.6 adds dry-run response v2; the ten persisted export models remain unchanged | Accepted | Strict compatibility and Mac parity evidence |
| Canonical JSON uses selector `json` v1 with exact bytes, all four current row schemas, and no consumer profile | Accepted | Roadmap item 5.2 and `docs/contracts/canonical-json-export-v1.md` |
| Canonical JSON v1 has a fixed closed tree and no container options | Accepted | One stable portable representation; request v1 remains sufficient |
| `dataset.json` is the sole membership-bearing file and keeps train/evaluation as explicit ordered arrays | Accepted | Exact partition preservation and complete-membership receipt binding |
| Complete provenance is mandatory but remains a separate canonical object with `train_then_evaluation` alignment | Accepted | Payload-only row discipline and Finished Dataset v1 provenance alignment |
| Constrained CSV uses selector `constrained-csv` v1, no consumer profile, `portable_exact_bytes`, and no container options | Accepted | Roadmap item 5.3 and `docs/contracts/constrained-csv-export-v1.md` |
| Constrained CSV supports exactly `instruction_output`, `prompt_completion`, and `text` in frozen column order | Accepted | Only the three current payload mappings are structurally flat exact strings |
| `messages` and every nested value fail before destination access or publication with `split-jsonl-directory` v1 and `json` v1 named as alternatives | Accepted | Roadmap nested-CSV refusal and truthful discovery |
| The CSV dialect is UTF-8 without BOM, comma-delimited, quote-all, doubled-quote escaped, and LF-terminated with exact embedded newline and Unicode preservation | Accepted | Portable exact-byte determinism without platform or library defaults |
| CSV v1 has no null encoding; quoted empty field denotes an exact empty string, while current admitted ProductRow fields remain non-empty | Accepted | Null and empty string must not collapse to one ambiguous CSV cell |
| Constrained CSV uses fixed `data/train.csv` and `data/evaluation.csv` payload files, a canonical data card, mandatory train-then-evaluation provenance, deterministic README, and the shared receipt | Accepted | Exact partitions, row-set closure, and one closed derivative tree |
| Historical request v1 selects constrained CSV; configured request v2 is refused before source or destination access | Accepted | The v1 tree and dialect expose no safe configuration surface |
| The general ingest CSV parser is not admissible round-trip evidence for constrained CSV export | Accepted | Ingest recovery normalizes newlines, trims cells, drops blank rows, and pads ragged rows |
| The item 5.4 profile is exactly `deterministic-export-pack-zip-v1` with suffix `.vfexport.zip` | Accepted | ADR-0006 and deterministic archive contract |
| Export-pack transport is optional and post-export; it is not a fourth renderer, export selector, request option, consumer profile, trainer format, or alternate destination root | Accepted | Verified Export Contract v1 and ADR-0006 |
| Packaging and verification require a separately retained digest of canonical `export-receipt.json` and archive exactly that receipt plus its complete bound file set | Accepted | Existing receipt closure and external-anchor discipline |
| The archive consumes the existing embedded plan and receipt without changing any of the ten persisted export v1 schemas or introducing an outer self-hash | Accepted | Exact-field compatibility and receipt self-reference avoidance |
| Export-pack v1 admits only `portable_exact_bytes`; `semantic_content_only` fails until an exact profile-bound semantic replayer exists | Accepted | ADR-0006 and deterministic archive verification boundary |
| `package` / `package-verify` select bundle or export-pack transport through mutually exclusive manifest- or receipt-digest flags; legacy bundle bytes and behavior remain unchanged | Accepted | One command family and backward-compatibility gate |
| Export-pack archive verification preserves the embedded source trust grade and is receipt-anchored, not source-bound; the archive digest is identity, not authority | Accepted | ADR-0006 trust boundary |
| Item 5.4 adds no MCP operation or Mac UI action | Accepted | Bounded post-export CLI/Python transport scope |
| Item 5.5 is a frozen conformance fixture, not a production importer, public import operation, or reusable replay API | Accepted | First-class existing-dataset import belongs to Phase 7 |
| The consolidated matrix is discovery-closed over the current production catalog and row-schema taxonomy | Accepted | New containers or schemas must fail the fixture until their compatible pair is explicitly admitted |
| The current compatibility matrix contains 11 positive pairs and one negative pair: constrained CSV with `messages` | Accepted | JSONL and JSON admit all four schemas; constrained CSV admits only the three flat schemas |
| Round-trip proof starts from ordinary emitted files and preserves separate ordered train/evaluation partitions, aligned provenance, and exact `RowSet` identity | Accepted | Phase 5 exit semantics without inventing an import product surface |
| Constrained CSV proof uses its strict contract loader and never the general ingest CSV recovery parser | Accepted | Recovery parsing trims, normalizes, drops, or pads inputs outside the exact export contract |
| Item 5.5 adds one canonical semantic tamper case per current container while exhaustive byte/member tampering remains in the container suites | Accepted | Consolidated semantic closure without duplicating existing adversarial coverage |
| Dry-run success uses additive runtime response v2 with result exactly `plan` and `preview`; non-dry-run operations retain response v1 | Accepted | Exact strict-envelope compatibility without changing durable export evidence |
| The runtime preview schema is `veriformis.export-dry-run-preview/v1` and is not one of the ten persisted verified-export v1 models | Accepted | Preview is bounded operator information, not a receipt or durable attestation |
| Preview samples ordinal zero from each non-empty partition in train-then-evaluation order under `first-row-per-non-empty-partition` | Accepted | Exact deterministic sample selection without filtering or resplitting |
| Canonical payload JSON larger than 65,536 bytes or unable to fit the response budget is omitted whole with an exact reason, never truncated | Accepted | Preserve decoded row values and bounded transport simultaneously |
| Preview transport is ASCII-safe while decoding to the exact payload values, without Unicode normalization or content rewriting | Accepted | Canonical response transport and semantic fidelity |
| The sorted root-relative tree is derived from the plan and adds only the known `export-receipt.json`; preview never calls a renderer or accesses a destination | Accepted | One plan semantics and a side-effect-free dry run |
| Item 5.6 changes no persisted schema, request, discovery, selector, taxonomy, support state, renderer, destination policy, trainer, or consumer claim | Accepted | Bounded roadmap item and compatibility discipline |
| Training objective and semantic row schema are fixed by construction and the finished-dataset plan before generic export; a physical container only encodes those completed rows and partitions | Accepted | Taxonomy axis separation and derivative-only export contract |
| Consumer compatibility is independent of file extension and requires a separately admitted named profile; all three generic export descriptors retain a null consumer profile | Accepted | Taxonomy claim discipline and current production discovery |
| Operators choose split JSONL for one-record-per-line readers and nested rows, canonical JSON for one explicit dataset object, and constrained CSV only for exact flat columns under its frozen dialect | Accepted | Roadmap item 5.7 and the Generic Export Operator Guide |
| Item 5.7 is documentation and reconciliation only; it changes no runtime behavior, persisted schema, request, response, discovery, selector, taxonomy entry, support state, renderer, trainer profile, or consumer profile | Accepted | Bounded closeout scope and current contract review |

No Phase 5 contract or guidance decision remains pending. Item 5.6 merged as PR
#58 at `cd017941090c7352cb1d10f9a383042b954d4f2e`. Item 5.7's static guidance
and decision reconciliation merged as PR #59 at
`65cbd471e96d83f8dd65e2cda60e90f64a916e2b` under the accepted boundaries
above. Later decisions remain scoped to their own sequential pull requests and
cannot broaden these support claims.
