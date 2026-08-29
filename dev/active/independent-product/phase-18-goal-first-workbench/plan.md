# Phase 18 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-28

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 18; [program.json](../program.json); [project tracking policy](../../../../docs/governance/project-tracking.md); operator plan `/Users/biscuit/Desktop/Phase18-Plan.txt`.

**Predecessor:** Phase 17 closeout merged as PR #159 at
`7d851c8a531eac7217051effe000048403a3b866`. Clean local `main` equaled
`origin/main` there when this packet opened.

Each numbered item is one sequential pull request. Every pull request must pass
focused tests, project tracking, Ruff, the lock check, `git diff --check`, the
core test suite, and every GitHub check. Items that change `macos/` also pass
local `xcodebuild` tests and `macos/scripts/parity_check.sh`. The pull request
then merges and leaves clean local `main` equal to `origin/main` before the
next item begins.

Phase 18 does not start Phase 19. Swift owns no dataset policy.

## Goal

Make the full independent workflow approachable on Mac without hiding
contracts or rebuilding them in Swift. A first-time test user can complete
the final workflow on a clean Mac without Aptus or the terminal; artifacts
and receipts match the CLI golden path.

## Architecture

`PipelineService` owns policy. The Mac workbench is a thin CLI adapter.
Document-source, dataset-row, and mixed are the compiler paths. Mapping is
confirm-then-map. Export and review wrap existing CLI packets. Recipe
defaults stay in versioned preset data.

## Locks

| ID | Lock |
| --- | --- |
| L1 | Execute sequential green PRs. Item 18.1 opens the packet; 18.10 closes it. |
| L2 | Item 18.1 adds honesty records and isolation tests only. |
| L3 | Swift is a thin CLI adapter. `PipelineService` owns policy. No second catalog. |
| L4 | Expose only capabilities already owned by shared services. |
| L5 | Workbench success is seal + verify, not a trainer handoff. Aptus stays optional. |
| L6 | Document-source, dataset-row, and mixed are the only compiler paths. |
| L7 | Mapping is confirm-then-map with `mapped_value`. Unconfirmed plans fail closed. |
| L8 | Default `review_policy` stays `none`. Review screens wrap existing queues. |
| L9 | Quality stays preview-only. No quality-report command. No heuristic blocks seal. |
| L10 | Export always shows the source bundle and receipt. Membership is not mutated. |
| L11 | Existing SFT, Phase 16, and Phase 17 goldens stay byte-identical. |
| L12 | ADR-0017 Decision A and ADR-0018 Decision A stand. No plugin UI. No generator UI. |
| L13 | Phase 17 families appear only through dataset-row mapping. No family-to-trainer chrome. |
| L14 | Accessibility and keyboard are required for new screens. Skip virtualization and full localization with records. |
| L15 | Do not start Phase 19 from this packet. Signed/notarized Mac remains the Group 9 owner remainder. |

## Checklist

### 18.1 Open the goal-first-workbench packet

**Branch:** `phase18/01-workbench-packet`

- [x] Confirm Phase 17 complete and clean `main` at PR #159.
- [x] Create the standard packet and move Phase 18 to `in_progress`.
- [x] Record L1 through L15 and reconcile active tracking documents.
- [x] Add isolation tests for the current workbench.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

No new screen, input mode, mapping confirm path, export execute, review
queue, accessibility audit, or CLI-equivalent copy is permitted in this item.

### 18.2 Pin the thin-adapter workbench contract

**Branch:** `phase18/02-thin-adapter-contract`

- [x] Add ADR-0019 covering CLI ownership, no second catalog, fail-closed
      truncated/cancelled discovery, ADR-0017, and ADR-0018.
- [x] Add `veriformis.workbench-adapter/v1` as a schema pin.
- [x] Add no Review, Exports, or dataset-row UI.

### 18.3 Replace Aptus-centered project copy with goal-first IA

**Branch:** `phase18/03-project-ia`

- [x] Reorganize copy around Sources, Goal, Compile, History, and optional
      Integrations. Keep Review and Exports out of the sidebar.
- [x] Surface a copyable CLI equivalent of the current compile plan.

### 18.4 Add document, dataset-row, and mixed modes with mapping preview

**Branch:** `phase18/04-input-modes-and-mapping`

- [ ] Select ADR-0010 modes. Confirm-then-map. Family goals only on
      dataset-row.

### 18.5 Expose inspectable advanced settings from presets

**Branch:** `phase18/05-inspectable-settings`

- [ ] Progressive disclosure of the preset and goal contract. Overrides
      remain explicit.

### 18.6 Show pre-publication samples

**Branch:** `phase18/06-prepublication-samples`

- [ ] Show recovery, mapping, row, supervised region, preview-only quality,
      exclusions, split facts, and export destination tree. Omit oversized
      payloads whole.

### 18.7 Add generic and named-profile export flows

**Branch:** `phase18/07-export-flows`

- [ ] Wire the existing Swift export bridge. Always display bundle and
      receipt. Profiles refuse family schemas.

### 18.8 Add Mac Review over existing review packets

**Branch:** `phase18/08-review-flows`

- [ ] Wrap review-export, review-import, and review-submit. Default
      `review_policy` stays `none`.

### 18.9 Add accessibility, keyboard, CLI equivalents, and error recovery

**Branch:** `phase18/09-accessibility-and-cli-equivalents`

- [ ] Labels, keyboard, copyable CLI, error recovery. Skip virtualization
      and full localization with records.

### 18.10 Add adversarial workbench tests and close Phase 18

**Branch:** `phase18/10-adversarial-closeout`

- [ ] Refuse unconfirmed mapping, truncated discovery, family-on-refusing
      profile, nested CSV, required-review seal, generator/plugin UI, and
      Aptus-on-by-default. Reprove digest parity. Close Phase 18. Do not
      start Phase 19 from this packet.

## Skip rules

| Item | Skip only when |
| --- | --- |
| 18.1–18.4, 18.7, 18.8, 18.10 | Do not skip. |
| 18.5 inspectable settings | 18.3 already surfaces the full preset contract. Prefer keeping it separate. |
| 18.6 pre-publication samples | 18.4+18.7 already show the same samples. Prefer a dedicated item. |
| 18.9 virtualization | No measured list bottleneck (expected). |
| 18.9 full localization | English v1 locale (expected). |
| Family-to-trainer mapping UI | Phase 17 did not pin those adapters. |
| Generator UI, plugin UI, Hub, signed Mac | Forbidden / out of scope. Record at closeout. |
| GitHub xcodebuild job | Not licensed (expected). |

## Exit gate

A first-time test user can complete sources to a sealed, independently
verified `.vfbundle` in the workbench without Aptus or Terminal. Document,
dataset-row, and mixed modes exist. Mapping is confirm-then-map. Export
shows bundle and receipt. Review is optional and CLI-backed. Swift owns no
policy. Existing goldens stay unchanged.
