# Skipped MCP wraps: package / package-verify

**Date:** 2026-08-31

**Item:** 19.5

Phase 19.5 audited MCP against the roadmap set: discovery, preflight,
mapping, quality preview, review, export, and verification.

`package` and `package-verify` are CLI transport over an already sealed
bundle. They are not in that set. Verification of sealed bundles is
already wrapped as MCP `verify`. Export-pack transport stays on the CLI.

This packet does not add MCP `package` or `package_verify`. The CLI
commands remain. There is no Hub tool and no quality-report tool.
`run_pipeline` still executes `veriformis.pipeline/v1` only.
