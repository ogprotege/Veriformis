# Post-20 Defect Closure

**Status:** Complete. All eight local exit gates passed; PR #204 records the final CI and merge evidence.

**Started:** 2026-09-09

**Kind:** Remainder defect-closure packet (not a numbered roadmap phase)

**Opened from:** the 2026-09-09 full-repository audit of `main` at `5d617f8`
(after PR #202), with independent-product Phases 0–20 complete and the
[post-20 claim-honesty remainder](../post-20-claim-honesty/README.md) closed.

This packet is **not Phase 21**. Do not invent a Phase 21 from it. Version
remains `0.1.0` development alpha. The frozen claim stays
`cli-first-independent-core`. Hub execute, generator, plugin loader, and
default-parse `ocr-image` stay excluded under their ADRs.

## Purpose

Close the defects, contract drift, dead test signal, and scalability blockers
that eight read-only audits found behind a green 2,701-test baseline. Every
gate passed on the audited tree; the findings live in paths the fixtures did
not cross: undeclared HTML charsets, JSON strings carrying U+2028, a wheel
that omits one packaged data file, a Mac screen whose argv the tests never
drove through the real CLI, a consumer check that trusted the descriptor it
was verifying, and authority documents frozen at Phase 8 or Phase 16.

## Scope

The defect register lives in [plan.md](plan.md) as items D-01 through D-35,
grouped into eight sequenced phases:

| Phase | Theme |
| --- | --- |
| 1 | Ship blockers and silent corruption |
| 2 | Claim-honesty reconciliation and tracking-checker teeth |
| 3 | Recovery-layer truthfulness and hardening (parser pin bumps) |
| 4 | Finished-dataset and export contract fidelity |
| 5 | Review, mapping, automation, and preflight completeness |
| 6 | Test and CI hardening |
| 7 | Performance and memory |
| 8 | Mac workbench robustness |

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Defect register, phases, and exit gates |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope and non-scope decisions |
| [risks.md](risks.md) | Active risks and controls |
| [evidence.md](evidence.md) | Verification proof per defect |
| [closeout.md](closeout.md) | Exit-gate judgment |

## Non-goals

No new objective, row schema, container, consumer profile, or input family.
No version bump. No Hub execute, generator, plugin loader, signed Mac, or
public-ready claim. `scale-support` tiers stay empty unless a later measured
baseline licenses one. `quality-report` stays a preview. Default
`review_policy` stays `none`.
