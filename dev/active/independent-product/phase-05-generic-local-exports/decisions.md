# Phase 5 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| The verified `minimal-v1` bundle remains canonical; generic exports are derivatives | Accepted | ADR-0004; roadmap Phase 5 |
| Phase 5 executes as seven sequential green pull requests matching roadmap items 1–7 | Accepted | Phase 5 opening scope on 2026-08-21 |
| Item 5.1 ships only the trainer-neutral split JSONL container | Accepted | Roadmap work item 1 and later-item boundaries |
| All shipped implementations enter through `ExportService` and its production catalog | Accepted | Phase 4 exit boundary |
| A generic container never implies trainer or consumer compatibility | Accepted | Roadmap non-goal and taxonomy claim discipline |
| Support remains unpromoted until implementation, admission, and reconciliation evidence pass | Accepted | Project-tracking claim discipline |
| Exported rows and logical partition membership must equal the verified source; configurable filenames are physical bindings only | Accepted | Derivative-only contract and roadmap exit gate |
| Split JSONL reuses canonical row serialization and Phase 4 publication, receipt, and verification machinery | Accepted | Avoid a second semantics or filesystem path |
| Item 5.4 reuses ADR-0005 and the existing deterministic transport | Accepted | Roadmap work item 4 |
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

No item 5.1, 5.2, or 5.3 contract decision remains pending. Item 5.3 is
implemented and locally admitted; only its GitHub-green merge and local-main
synchronization gates remain. Later container decisions remain scoped to their
own sequential pull requests and cannot broaden these support claims.
