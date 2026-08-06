# Phase 1 — Private beta workbench shell (design)

**Status:** Implemented (2026-08-06)  
**Date:** 2026-08-06  
**Parent plan:** [docs/plans/2026-08-06-private-beta-workbench.md](../../docs/plans/2026-08-06-private-beta-workbench.md)  
**Dogfood inputs:** [phase-0-dogfood.md](phase-0-dogfood.md) (D1–D10, D15, D16, D22)

## Goal

Ship a **KISS** private-beta shell around the existing thin CLI adapter so the
owner can navigate Home / Compile / History / Settings, start a compile with a
Disk Utility–style run sheet (progress % + expandable live log), retain history,
and configure CLI/output defaults — **without** new dataset formats or export
matrices.

## Non-goals (Phase 1)

- New row schemas, Parquet/Arrow/etc., multi-export
- Notarized public installer
- Cancel mid-compile (Phase 2+)
- Full debugger power (copy digests, re-run) — light touch only if free

## Information architecture

```text
┌────────────┬──────────────────────────────────────────┐
│ Home       │  Status / last run / short tips            │
│ Compile    │  Sources + options + Start                 │
│ History    │  Past runs → open log / reveal bundle      │
│ Settings   │  CLI resolution + default output           │
└────────────┴──────────────────────────────────────────┘
```

Navigation: `NavigationSplitView` sidebar list (not a multi-window wizard).

## Screens

### Home

- App title + “Dataset compiler (private beta)”
- CLI ready / not ready (from last bootstrap)
- Last successful run summary if any (time, source name, objective, open History)
- Tips: one file to start; output defaults; `docs/install.md` pointer
- Primary button → jump to Compile

### Compile

- Source drop + Browse (keep multi-file support; copy: “start with one file”)
- Objective picker with **subtitle** (D7)
- Continuation: “Train share (ppm)” + tip ≈ 40% at 400000 (D8)
- Toggle: allow empty evaluation partition + help (D9)
- Toggle: write Aptus handoff file (training consumer)
- Output folder: show path; **default** `~/Documents/Veriformis` or Settings default (D2)
- Advanced disclosure: source root (D10)
- Primary: **Compile to sealed bundle** (disabled with clear reason if blocked)
- Optional: stage chip strip (wrap if needed) for idle state

### Run sheet (modal / sheet while running + until dismissed)

Inspired by Disk Utility First Aid:

- Title: Compiling… / Compile complete / Compile failed
- Progress bar + **percent** (stage-mapped; 9 stages parse→seal → ~11% each)
- Current stage name
- Disclosure “Show log” → expandable monospaced live log (D3)
- On failure: stage + last lines visible in sheet (D11 light)
- Done: Close; optional Reveal bundle

### History

- List of runs (newest first): timestamp, status, objective, primary source name
- Select → detail: paths, manifest SHA, Open log, Reveal workspace, Reveal bundle, Reveal handoff
- Persistence: Application Support JSON under
  `com.veriformis.workbench/run-history.json` (cap e.g. 100 entries)
- Each run writes `run.log` under the workspace or output stamp folder (D15)

### Settings

- Show resolved CLI path + prefix args (read-only status)
- Optional absolute path override for `veriformis` (persisted; applied on bootstrap)
- Default output directory picker (persisted; used when Compile output unset)
- Bootstrap / “Re-detect CLI” button
- Short note: GUI apps need `run_workbench.sh` or PATH/venv; link install guide

## Progress model

Pipeline stages used for percent (exclude verify):

`parse, clean, chunk, construct, curate, split, format, validate, seal`

```text
percent = floor(100 * completedStages / 9) while running
percent = 100 on success
```

Honest stage mapping — not fake byte precision.

## Live log streaming (D4)

`VeriformisCLI.run` must stream stdout/stderr **while** the process runs
(`readabilityHandler` or incremental reads), not only after exit. UI appends
lines on the main actor.

## Defaults and compile enablement (D2)

On launch:

1. Bootstrap CLI (diagnostics in log)
2. If no output directory set → apply Settings default or create/use
   `~/Documents/Veriformis`
3. `canCompile` = sources non-empty ∧ source root directory ∧ output directory ∧ !running ∧ CLI present

## Copy glossary (Phase 1)

| Control | Label |
| --- | --- |
| Nav | Compile (not Convert) |
| Objective subtitles | See `TrainingObjective.subtitle` |
| Split | Train share (ppm) |
| Empty eval | Allow empty evaluation partition |
| Handoff | Write Aptus handoff file |
| Source root | Advanced → Source root directory |

## Objective subtitles (fixed strings)

| Objective | Subtitle |
| --- | --- |
| full_text | Whole cleaned text as training rows (Aptus may reject plain text handoff) |
| continuation | Prompt/completion pairs for next-token style training |
| section_reconstruction | Rebuild section content from structure |
| before_after_transformation | Paired before/after transformation examples |
| structured_field | Structured field extraction rows |

## Technical constraints

- Thin adapter only; stage order remains `VeriformisCLI.compilePlan`
- Parity script must stay green
- Source root remains a **directory** (`defaultSourceRoot`)
- No Python API changes required for Phase 1

## Exit criteria

1. Sidebar navigates Home / Compile / History / Settings
2. Default output folder allows compile without hunting for “Output folder…” first
3. Run sheet shows progress % and expandable live log during compile
4. Successful and failed runs appear in History with open log / reveal bundle
5. Settings shows CLI path and can set default output (+ optional CLI override)
6. `bash macos/scripts/parity_check.sh` PASS; Swift unit tests PASS
7. Docs updated (this file + plan status + macos README)

## Implementation order

1. **Docs PR** (this design + plan/WIP/install links)  
2. Models + history persistence + settings defaults  
3. Streaming CLI run  
4. Navigation shell + screens  
5. Run sheet wiring  
6. Tests + dogfood rebuild via `run_workbench.sh`
