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
| Discovery and response stay v1; request v2 is additive and the ten persisted export models remain unchanged | Accepted | Strict compatibility and Mac parity evidence |
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

No item 5.1, 5.2, 5.3, or 5.4 contract decision remains pending. Item 5.3
merged as PR #55 at `c6d7fc13a09a`. Item 5.4 is locally admitted after its
required evidence passed and both independent reviews were corrected and
re-reviewed clear. Pull-request publication, GitHub evidence, merge, and
clean-main synchronization remain pending. Later decisions remain scoped to
their own sequential pull requests and cannot broaden these support claims.
