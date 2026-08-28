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

## 2026-08-27: Item 16.2 merged; item 16.3 in progress

**Status:** Item 16.2 merged as PR #141 at
`4534975fb7d97aef392c6ba0481ea7bd4af1e052` after all 18 GitHub checks passed.
Clean local `main` equaled `origin/main` there before 16.3 began.

Item 16.3 wraps existing parser functions, `execute_mapping`, `_CONSTRUCTORS`,
quality detectors and preview-only gates, and the one export catalog behind a
built-in-only registry owned by `PipelineService`. Suffix dispatch, constructor
lookup, mapping execution, and export selectors stay on their current
functions. Third-party origin is refused. No loader, extra, CLI operation, or
MCP operation is added.

**Next action:** Run the complete item 16.3 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 16.4.

## 2026-08-27: Item 16.3 local gates green

**Status:** Existing bindings are wrapped without changing dispatch. The
focused registry and isolation suite passed 45 tests. Project tracking, Ruff,
the lock check, and `git diff --check` passed. The core suite passed 2,323
tests with 17 deselected and the one expected durability warning.

**Next action:** Publish the item 16.3 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 16.4.

## 2026-08-27: Item 16.3 merged; item 16.4 in progress

**Status:** Item 16.3 merged as PR #142 at
`ccf97f7de863d09cb71acd742df468fb19854740` after all 18 GitHub checks passed.

Item 16.4 adds one read-only `supported` declaration per built-in registry
binding. Discovery is `PipelineService.discover_extensions`, CLI
`extension-capabilities`, and MCP `extension_capabilities`. Unsloth stays
candidate. `ocr-image` stays explicitly unsupported. Empty extras stay empty.
Declarations are not executable bindings.

**Next action:** Run the complete item 16.4 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 16.5.

## 2026-08-27: Item 16.4 local gates green

**Status:** Read-only built-in declarations and discovery are in place. The
focused extension suite passed 50 tests. Project tracking, Ruff, the lock
check, and `git diff --check` passed. The core suite passed 2,328 tests with
17 deselected and the one expected durability warning.

**Next action:** Publish the item 16.4 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 16.5.

## 2026-08-27: Item 16.4 merged; item 16.5 in progress

**Status:** Item 16.4 merged as PR #143 at
`e70c13d6f42cc884c1599a96fd92cda052dd1d42` after all 18 GitHub checks passed.

Item 16.5 selects `.txt` only through the internal protocol. Parse reports and
source identities stay identical to `parse_text`. Markdown, code, and other
suffixes keep existing dispatch. Unknown text-parser contract versions fail
closed and name the supported version.

**Next action:** Run the complete item 16.5 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 16.6.

## 2026-08-27: Item 16.5 local gates green

**Status:** `.txt` is selected through the protocol. Focused tests passed.
The core suite passed 2,331 tests with 17 deselected.

**Next action:** Publish the item 16.5 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 16.6.

## 2026-08-27: Item 16.5 merged; item 16.6 in progress

**Status:** Item 16.5 merged as PR #144 at
`858b2833f041480e22fd415f484ad4075da4c4d0` after all 18 GitHub checks passed.
Clean local `main` equaled `origin/main` there before 16.6 began.

Item 16.6 binds generic `split-jsonl-directory` only through the protocol and
returns the same private catalog object. Canonical JSON, constrained CSV,
columnar containers, and every consumer profile stay on the catalog loop.
Unknown exporter contract versions fail closed and name the supported version.
Still one catalog. Still no trainer claim.

**Next action:** Run the complete item 16.6 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 16.7.

## 2026-08-27: Item 16.6 local gates green

**Status:** Generic `split-jsonl-directory` is bound through the protocol and
is the same catalog object. Focused tests passed. The core suite passed 2,337
tests with 17 deselected and the one expected durability warning.

**Next action:** Publish the item 16.6 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 16.7.

## 2026-08-27: Item 16.6 merged; item 16.7 in progress

**Status:** Item 16.6 merged as PR #145 at
`13e3280ac6f27a3e8c6484f0c6e380836723ddc9` after all 18 GitHub checks passed.
Clean local `main` equaled `origin/main` there before 16.7 began.

Item 16.7 freezes source and export goldens for the two migrated exemplars
and adds negative cases: unknown kind, unknown contract version, missing
extra, broken declaration identity, and unapproved third-party origin.
Errors name exact contract versions. The kit is test-only.

**Next action:** Run the complete item 16.7 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 16.8.

## 2026-08-27: Item 16.7 local gates green

**Status:** Frozen text and split-JSONL goldens match protocol-bound output.
Negative cases fail closed and name contract versions. Focused tests passed.
The core suite passed 2,348 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 16.7 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 16.8.
