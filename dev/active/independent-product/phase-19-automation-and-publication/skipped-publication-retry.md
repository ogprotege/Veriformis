# Skipped: publication retry and idempotency

**Date:** 2026-08-31

**Item:** 19.9

Phase 19.7 ADR-0020 Decision A installs no Hub execute, retry, or
credential helpers. Retry, idempotency, conflict, partial-upload,
offline, and revocation have no execute surface.

This packet skips those controls with a record, same honesty as
15.5–15.8, 16.10 public plugins, and 17.9 generation. A later operator
license that supersedes ADR-0020 Decision B would reopen this item.

CLI and MCP still have no `hub-upload`. `execute_allowed` stays false.
`retry_allowed` stays false.
