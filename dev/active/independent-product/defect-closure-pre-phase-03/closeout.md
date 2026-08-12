# Closeout

**Status:** Complete

**Last reviewed:** 2026-08-12

## Exit-gate judgment

Passed. All seven clusters were developed test-first, each regression proven red
on unmodified `main` and green after its fix, then integrated with zero merge
conflicts. On the integrated tree the full core suite is **728 passed** (net +53
regression tests over the 675 baseline), the handoff suite is **10 passed**, the
Swift workbench suite is **TEST SUCCEEDED** (29 tests), and Ruff, lockfile,
project-tracking, and diff checks are all clean.

## Defects closed

Two criticals — the workspace commit no-op/transition guard (a successful commit
could brick the workspace or stale a sealed pipeline) and HTML residual-text loss
(uncaptured body text sealed as `complete`) — plus ten majors: DOCX table-wrapper
and code-run drops, Markdown blockquote footnote refusals, RecursionError
containment across loaders/validator/verifier, the iterative disjoint-set,
reachable `primary-source-cap`, the transport post-publication warning guard, the
handoff `\n`-framed JSONL loader, handoff descriptor path pinning with manifest
cross-check, `SealPartialPublicationError` surfacing in `run` and MCP, the
`special-chars` combining-mark preservation, the `chunk_sentence` evidence
alignment, strict pipeline-spec validation, the reviewed-construction replay
plumbing, and the workbench fail-closed evaluation-gate default. Adjacent minors
in the same functions (handoff missing-file crash, undeclared row-schema shape,
sentence/paragraph edge cases) were closed alongside their cluster.

## Invariants preserved

No persisted schema, durable identity, or revision digest changed. Existing
default-rule workspaces and all sealed bundles still load and verify. Parser
recovery changes affect only new parses (corrected behavior, diagnosed and
status-degraded, not a migration). The `special-chars` version bump makes old
opt-in `special-chars` workspaces fail closed at replay rather than diverge.

## Limitations carried forward

This packet does not touch taxonomy, objectives, row schemas, containers, or any
persisted schema; it introduces no signing, notarization, remote publication, or
public-ready claim. The lower-severity review findings enumerated in `risks.md`
(macOS `F_FULLFSYNC` durability, `Workspace.create` atomicity, legacy M1
bundle-writer quarantine, the third `construction/models.py` canonical-parser
copy, sentence/paragraph/regex heuristics, CSV header heuristic, Markdown NUL
diagnostic, transport fd-anchoring, `write_aptus_handoff` atomicity, the
`baseline_commit` and Swift-CI governance gates, and the strategic roadmap
controls) are scheduled for Phase 3+ rather than absorbed here. Phase 3 remains
`planned` in the program ledger; it owns taxonomy contracts under its own packet.
