# Private Beta Mac Workbench — Vision and Plan

**Status:** Owner-directed product plan (not a public-release claim)

**Created:** 2026-08-06

**Maturity context:** Version `0.1.0` remains development **alpha** until a
deliberate beta label cut. This document defines a **private** Mac workbench
beta used for dogfooding, debugging, and making the real compiler path
comfortable — not App Store distribution and not a multi-format converter
product.

**Related authorities:**

- [Current implementation status](../current-status.md)
- [Product contract](../product-contract.md)
- [Beta limitations](../beta-limitations.md)
- [Release guide](../release.md)
- [macOS workbench](../../macos/README.md)
- [Build roadmap](2026-07-29-veriformis-roadmap.md) (Group 7 workbench; Group 9 packaging)

**Implementation baseline:** Group 7 thin SwiftUI adapter under `macos/`;
composition root remains `PipelineService` / `veriformis` CLI.

---

## 1. The idea (one sentence)

**Compile** means: turn supported raw sources into a **validated,
provenance-sealed training dataset** (which may contain JSONL rows you can
train on) — not a shallow file-format flip.

### 1.1 Convert vs compile

| Word people use | What they often mean | What Veriformis does |
| --- | --- | --- |
| Convert | File A → file B (encoding/container) | Not the product center |
| Compile | Multi-stage pipeline with policy and a sealed artifact | **This product** |

Everyday analogy: **convert** is closer to “Save as…”; **compile** is closer
to a real build — many passes, invariants, and an artifact you can trust.

The private-beta app helps a human run that **compile** path with a simple UI
and excellent live visibility. It does not pretend to be a universal
HTML→Parquet toolbox.

### 1.2 What “LLM-usable dataset” means here

Users correctly want something like:

> Take HTML, TXT, Markdown, … and produce training-usable data.

In Veriformis that means:

```text
supported raw sources
  → parse → clean → chunk → construct → curate → split
  → format → validate → seal
  → optional Aptus handoff
  → independently verifiable .vfbundle
```

The sealed product’s training partitions are **JSONL** today
(`data/train.jsonl`, `data/evaluation.jsonl`, plus provenance). Chat-style
shapes (prompt/completion, messages, …) come from **training objectives and
row schemas**, not from picking a random file extension. Formats such as
Parquet, Arrow, ShareGPT export packs, HDF5, etc. are **possible later
exports or post-processors**, not the definition of a finished compile.

### 1.3 Product principles (non-negotiable)

1. **KISS** — few screens, obvious navigation, one primary action.
2. **Thin adapter** — GUI shells the `veriformis` CLI; digests match terminal.
3. **Honest outputs** — success means seal (+ handoff when applicable), not a
   pretend “any format” export matrix.
4. **Debugger-first** — live log, retained logs, digests, reveal-in-Finder.
5. **Fail closed** — unsupported input and pipeline failures stay visible.
6. **Private beta packaging** — local/dev builds first; signed public Mac is a
   separate Group 9 owner checklist.

---

## 2. Final vision

### 2.1 Who it is for

- Primary: the owner, as a daily debugger and confidence tool.
- Secondary (later): a small private beta cohort under explicit limitations.

### 2.2 Information architecture

Left sidebar (or equivalent simple navigation):

| Nav item | Role |
| --- | --- |
| **Home** | Status, last run, “CLI ready?”, short tips |
| **Compile** | The workbench: sources → options → Start |
| **History** | Past runs: open log, reveal bundle, status |
| **Settings** | CLI resolution, default output directory, defaults |

No multi-page wizard. No dashboard cosplay.

### 2.3 Compile experience (target UX)

1. **Input** — drag-and-drop and/or file picker.  
   Private-beta default: **one primary source file** for clarity (engine may
   already support multi-source; multi-source UI is a later enhancement).
2. **Objective** — training objective picker with plain-language subtitles  
   (`full_text`, `continuation`, …).
3. **Objective-specific options only** — e.g. continuation split ratio; no
   unrelated knobs.
4. **Output directory** — where the `.vfbundle` is written.
5. **Aptus handoff** — on/off (default on for supervised / Aptus-friendly paths).
6. **Start** — opens a run sheet inspired by Disk Utility First Aid:
   - progress bar and **percent** (stage-mapped, honest bands);
   - disclosure control that expands a **live log**;
   - clear success / failure with stage identity.
7. **Result** — reveal sealed bundle, handoff path if any, copy digests.

Each run writes a **detailed log** on disk (History can reopen it). Live log
is for watching; file log is for forensics.

### 2.4 Success criteria (private beta workbench)

A private-beta workbench is “good enough” when the owner can:

1. Build and launch the Mac app from the repo without terminal for normal runs.
2. Compile a real source through seal with digests matching CLI parity.
3. Watch stage progress and a live log during the run.
4. Reopen past runs (log + bundle path) from History.
5. Understand failures without guessing which stage broke.

