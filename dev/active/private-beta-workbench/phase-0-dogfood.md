# Phase 0 — Workbench dogfood punch list

**Date:** 2026-08-06  
**Plan:** [docs/plans/2026-08-06-private-beta-workbench.md](../../docs/plans/2026-08-06-private-beta-workbench.md)  
**Baseline:** `main` at `e52d51b` (vision plan merged)  
**Status:** Phase 0 complete for agent-assisted dogfood; owner should still click through the GUI once

## What was exercised

| Check | Result |
| --- | --- |
| `xcodegen generate` + `xcodebuild` Debug build | **BUILD SUCCEEDED** (local sign) |
| `macos/scripts/parity_check.sh` | **PASS** (A/B digests identical) |
| Swift unit tests (`CLIBridgeTests`) | **3 passed** |
| Workbench-equivalent CLI: `full_text` single source | Seal + `external_digest` verify **PASS** |
| Workbench-equivalent CLI: golden multi-source `continuation` | Seal + verify + handoff **accepted** **PASS** |
| `full_text` Aptus handoff-verify | **rejected** `backend-rejects-row-schema:text` (expected) |
| Empty-text PDF parse | Fail-closed `pdf.ocr-required` (expected) |

App product path:  
`/tmp/veriformis-dd/Build/Products/Debug/Veriformis.app` (from this session’s DerivedData).

Owner GUI pass (still recommended): open the app, drop a source, set output folder, compile, watch stages/log.

## What works well today

1. **Correct product verb in the primary button:** “Compile to sealed bundle.”
2. **Source drop + Browse** with multi-select and folder expand; extension filter matches supported inputs.
3. **Stage chips** (parse → seal) give a coarse pipeline story.
4. **Live-ish log panel** with monospaced text and auto-scroll.
5. **Result panel** with paths + Reveal bundle / handoff.
6. **CLI resolution** (env → PATH → `uv run` from repo) is documented and coded.
7. **Thin adapter + parity** is real: digests match pure CLI sequence.
8. Engine still **fails closed** on OCR and Aptus `text` schema (good for teaching honesty in UI).

## Punch list → Phase 1 / 2 (ordered)

### P0 for Phase 1 shell (KISS IA + run UX)

| ID | Pain | Why it hurts private beta | Suggested fix |
| --- | --- | --- | --- |
| D1 | **No Home / History / Settings nav** | Everything is one split view; hard to return to prior runs | Sidebar: Home, Compile, History, Settings |
| D2 | **Output folder required before Compile is enabled** | Easy to stall: drop files, click Compile, nothing — `canCompile` needs output dir | Default to `~/Documents/Veriformis` or last-used; show clear “choose output” callout |
| D3 | **No progress % / no Disk Utility run sheet** | Stage chips + log only; hard to feel distance-to-done | Modal/sheet: bar + stage-mapped %, disclosure for log |
| D4 | **Log is not true live streaming mid-stage** | `VeriformisCLI.run` drains pipes **after** process exit (`readDataToEndOfFile`) | Stream pipe reads while process runs (Phase 1/2) |
| D5 | **No History** | Prior workspaces/bundles only if you remember Finder paths | Persist run records (paths, objective, status, log path) |
| D6 | **No Settings UI for CLI path** | Failure mode is alert “missing CLI”; no place to set `VERIFORMIS_CLI` | Settings: show resolved CLI, paste override, open docs |
| D21 | **GUI launch could not find CLI** (PATH + Info.plist) | Double-click `.app` has minimal PATH; Debug repo root was not in Info.plist | Fixed: inject plist key, probe `~/.local/bin` / Homebrew / `.venv/bin/veriformis`, clearer error + README prerequisites |
| D22 | **Single-file compile set source-root to the file** | `commonAncestor` used the file path → `invalid-source-locator` / double-slash `//Users/...` | Fixed: `defaultSourceRoot` uses parent directory(ies); tests added |

### P1 debugger / honesty (Phase 2 or late Phase 1)

| ID | Pain | Suggested fix |
| --- | --- | --- |
| D7 | **Objective names without plain-English subtitles** | Subtitle under picker: e.g. Full text → “whole cleaned document as `text` rows (Aptus may reject handoff)” |
| D8 | **“Split ratio (ppm)” is expert jargon** | Label as “Train share (parts per million)” + short help (e.g. 400000 ≈ 40% train) |
| D9 | **“Allow empty evaluation” opaque** | Help text: needed when split yields empty eval partition |
| D10 | **Source root is advanced** | Collapse under “Advanced”; auto root usually enough |
| D11 | **Failures are modal alert only** | Keep log + show stage + exit + last N lines in place (not only alert) |
| D12 | **No copy-to-clipboard for manifest SHA** | Copy button (Phase 2) |
| D13 | **No reveal workspace** | Button next to Reveal bundle |
| D14 | **full_text success can still fail Aptus** | After seal, optional handoff-verify status in Result (accepted/rejected + finding) |
| D15 | **Log not saved to disk as a run artifact** | Write `run.log` beside workspace/bundle for History |
| D16 | **Stage chip row may overflow** on narrow windows | Wrap chips or use vertical list / compact progress |

### P2 polish / later

| ID | Pain | Notes |
| --- | --- | --- |
| D17 | Multi-source encouraged by UI before KISS “one file” story | Keep multi-source in engine; Phase 1 default copy can say “start with one file” |
| D18 | No cancel mid-compile | Harder; post-private-beta |
| D19 | No re-run with same settings | Phase 2 optional |
| D20 | Verify stage listed in enum but not run after seal | Optional external_digest verify step in plan when SHA known |

## Confusing control names (glossary for Phase 1 copy)

| Current UI | Prefer for private beta |
| --- | --- |
| (implicit “workbench”) | **Compile** nav title |
| Objective raw titles | Title + one-line subtitle |
| Split ratio (ppm) | Train share (ppm) + tip |
| Allow empty evaluation | Allow empty evaluation partition |
| Write Aptus handoff | Write Aptus handoff file (training consumer) |
| Source root… | Advanced: source root |
| Compile to sealed bundle | Keep (good) |

## Dogfood scenarios checklist

- [x] Build Debug app  
- [x] Parity script  
- [x] Unit tests  
- [x] Single-file full_text seal + verify  
- [x] Multi-file continuation seal + handoff accept  
- [x] full_text handoff reject (expected)  
- [x] OCR refuse (expected)  
- [ ] **Owner:** interactive GUI session (drop, compile, read log) — please do once and append notes here if anything differs  

## How to re-dogfood quickly

```bash
cd macos
xcodegen generate
xcodebuild -scheme Veriformis -configuration Debug \
  -derivedDataPath /tmp/veriformis-dd build
open /tmp/veriformis-dd/Build/Products/Debug/Veriformis.app

# CLI parity (engine)
cd .. && bash macos/scripts/parity_check.sh
```

Set `VERIFORMIS_CLI` or keep repo layout so `uv run veriformis` resolves.

## Phase 0 exit

Agent-assisted Phase 0 is **done**: current workbench builds, parity holds, real compiles succeed, and a concrete punch list feeds Phase 1.

**Next:** Phase 1 private beta shell (sidebar + run sheet + history + settings), prioritizing D1–D6 and copy fixes D7–D10.
