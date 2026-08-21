# Decisions

## Accepted

1. **Interstitial, not a phase.** This packet closes review-found defects before
   Phase 3. It is not added to `program.json`; no phase enters `in_progress`. The
   program ledger still holds exactly 21 phases with Phase 3 `planned`.

2. **No persisted-schema or identity change.** Every fix preserves durable
   identity derivation, so existing workspaces and sealed bundles keep loading
   and verifying. `primary-source-cap` is reached by mapping the documented
   surface spelling to the unchanged persisted literal, not by altering the
   `CurationPolicy` schema.

3. **Parser recovery changes are corrected behavior, not migration.** HTML,
   DOCX, and Markdown fixes change the canonical stream or diagnostics of **new**
   parses of affected sources. Prior sealed artifacts are unaffected; there is no
   revision bump. Where lost content cannot be faithfully recovered into the
   canonical stream, the parser emits a located diagnostic and degrades status
   rather than attesting `complete`.

4. **Defense in depth on commit.** Beyond fixing the no-op detection, `_commit`
   now validates its candidate revision transition before promoting `HEAD`,
   mirroring `migrate_to_current`, so any future gap fails closed instead of
   committing unloadable history.

5. **Handoff descriptor paths are pinned to contract constants and cross-checked
   against the verified manifest.** This is value validation of existing fields,
   not a schema or `handoff_id` change; valid descriptors are unaffected.

6. **Workbench inherits the CLI's fail-closed defaults.** The default compile no
   longer passes `--allow-empty-evaluation`; the split ratio matches the CLI.
   Explicitly saved user settings, if persisted, are not silently migrated.

## Non-scope (carried to risks.md)

Lower-severity review findings deferred to Phase 3+: macOS `F_FULLFSYNC`
durability, `Workspace.create` locking/atomicity, legacy M1 bundle-writer
quarantine, sentence-abbreviation token boundary, `chunk_paragraph` separator-
only chunks, `custom_regex` IGNORECASE default, CSV header heuristic, Markdown
NUL normalization diagnostic, `before_after_transformation` document-level
transform diagnostic, `snapshot-artifact-unavailable` dead code, transport
TOCTOU fd-anchoring, `write_aptus_handoff` atomic write, support-registry
`baseline_commit` check, and the Swift-workbench CI gate.
