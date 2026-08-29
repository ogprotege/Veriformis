# Phase 18 Progress

Append-only. Corrections add a later entry.

## 2026-08-28: Phase 18 opened; item 18.1 in progress

**Status:** Packet created from clean `main` at
`7d851c8a531eac7217051effe000048403a3b866`, the Phase 17 closeout merge in
PR #159. Phase 18 was `planned` with no packet. All declared dependencies
were complete. Phases 16 and 17 were also complete.

Item 18.1 records the current private-beta workbench. Sidebar remains Home /
Compile / History / Settings. The compile plan remains document-source.
Mapping-detect and export CLI bridges exist in Swift and are unused by
views. Default Aptus handoff stays off. There is no `GeneratorPass`.
ADR-0017 and ADR-0018 Decision A still hold.

**Next action:** Run the complete item 18.1 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 18.2.

## 2026-08-28: Item 18.1 local gates green

**Status:** The current workbench baseline is recorded without adding
product behavior. The focused isolation suite passed 8 tests. Project
tracking, Ruff, the lock check, and `git diff --check` passed. The core
suite passed 2,471 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 18.1 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.2.

## 2026-08-28: Item 18.1 merged; item 18.2 in progress

**Status:** Item 18.1 merged as PR #160 at
`73bf306bf53a650452f5d5dba5082ef842ced732`. Clean local `main` equals
`origin/main` there.

Item 18.2 adds ADR-0019 Decision A and `veriformis.workbench-adapter/v1`
as a schema pin. PipelineService owns policy. Swift is a process adapter.
Unknown commands, fields, and contract versions fail closed. Loading a
pin is not a screen. Review, Exports, and dataset-row UI remain absent.

**Next action:** Run the complete item 18.2 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 18.3.

## 2026-08-28: Item 18.2 local gates green

**Status:** The thin-adapter contract is a schema pin only. Focused
workbench tests passed 62. Project tracking, Ruff, the lock check, and
`git diff --check` passed. The core suite passed 2,525 tests with 17
deselected and the one expected durability warning.

**Next action:** Publish the item 18.2 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.3.

## 2026-08-28: Item 18.2 merged; item 18.3 in progress

**Status:** Item 18.2 merged as PR #161 at
`56b911def5ffe04aa38a65bde2496f9f33367a01`. Clean local `main` equals
`origin/main` there.

Item 18.3 replaces Aptus-centered copy with goal-first IA. Compile is
Sources, Goal, CLI equivalent, and optional Integrations. Sidebar stays
Home / Compile / History / Settings. Compile stays document-source.

**Next action:** Run the complete item 18.3 local gates, including
xcodebuild tests and parity, publish the pull request, require every
GitHub check, merge, and synchronize clean `main` before item 18.4.

## 2026-08-28: Item 18.3 local gates green

**Status:** Goal-first IA is copy and CLI equivalent only. Compile stays
document-source. Aptus stays optional Integrations. Focused workbench
tests passed 67. xcodebuild tests passed 100. Parity passed. Project
tracking, Ruff, the lock check, and `git diff --check` passed. The core
suite passed 2,530 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 18.3 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.4.

## 2026-08-28: Item 18.3 merged; item 18.4 in progress

**Status:** Item 18.3 merged as PR #162 at
`acf8ee405616d3b6ae8fa443cc3eb49f77bc790a`. Clean local `main` equals
`origin/main` there.

Item 18.4 adds the ADR-0010 mode picker and confirm-then-map. Dataset-row
wraps mapping-detect, operator confirm, mapping-preview, then
`parse --mode dataset-row` and `map`. Mixed refuses fused document and
row members. Family goals wait for a confirmed mapping plan. Review and
Exports stay out of the sidebar.

**Next action:** Run the complete item 18.4 local gates, including
xcodebuild tests and parity, publish the pull request, require every
GitHub check, merge, and synchronize clean `main` before item 18.5.

## 2026-08-29: Item 18.4 local gates green

**Status:** ADR-0010 modes and confirm-then-map are on Compile. Document-source
still omits `--mode`. Dataset-row runs parse, map, then the finished-dataset
tail. Mixed refuses fused document and row members. Family goals wait for a
confirmed mapping plan. Review and Exports stay out of the sidebar. Focused
workbench tests passed 75. xcodebuild tests passed 109. Parity passed. Project
tracking, Ruff, the lock check, and `git diff --check` passed. The core
suite passed 2,538 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 18.4 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.5.

## 2026-08-29: Item 18.4 merged; item 18.5 in progress

**Status:** Item 18.4 merged as PR #163 at
`c0c10b9`. Clean local `main` equals `origin/main` there.

Item 18.5 exposes inspectable preset and goal contract fields. Overrides
stay explicit. Validation and profiles are inspect-only until 18.7.

**Next action:** Run the complete item 18.5 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 18.6.

## 2026-08-29: Item 18.5 local gates green

**Status:** Inspectable Recipe settings bind the selected preset and goal
contract. Overrides stay explicit. Validation and profiles are inspect-only.
Focused workbench tests passed 79. xcodebuild tests passed 110. Parity
passed. Tracking, Ruff, lock, and `git diff --check` passed. The core
suite passed 2,542 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 18.5 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.6.

## 2026-08-29: Item 18.5 merged; item 18.6 in progress

**Status:** Item 18.5 merged as PR #164 at `2faad0d`. Clean local `main`
equals `origin/main` there.

Item 18.6 shows pre-publication samples on the compile result. Quality
findings stay preview-only. Dry-run destination tree waits until a
container is selected. No renderer. No destination write.

**Next action:** Run the complete item 18.6 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 18.7.

## 2026-08-29: Item 18.6 local gates green

**Status:** Pre-publication samples are on the compile result. Quality
findings stay preview-only. No renderer. No destination write. Focused
workbench tests passed 82. xcodebuild tests passed 111. Parity passed.
Tracking, Ruff, lock, and `git diff --check` passed. The core suite
passed 2,545 tests with 17 deselected and the one expected durability
warning.

**Next action:** Publish the item 18.6 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.7.

## 2026-08-29: Item 18.6 merged; item 18.7 in progress

**Status:** Item 18.6 merged as PR #165 at `093a4fd`. Clean local `main`
equals `origin/main` there.

Item 18.7 adds the Exports sidebar destination and wires discover, dry-run,
inspect, operator-confirmed execute, and verify. Generic containers come
first. Named profiles appear only for schemas they admit. Bundle identity
and receipt stay visible. Review stays out of the sidebar.

**Next action:** Run the complete item 18.7 local gates, including
xcodebuild tests and parity, publish the pull request, require every
GitHub check, merge, and synchronize clean `main` before item 18.8.

## 2026-08-29: Item 18.7 local gates green

**Status:** Exports wraps the existing CLI export bridge. Generic
containers come first. Named profiles appear only for admitted schemas.
Execute waits for an operator-confirmed dry-run plan. Focused workbench
tests passed 88. xcodebuild tests passed 112. Parity passed. Tracking,
Ruff, lock, and `git diff --check` passed. The core suite passed 2,551
tests with 17 deselected and the one expected durability warning.

**Next action:** Publish the item 18.7 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.8.
