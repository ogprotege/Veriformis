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
