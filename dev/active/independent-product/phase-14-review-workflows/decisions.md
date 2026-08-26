# Phase 14 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Phase 14 executes as sequential green pull requests; packet opening is 14.1; closeout folds into 14.8 | Accepted | Phases 12–13 precedent; operator instruction 2026-08-25 |
| Repository is public; each item is its own pull request | Accepted | Operator instruction 2026-08-25 |
| 14 owns Python/CLI/MCP review APIs; Mac Review screens belong to Phase 18 | Accepted | Operator lock 1; composition-root invariant; Phase 18 depends on review APIs |
| Core v1 queues are construction pending, conflicts, OCR `review`, mapping, and parser degradation; sampling is its own item; near-duplicate and detector queues are opt-in only | Accepted | Operator lock 2 |
| Default `review_policy` stays `none`; required review is opt-in and then fail-closed | Accepted | Operator lock 3; product contract |
| Waiver never changes bytes; correction is a new transform or mapping revision | Accepted | Operator lock 4 |
| No Phase 13 heuristic becomes a default required-review trigger | Accepted | Operator lock 5; findings are not certification |
| Reviewer identity is an opaque local unsigned attestation | Accepted | Operator lock 6; construction `ReviewEvidence` |
| No review-queue schema, submit command, or Mac UI in 14.1 | Accepted | Honesty pattern of 13.1 |
| Do not start Phase 15 from this packet | Accepted | Roadmap: Phase 15 does not depend on 14 |
