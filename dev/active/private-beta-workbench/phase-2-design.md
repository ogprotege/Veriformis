# Phase 2 — Debugger power (design + status)

**Status:** Implemented (2026-08-06)  
**Parent plan:** [docs/plans/2026-08-06-private-beta-workbench.md](../../docs/plans/2026-08-06-private-beta-workbench.md)

## Goal

Make failed and successful compiles faster to diagnose than retyping CLI.

## Shipped

| Feature | Where |
| --- | --- |
| Failure panel: stage, exit code, last log lines | Run sheet |
| Copy error / copy digests | Run sheet, Result, History |
| Manifest SHA-256 + assignment digest extract + copy | Result, run sheet success panel, History |
| Reveal workspace + bundle (+ handoff/log) | Result, run sheet, History |
| Re-run last / re-run from History | Compile, Result, Run sheet, History |
| History stores re-run settings + failure stage/exit | `RunHistoryEntry` |

## Non-goals (still later)

- Cancel mid-compile
- Full Aptus handoff-verify auto status in UI (Phase 2 optional stretch; not required)
- Export menu (Phase 3)

## Exit

Owner can fail a run, see stage/exit/log tail, copy digests on success, reveal artifacts, and re-run without re-picking every control.
