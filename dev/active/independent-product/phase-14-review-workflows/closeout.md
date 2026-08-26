# Phase 14 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-26

## Exit-gate judgment

Passed. Required-review construction cannot validate or seal until
resolved. Corrections bind a new transform or mapping-plan identity and
cannot mutate accepted records in place. Waivers do not change bytes.
Supersession keeps prior and successor review identities auditable.
Default recipes stay `none`. No Phase 13 heuristic is a default
required-review trigger. Mac Review belongs to Phase 18. Do not start
Phase 15 from this packet.

## Usability criteria

| ID | Judgment | Evidence |
| --- | --- | --- |
| U1 | Pass | `PipelineService` owns export, import, submit, and seal blocking. CLI and MCP are adapters. |
| U2 | Pass | Corrections are `transform` or `mapping-revision` with a new result identity. |
| U3 | Pass | Waiver `changes_bytes` is false. |
| U4 | Pass | Default `review_policy` is `none`. Required pending reviews block seal. |
| U5 | Pass | Quality heuristics remain `admitted_to_block=False`. |
| U6 | Pass | Reviewer identity is an unsigned local token. |
| U7 | Pass | Python, CLI, and MCP agree on review packet and bundle identities. |
| U8 | Pass | Named-seed HMAC sampling records the population and claims no statistical meaning. |
| U9 | Pass | Packet, ledger, and docs forbid starting Phase 15. |

## Delivered scope

- 14.1 packet; no queues or submit yet.
- 14.2 versioned review bundle, waiver, and correction schema.
- 14.3 core queues over construction pending and curation conflicts.
- 14.4 corrections as new transforms or mapping revisions.
- 14.5 named-seed sampling with complete population evidence.
- 14.6 review packet export, import, and submit on CLI, MCP, and Python.
- 14.7 required unresolved reviews block seal.
- 14.8 supersession with auditable history and closeout.

## Exclusions

Mac Review screens (Phase 18). Phase 15 scale work. Statistical meaning
for samples. Privacy, copyright, safety, or contamination certification
from detector findings. In-place mutation of content-addressed records.
Multi-tenant accounts or a cloud annotation platform.
