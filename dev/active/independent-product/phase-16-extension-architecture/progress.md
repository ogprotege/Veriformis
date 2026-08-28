# Phase 16 Progress

Append-only. Corrections add a later entry.

## 2026-08-27: Phase 16 opened; item 16.1 in progress

**Status:** Packet created from clean `main` at
`435bd63c90778674ff4eb68a5d882a168349baca`, the Phase 15 closeout merge in
PR #139. Phase 16 was `planned` with no packet. All dependencies were
complete.

Item 16.1 records the current architecture only. Parser dispatch is still a
suffix chain. Constructors use a private `(id, version)` map. Row mapping is a
compiler function. Quality gates remain preview-only. Exporters and consumer
profiles share one private catalog. Optional extras are empty. No extension
module, public plugin API, entry-point loader, CLI operation, or MCP operation
exists.

**Next action:** Run the complete item 16.1 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main` before
item 16.2.

## 2026-08-27: Item 16.1 local gates green

**Status:** The pre-extension baseline is recorded without adding product
behavior. The focused isolation suite passed 11 tests. Project tracking, Ruff,
the lock check, and `git diff --check` passed. The core suite passed 2,289
tests with 17 deselected and the one expected durability warning.

The first core run exposed a test-isolation defect in the new clean-import
assertion because a prior test had already imported `datasets` into the shared
pytest process. The assertion now runs in a fresh interpreter. No product code
changed.

**Next action:** Publish the item 16.1 pull request, require every GitHub check,
merge, and synchronize clean `main` before item 16.2.

## 2026-08-27: Item 16.1 merged; item 16.2 in progress

**Status:** Item 16.1 merged as PR #140 at
`76c0e2e90d95874b3e117f95554c428c70da1daf` after all 18 GitHub checks passed.
Clean local `main` equaled `origin/main` there before 16.2 began.

Item 16.2 adds `veriformis.extension-protocol/v1` as a schema pin. Six kinds,
two origins, five lifecycle states, extras, deterministic requirements,
diagnostics, fixtures, and discovery metadata load and refuse. Unknown fields,
kinds, and contract versions fail closed and name the supported version.
Parser dispatch, constructors, the export catalog, and public surfaces stay
unchanged. No loader, executable registry, extra, CLI operation, or MCP
operation is added.

**Next action:** Run the complete item 16.2 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 16.3.

## 2026-08-27: Item 16.2 local gates green

**Status:** The internal protocol is a schema pin only. The focused protocol
and isolation suite passed 28 tests. Project tracking, Ruff, the lock check,
and `git diff --check` passed. The core suite passed 2,306 tests with 17
deselected and the one expected durability warning.

**Next action:** Publish the item 16.2 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 16.3.
