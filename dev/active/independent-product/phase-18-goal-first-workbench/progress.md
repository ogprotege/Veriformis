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