It is **not** required for private beta that the app:

- export Parquet/Arrow/HDF5/WARC/…;
- multi-convert many formats to many formats in one click;
- be notarized for Gatekeeper-silent distribution to strangers.

### 2.5 Long-term vision (after private beta)

Only after the compile path is muscle memory:

1. Optional **export** of sealed partitions into additional containers the
   project actually implements (starting with plain JSONL outside the bundle if
   useful).
2. Optional **multi-source** compile UI (engine already multi-source).
3. Optional wider packaging (signed/notarized Mac) per [release.md](../release.md).
4. Explicit multi-in / multi-out remains an **endgame**, not a near-term gate.

---

## 3. The plan (phased)

### Phase 0 — Dogfood current workbench

**Status:** Complete (2026-08-06 agent-assisted dogfood).  
**Evidence:** [dev/active/private-beta-workbench/phase-0-dogfood.md](../../dev/active/private-beta-workbench/phase-0-dogfood.md)

- Build and run `macos/` workbench against current `main`.
- Compile real sources; break things; live in the log.
- Note confusing control names, missing affordances, and pain points.
- Outcome: punch list that informs Phase 1.

**Exit:** Punch list landed; build + parity + real compiles verified. Owner
should still do one interactive GUI pass and append notes if needed.

### Phase 1 — Private beta shell (UI)

**Status:** Implemented (2026-08-06).  
**Design:** [dev/active/private-beta-workbench/phase-1-design.md](../../dev/active/private-beta-workbench/phase-1-design.md)

**Scope:** Information architecture and run visibility. No new dataset formats.

- Sidebar: Home / Compile / History / Settings.
- Compile: drop zone, objective (+ few options), output dir, Start.
- Start sheet: progress + % + expandable live log.
- History: past runs, open log, reveal bundle.
- Settings: CLI path resolution, default output directory.
- Keep thin CLI adapter; parity script remains green.
- Dogfood items D1–D10, D15, live stream D4, source-root directory rule.

**Exit:** Owner can do a full compile from the new shell with live log and
history retention.

### Phase 2 — Debugger power

**Status:** Implemented (2026-08-06).  
**Notes:** [dev/active/private-beta-workbench/phase-2-design.md](../../dev/active/private-beta-workbench/phase-2-design.md)

- Failures show stage, exit code, and last log lines.
- One-click copy manifest SHA-256 / assignment digest.
- Reveal in Finder for workspace and bundle.
- Re-run with same settings (last run or History entry).

**Exit:** Debugging a failed compile is faster in the app than retyping CLI.

### Phase 3 — Export menu (optional)

- Explicit “Export partition as…” only for formats actually implemented.
- First candidate: plain JSONL copies of train/eval **after** a successful
  seal (never a substitute for seal).

**Exit:** Optional convenience export exists without diluting the sealed product.

### Phase 4 — Heavy post-processors (only if still needed)

- Parquet / Arrow / similar as **optional post-processors**.
- Never replace seal, validation, or provenance contracts.

**Exit:** Documented, optional, fail-closed exporters — or consciously deferred.

---

## 4. Explicit non-goals (private beta)

- Universal “convert any file to any of 25 ML formats.”
- Hand-holding every training objective with a multi-page wizard.
- OCR / scanned PDF recovery.
- LLM generation inside the compile path (Group 8 remains separate).
- Claiming public beta or public Mac readiness without checklists in
  [beta-limitations.md](../beta-limitations.md) and [release.md](../release.md).

---

## 5. Technical constraints

| Constraint | Rule |
| --- | --- |
| Composition root | `PipelineService` / CLI only; SwiftUI does not reimplement stages |
| Digest parity | Workbench sequence matches CLI; keep `macos/scripts/parity_check.sh` |
| Progress model | Stage-mapped percent is honest; avoid fake byte precision |
| Packaging | Local private builds first; notarization is owner Group 9 remainder |
| Limitations | OCR no; Aptus rejects plain `text` rows for current backend policy |

---

## 6. Working vocabulary (for UI copy)

| Prefer | Avoid (in this product) |
| --- | --- |
| Compile | Convert (as the primary verb) |
| Sources | “Input format pack” |
| Objective | “Output format = Parquet” |
| Sealed bundle / `.vfbundle` | “The JSON file” as the whole product |
| Training rows / partitions | “Export” as the only success |
| Live log / run log | Silent spinner |

---

## 7. Execution order agreed with owner

1. Land this document on `main` (documentation PR).
2. **Phase 0** dogfood — owner OK after merge.
3. Then implement **Phase 1** (and later phases) as normal workbench changes.

This plan does not replace the numbered roadmap; it specializes Group 7
workbench evolution toward a private beta debugger under KISS discipline.
