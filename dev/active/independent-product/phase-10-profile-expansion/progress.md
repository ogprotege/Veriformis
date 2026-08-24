# Phase 10 Progress

Append-only. Corrections add a later entry.

## 2026-08-24 — Phase 10 opened; item 10.1 in progress

**Status:** Packet created from clean `main` at
`abdcce6474aadd33fcf38a5360b63a4f8d293a5c` (PR #96).

Item 10.1 publishes ADR-0014 and keeps `axolotl`, `llama-factory`, and
`unsloth` as candidates. Selecting those consumer identifiers refuses as
Phase 10. Extras are empty lists. Do not emit those profiles. Aptus
remains the sibling handoff until item 10.6. Operator approval is
required after 10.2 before 10.3.

**Next action:** Publish the item 10.1 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 10.2.

## 2026-08-24 — Item 10.1 local gates green

**Status:** Packet, ADR-0014, empty extras, and candidate-refusal tests
are on `phase10/01-profile-expansion-packet`.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused isolation 22 passed;
core pytest 2053 passed, 15 deselected, 1 expected durability warning;
`git diff --check` clean.

**Next action:** Open the item 10.1 pull request. Require every GitHub
check, merge, and synchronize clean main before item 10.2.

## 2026-08-24 — Item 10.1 merged; item 10.2 in progress

**Status:** Item 10.1 merged as PR #97 at
`8df562fb9e0fd673cf39a53aaee6d82daecaf98c` after GitHub checks passed.
Clean local `main` equals `origin/main`.

Item 10.2 packages section-5 pins. Axolotl and LLaMA-Factory are
admitted for a later emit. Unsloth is experimental. Aptus is deferred
to 10.6. Extras stay empty. No trainer files.

**Next action:** Publish the item 10.2 pull request. Require green
GitHub checks, merge, and synchronize clean main. Then stop for
operator approval before item 10.3.

## 2026-08-24 — Item 10.2 local gates green

**Status:** Candidate admission catalog, CLI/MCP discovery, and tests
are on `phase10/02-admission-pins`.

Local gates: `uv lock --check`; `ruff check src tests`; tracking PASS;
focused admission/isolation tests passed; core pytest 2061 passed, 15
deselected, 1 expected durability warning; `git diff --check` clean.

**Next action:** Open the item 10.2 pull request. After merge, stop for
operator approval before item 10.3.

## 2026-08-24 — Item 10.2 merged; items 10.3–10.8 combined

**Status:** Item 10.2 merged as PR #98 at
`47297f658892d594378b8af24c150a132f3df346` after GitHub checks passed.
The operator asked to implement 10.3 through 10.8 fully in one pull
request, not six sequential PRs.

Axolotl is the first admitted emit. LLaMA-Factory is the second.
Unsloth is skipped with the experimental pin. Aptus becomes
`consumer_id=aptus` identity export; sibling handoff remains. Official-
schema harnesses and closeout fold into the same change. Extras stay
empty.

**Next action:** Finish the combined 10.3–10.8 change, pass local gates,
and open one pull request.

## 2026-08-24 — Items 10.3–10.8 local gates green

**Status:** Combined emit, Unsloth skip, Aptus-as-profile, harnesses, and
closeout are on `phase10/03-08-emit-harness-closeout`.

Local gates: `uv lock --check`; `ruff check src tests`; tracking PASS;
focused profile/isolation/taxonomy tests 197 passed, 3 skipped; core
pytest 2090 passed, 16 deselected, 1 expected durability warning;
`git diff --check` clean.

**Next action:** Open one pull request covering 10.3–10.8. Require every
GitHub check, merge, and synchronize clean main. Do not start Phase 11
or 13.
