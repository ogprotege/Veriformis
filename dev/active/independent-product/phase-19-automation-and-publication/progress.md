# Phase 19 Progress

Append-only. Corrections add a later entry.

## 2026-08-31: Phase 19 opened; item 19.1 in progress

**Status:** Packet created from clean `main` at
`2737476eb2df83d82f575e3735b68487ee7cabc8`, PR #170 after the Phase 18
closeout merge in PR #169 at `9f384eeedb401441c564c511b642904c403dad38`.
Phase 19 was `planned` with no packet. All declared dependencies (4, 7, 8,
9, 10, 15, 18) were complete. Phases 5, 6, 11–14, 16, and 17 were also
complete.

Item 19.1 records the current automation boundary. `veriformis.pipeline/v1`
omits mode, map, and export. `veriformis run` exists. MCP has no Hub tool
and no quality-report tool. CLI has no hub-upload. Package metadata has no
`HF_TOKEN`. Default `review_policy` stays `none`. Quality gates remain
`admitted_to_block is False`. Core compile names no network client.

**Next action:** Run the complete item 19.1 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 19.2.

## 2026-08-31: Item 19.1 local gates green

**Status:** The current automation boundary is recorded without adding
product behavior. The focused isolation suite passed 9 tests. The Phase
18 closeout test now records that Phase 19 opened under its own packet
and Phase 20 stays planned. Project tracking, Ruff, the lock check, and
`git diff --check` passed. The core suite passed 2,580 tests with 17
deselected and the one expected durability warning.

**Next action:** Publish the item 19.1 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 19.2.

## 2026-08-31: Item 19.1 merged; item 19.2 in progress

**Status:** Item 19.1 merged as PR #171 at
`d8d91c264868438e4c8b91d66e754e1dd0cdf68e`. Clean local `main` equals
`origin/main` there.

Item 19.2 pins additive `veriformis.project-spec/v1`. Loading is not
execute. `veriformis.pipeline/v1` stays. Unknown fields, unknown versions,
unconfirmed mapping, mixed fused members, and family-on-refusing profiles
fail closed. No dry-run, lock, resume, MCP, CI, or Hub.

**Next action:** Run the complete item 19.2 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 19.3.

## 2026-08-31: Item 19.2 local gates green

**Status:** Additive `veriformis.project-spec/v1` is a schema pin only.
Focused project-spec and isolation tests passed 27. Pipeline spec
defect-close tests still pass. Project tracking, Ruff, the lock check,
and `git diff --check` passed. The core suite passed 2,598 tests with 17
deselected and the one expected durability warning.

**Next action:** Publish the item 19.2 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 19.3.

## 2026-08-31: Item 19.2 merged; item 19.3 in progress

**Status:** Item 19.2 merged as PR #172 at
`eb7777eae7b755637d4639a7316121303affc19f`. Clean local `main` equals
`origin/main` there.

Item 19.3 emits JSON Schema from the project-spec model, dry-runs a spec
without writing a workspace, bundle, or destination, writes
`veriformis.project-lock/v1`, and adds environment inspection. No resume,
map/export execute, or Hub.

**Next action:** Run the complete item 19.3 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 19.4.

## 2026-08-31: Item 19.3 local gates green

**Status:** Schema is generated from the project-spec model. Dry-run writes
nothing. The lock pins spec digest, versions, and extras. Environment
inspection names no secrets. Focused automation tests passed 40. Project
tracking, Ruff, the lock check, and `git diff --check` passed. The core
suite passed 2,611 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 19.3 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 19.4.

## 2026-08-31: Item 19.3 merged; item 19.4 in progress

**Status:** Item 19.3 merged as PR #173 at
`0a29f44ffa00182d0f9ac430ef880f8d8a940ec9`. Clean local `main` equals
`origin/main` there.

