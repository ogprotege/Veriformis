# Phase 17 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Execute 17.1 through 17.10 as sequential green PRs | Accepted | Operator instruction 2026-08-28 |
| Open the packet inside 17.1 and fold closeout into 17.10 | Accepted | Tracking policy and Phase 12–16 precedent |
| Add honesty only in 17.1 | Accepted | No premature family contract or execute |
| Admit each semantic family separately | Accepted | Roadmap next_gate and ordering rule 10 |
| Use dataset-row mapping as the default admission path | Accepted | User-provided evidence first |
| Bind every supervised field to `mapped_value` or a named derivation | Accepted | Product invariant 6 |
| Give new families new row schemas and loss policies | Accepted | ADR-0007; do not overload SFT schemas |
| Keep existing SFT and Phase 16 goldens byte-identical | Accepted | Phase 17 exit evidence |
| Keep constrained CSV on the three flat SFT schemas | Accepted | Constrained CSV v1 |
| Refuse new families in generic exporters and trainer profiles until admitted and pinned | Accepted | Ordering rule 10 |
| Keep quality preview-only and default `review_policy` none | Accepted | Phase 13 and 14 closeouts |
| Keep taxonomy as capability state, not the executable registry; add no eighth axis | Accepted | Taxonomy v1 |
| Do not admit families through the extension protocol | Accepted | ADR-0017 |
| Keep generation off by default; stop after 17.9 for operator review | Accepted | Phase 17 operator gate |
| Keep multimodal `explicitly_unsupported` and pre-tokenized planned | Accepted | Taxonomy v1 and Phase 17 non-goals |
| Keep `PipelineService` as policy owner; no Mac UI; do not start Phase 18 from this packet | Accepted | Product invariant 2 |
| Pin `veriformis.advanced-family-admission/v1` as a schema-only contract in 17.2 | Accepted | No execute; taxonomy stays planned |
| Keep extra grouping keys off the default SFT SplitPolicy and algorithm name | Accepted | Sealed-bundle identities must stay byte-identical |
| Keep family review queues opt-in and family quality hooks preview-only | Accepted | Phase 13/14 closeouts; no heuristic seal block |
| Admit classification from mapped_value labels only; refuse invented document-source labels | Accepted | Phase 17 lock L4 |
| Admit preference pairs from mapped_value chosen/rejected only; skip unpaired and ranking-order schemas | Accepted | Pair leakage/evidence does not cover unpaired; ranking needs a user-provided total order not present in the pair fixture |
| Admit tool-call conversations from mapped_value traces; keep two-turn messages exact | Accepted | Synthetic JSONL is a retained fixture; do not widen `messages` |
