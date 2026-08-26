# Phase 13 Decision Index

**Status:** Closed

| Decision | State | Basis |
| --- | --- | --- |
| Phase 13 executes as sequential green pull requests; packet opening is 13.1; closeout folds into 13.9 | Accepted | Phase 12 precedent; operator instruction 2026-08-25 |
| Repository is public; each item is its own pull request | Accepted | Operator instruction 2026-08-25 |
| Facts stay separate from policy decisions and recommendations | Accepted | Roadmap work item 1 |
| No quality-report schema, CLI, or MCP in 13.1 | Accepted | Honesty pattern of Phase 8.1 / 12.1 |
| `near_duplicate_policy` stays `disabled` in 13.1 | Accepted | Roadmap: calibrate before enforcement |
| Near-duplicates are not semantic identity and must not silently delete rows | Accepted | Roadmap work item 3 |
| Optional detectors are findings, not certification | Accepted | Roadmap work item 6 and non-goals |
| Do not start Phase 14 from this packet | Accepted | Roadmap dependency 7: quality facts precede review gates |
| Quality gates preview only; none admitted to block seal | Accepted | Roadmap items 8–9; U3; detectors and near-duplicates are not certification or identity |
| Gates bind to `plan_id`; FinishedDatasetPlan and snapshot schemas stay frozen | Accepted | Changing those schemas would rewrite every sealed bundle |
| No quality-report CLI or MCP command in Phase 13 | Accepted | Report is not a pipeline stage; U8 is agreement that the operator surface is absent |