Item 19.4 adds machine-readable diagnostics, confirmed spec execute
through PipelineService, and lock-matched resume. Document-source parse
omits `--mode`. Dataset-row is parse `--mode dataset-row` then `map`
then the finished-dataset tail. Resume requires matching lock, HEAD,
and source identities. Export is not auto-run. No Hub. No MCP spec
tool.

**Next action:** Run the complete item 19.4 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 19.5.

## 2026-08-31: Item 19.4 local gates green

**Status:** Machine-readable diagnostics fail closed on truncated JSON.
Confirmed spec-run executes through PipelineService. Document-source
parse omits `--mode`. Dataset-row is parse `--mode dataset-row` then
`map` then the finished-dataset tail. Resume requires matching lock,
HEAD, and source identities. Export is not auto-run. Focused automation
tests passed 50. Project tracking, Ruff, the lock check, and
`git diff --check` passed. The core suite passed 2,621 tests with 17
deselected and the one expected durability warning.

**Next action:** Publish the item 19.4 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 19.5.

## 2026-08-31: Item 19.4 merged; item 19.5 in progress

**Status:** Item 19.4 merged as PR #174 at
`f80bab4ffd714bec6dfcf354050b4aa71735bb0a`. Clean local `main` equals
`origin/main` there.

Item 19.5 wraps project-spec schema, dry-run, lock, env inspect, run, and
resume as MCP tools. `run_pipeline` stays `veriformis.pipeline/v1`.
`package` / `package-verify` MCP wraps are skipped with a record. No Hub.
No quality-report.

**Next action:** Run the complete item 19.5 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 19.6.

## 2026-08-31: Item 19.5 local gates green

**Status:** MCP wraps project-spec schema, dry-run, lock, env inspect,
run, and resume. `run_pipeline` stays `veriformis.pipeline/v1`.
`package` / `package-verify` MCP wraps are skipped with a record. No Hub.
No quality-report. Focused automation tests passed 54. Project tracking,
Ruff, the lock check, and `git diff --check` passed. The core suite
passed 2,625 tests with 17 deselected and the one expected durability
warning.

**Next action:** Publish the item 19.5 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 19.6.

## 2026-08-31: Item 19.5 merged; item 19.6 in progress

**Status:** Item 19.5 merged as PR #175 at
`95acb66787a6e7775bb4f9f1493296f76a163088`. Clean local `main` equals
`origin/main` there.

Item 19.6 adds retained project-spec fixtures, a committed fingerprint,
and a CI example that does not replace golden-compile. No Hub. No
secrets. No xcodebuild.

**Next action:** Run the complete item 19.6 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 19.7.

## 2026-08-31: Item 19.6 local gates green

**Status:** Retained project-spec fixtures compile to a committed
manifest SHA-256. The CI example job does not replace golden-compile.
No Hub. No secrets. No xcodebuild. Focused automation tests passed 56.
Project tracking, Ruff, the lock check, and `git diff --check` passed.
The core suite passed 2,627 tests with 17 deselected and the one
expected durability warning.

**Next action:** Publish the item 19.6 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 19.7.

## 2026-08-31: Item 19.6 merged; item 19.7 in progress

**Status:** Item 19.6 merged as PR #176 at
`3987d6d3fc9706f21e4182ee65388d0027d11aea`. Clean local `main` equals
`origin/main` there.

Item 19.7 pins ADR-0020 Decision A. `veriformis.publication-adapter/v1`
is a schema pin. Loading is not upload. No Hub execute.

**Next action:** Run the complete item 19.7 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 19.8.

## 2026-08-31: Item 19.7 local gates green

**Status:** ADR-0020 Decision A stands. The publication adapter is a
schema pin. Loading is not upload. CLI and MCP have no Hub tool.
Focused automation tests passed 60. Project tracking, Ruff, the lock
check, and `git diff --check` passed. The core suite passed 2,631 tests
with 17 deselected and the one expected durability warning.

**Next action:** Publish the item 19.7 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 19.8.
