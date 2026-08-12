# Risks and Controls

## Active during this packet

| Risk | Cause | Control |
| --- | --- | --- |
| Parser fix changes a golden fixture that asserted lossy behavior | Existing tests may pin the old silent-drop output | Each cluster updates such assertions to the corrected behavior and records it in the PR; corrected behavior must add diagnostics, never weaken the fix |
| `pipeline/service.py` merge conflict | Clusters 3 and 6 both edit the file | Different methods; integration keeps both edits and re-runs the full suite |
| HTML residual-recovery breaks span/evidence invariants | Canonical-stream spans must still verify | Prefer capturing residual text as real paragraph blocks through existing machinery; emit a diagnostic only for genuinely non-representable content; evidence tests must pass |
| A fix quietly reduces coverage | Large multi-cluster change | Exit gate requires net test count strictly above the 675 baseline and every new regression shown red-before / green-after |

## Deferred findings (carry to Phase 3+ scheduling)

Lower-severity review findings not closed here, each to be scheduled explicitly
rather than absorbed silently:

- macOS durability confirmation overstated (`os.fsync` without `F_FULLFSYNC`) in
  `workspace.py`, `bundle/finished.py`, `bundle/transport.py`.
- `Workspace.create` is unlocked and non-atomic (identity swap under a race;
  unadoptable directory on interrupted create).
- Legacy M1 bundle writer emits nondeterministic and self-referential manifests;
  quarantine or document as M1-only.
- `chunk_sentence` abbreviation guard matches word suffixes; `chunk_paragraph`
  emits separator-only chunks; `custom_regex` applies IGNORECASE silently.
- CSV header heuristic promotes a data row after a leading blank line; Markdown
  NUL→U+FFFD lacks a diagnostic; `before_after_transformation` aborts instead of
  diagnosing a document-level transform record.
- `snapshot-artifact-unavailable` finding is dead code (misreported as digest
  mismatch); transport publication is path- rather than fd-anchored (TOCTOU);
  `write_aptus_handoff` is a non-atomic overwriting write.
- Governance: add a `baseline_commit` ancestry check to the tracking script; add
  a macOS `xcodebuild test` CI gate for the workbench.
- Strategic (roadmap): front-load dependency/license scanning, a performance
  baseline, a demand-validation beta gate, a Windows-support ADR, and a
  maintainer-capacity risk row.
