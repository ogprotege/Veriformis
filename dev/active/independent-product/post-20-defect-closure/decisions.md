# Decisions

Accepted scope and non-scope decisions for the post-20 defect-closure packet.

| # | Decision | Rationale |
| --- | --- | --- |
| 1 | This is a remainder packet, not Phase 21. | Phase 20 froze the CLI-first 1.0 matrix and version `0.1.0`. Closing defects behind that claim adds no capability and needs no ledger entry. |
| 2 | Parser fixes that change canonical streams bump the parser identity pin and regenerate frozen fixtures; pre-change workspaces re-parse. | Replay fails closed on identity mismatch by design; a corrected recovery is a new parser version, not a migration. |
| 3 | The exact-record fingerprint gains a versioned selector on the finished plan rather than a silent algorithm change. | Verifiers recompute the fingerprint for existing sealed bundles; those bundles must keep verifying. |
| 4 | Required review becomes resolvable by binding a submitted review bundle into a construct re-commit; the default `review_policy` stays `none`. | The contract already promises Python, CLI, and MCP round trips; resolution was the missing half. |
| 5 | The ZIP64 boundary is handled by accepting exactly one well-formed ZIP64 extra field whose values match the central-directory record. | The contract promised ZIP64; refusing the archive the codec itself wrote is not fail-closed, it is a defect. |
| 6 | Pass-through validation gates gain one independent assertion each rather than being removed from the report. | The 17-gate report is a persisted v1 identifier; removing names would need a report migration. |
| 7 | `scale-support` tiers remain empty after the performance phase until a named-hardware baseline is re-recorded. | Observed reports are not an SLA; a modest fig-leaf tier is forbidden. |
| 8 | Mac fixes keep Swift a process adapter; discovery values become opaque strings. | ADR-0019 Decision A. A closed Swift enum that gates CLI discovery is a second catalog. |
| 9 | Documentation is corrected in the same change as the code it describes; pre-existing drift is corrected in Phase 2 before parser behavior changes. | Authority documents were wrong on the audited tree; correcting them first keeps later diffs reviewable. |
