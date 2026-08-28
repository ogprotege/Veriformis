# Phase 17 Progress

Append-only. Corrections add a later entry.

## 2026-08-28: Phase 17 opened; item 17.1 in progress

**Status:** Packet created from clean `main` at
`a1fbf04d58d73692cc4237b7d741c5da27022581`, the Phase 16 closeout merge in
PR #149. Phase 17 was `planned` with no packet. All dependencies were
complete.

Item 17.1 records the current SFT-only architecture. Implemented families
remain language-modeling and supervised fine-tuning. Row schemas remain the
four SFT shapes. `messages` remains exactly two turns. Mapping still has no
preference, tool, multimodal, or free multi-turn payload. Constructors remain
the five deterministic SFT constructors. There is no `GeneratorPass`. Trainer
profiles still refuse preference, tools, ranking, stepwise, unpaired
preference, and vision. Constrained CSV still admits only the three flat SFT
schemas. The extension protocol still has six kinds and no family kind.
ADR-0017 Decision A still holds.

**Next action:** Run the complete item 17.1 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main` before
item 17.2.

## 2026-08-28: Item 17.1 local gates green

**Status:** The SFT-only baseline is recorded without adding product
behavior. The focused isolation suite passed 16 tests. Project tracking, Ruff,
the lock check, and `git diff --check` passed. The core suite passed 2,376
tests with 17 deselected and the one expected durability warning.

**Next action:** Publish the item 17.1 pull request, require every GitHub check,
merge, and synchronize clean `main` before item 17.2.

## 2026-08-28: Item 17.1 merged; item 17.2 in progress

**Status:** Item 17.1 merged as PR #150 at
`712d28a1a5d3201007601b6daf9681c97221fcf4`. Clean local `main` equals
`origin/main` there.

Item 17.2 adds `veriformis.advanced-family-admission/v1` as a schema pin.
Four admittable families, two named-not-admitted families, and multimodal
as explicitly unsupported. Unknown families, fields, and contract versions
fail closed and name requested versus supported identity. Loading a pin
does not promote taxonomy or execute a family.

**Next action:** Run the complete item 17.2 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 17.3.

## 2026-08-28: Item 17.2 local gates green

**Status:** The admission contract is a schema pin only. Focused family tests
passed 34. Project tracking, Ruff, the lock check, and `git diff --check`
passed. The core suite passed 2,394 tests with 17 deselected and the one
expected durability warning.

**Next action:** Publish the item 17.2 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 17.3.

## 2026-08-28: Item 17.2 merged; item 17.3 in progress

**Status:** Item 17.2 merged as PR #151 at
`c91948521a086c5691290dd20eb92f906ebc2181`. Clean local `main` equals
`origin/main` there.

Item 17.3 adds named leakage grouping keys as a substrate. Default SFT split
stays `transitive-leakage-prefix-v1`. Extra keys join records only when
supplied as exact values. Missing or empty values fail closed. No family
is executed.

**Next action:** Run the complete item 17.3 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 17.4.

## 2026-08-28: Item 17.3 local gates green

**Status:** Leakage grouping keys are a substrate only. Focused family and
split tests passed. Project tracking, Ruff, the lock check, and
`git diff --check` passed. The core suite passed 2,403 tests with 17
deselected and the one expected durability warning.

**Next action:** Publish the item 17.3 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 17.4.

## 2026-08-28: Item 17.3 merged; item 17.4 in progress

**Status:** Item 17.3 merged as PR #152 at
`db75e5ba3b8cdc39ae7c03bdcea39fe50054fe28`. Item 17.4 adds opt-in family
review queues and preview-only quality hooks. Default recipes stay `none`.
No family is executed.

**Next action:** Run item 17.4 local gates, publish the pull request, merge
green, and synchronize clean `main` before item 17.5.

## 2026-08-28: Item 17.4 local gates green

**Status:** Opt-in family review queues and preview-only quality hooks
are substrate only. Default `review_policy` stays `none`. No family
execute. Focused review, quality, and isolation tests passed 60.
Project tracking, Ruff, the lock check, and `git diff --check` passed.
The core suite passed 2,407 tests with 17 deselected and the one
expected durability warning.

**Next action:** Publish the item 17.4 pull request, require every
GitHub check, merge, and synchronize clean `main` before item 17.5.

## 2026-08-28: Item 17.4 merged; item 17.5 in progress

**Status:** Item 17.4 merged as PR #153 at
`07bb0d0fc7ca427db297bf55d1c5ed9d26627c95`. Item 17.5 admits
`explicit-label-classification` from user-provided labels on the
dataset-row path. Existing trainer profiles refuse the new schema.

**Next action:** Run item 17.5 local gates, publish the pull request,
merge green, and synchronize clean `main` before item 17.6.

## 2026-08-28: Item 17.5 local gates green

**Status:** `explicit-label-classification` compiles from user-provided
labels through map, curate, split, format, validate, seal, and verify.
Document-source construction cannot invent labels. Constrained CSV and
existing trainer profiles refuse the schema. Focused classification
tests passed 9. Project tracking, Ruff, the lock check, and
`git diff --check` passed. The core suite passed 2,416 tests with 17
deselected and the one expected durability warning.

**Next action:** Publish the item 17.5 pull request, require every
GitHub check, merge, and synchronize clean `main` before item 17.6.

## 2026-08-28: Item 17.5 merged; item 17.6 in progress

**Status:** Item 17.5 merged as PR #154 at
`301d1a6c4477480a12bfcba66a9246f5a4607f61`. Clean local `main` equals
`origin/main` there.

Item 17.6 admits `preference-and-ranking` from user-provided
chosen/rejected pairs. Unpaired feedback and ranking-order schemas are
skipped because the pair leakage and evidence contract does not cover
them. Existing trainer profiles refuse the new schema.

**Next action:** Run item 17.6 local gates, publish the pull request,
merge green, and synchronize clean `main` before item 17.7.

## 2026-08-28: Item 17.6 local gates green

**Status:** `preference-and-ranking` compiles from user-provided
chosen/rejected pairs through map, curate, split, format, validate,
seal, and verify. Shared-prompt leakage keeps one prompt in one
partition. Document-source construction cannot invent pairs.
Constrained CSV and existing trainer profiles refuse the schema.
Unpaired feedback and ranking-order schemas are skipped with a record.
Focused preference tests passed 11. Project tracking, Ruff, the lock
check, and `git diff --check` passed. The core suite passed 2,427 tests
with 17 deselected and the one expected durability warning.

**Next action:** Publish the item 17.6 pull request, require every
GitHub check, merge, and synchronize clean `main` before item 17.7.

## 2026-08-28: Item 17.6 merged; item 17.7 in progress

**Status:** Item 17.6 merged as PR #155 at
`4496d0ebc851af20b2a94316a7520b9d3f20b096`. Clean local `main` equals
`origin/main` there.

Item 17.7 admits `tool-call-conversations` from user-provided tool
traces. Two-turn `messages` stays exactly two turns. Synthetic JSONL is
the retained fixture.

**Next action:** Run item 17.7 local gates, publish the pull request,
merge green, and synchronize clean `main` before item 17.8.

## 2026-08-28: Item 17.7 local gates green

**Status:** `tool-call-conversations` compiles from user-provided tool
traces through map, curate, split, format, validate, seal, and verify.
Conversation leakage keeps one thread in one partition. Document-source
construction cannot invent traces. Constrained CSV and existing trainer
profiles refuse the schema. Two-turn `messages` stays exactly two
turns. Focused tool-call tests passed 10. Project tracking, Ruff, the
lock check, and `git diff --check` passed. The core suite passed 2,437
tests with 17 deselected and the one expected durability warning.

**Next action:** Publish the item 17.7 pull request, require every
GitHub check, merge, and synchronize clean `main` before item 17.8.

## 2026-08-28: Item 17.7 merged; item 17.8 in progress

**Status:** Item 17.7 merged as PR #156 at
`132fd478bdd9f65518450a5ce3c8a93da5a6dad0`. Clean local `main` equals
`origin/main` there.

Item 17.8 admits `stepwise-supervision` from user-provided ordered
steps. Copied source text is never labeled reasoning. Synthetic JSONL
is the retained fixture.

**Next action:** Run item 17.8 local gates, publish the pull request,
merge green, and synchronize clean `main` before item 17.9.

## 2026-08-28: Item 17.8 local gates green

**Status:** `stepwise-supervision` compiles from user-provided ordered
steps through map, curate, split, format, validate, seal, and verify.
Shared-prompt leakage keeps one prompt in one partition.
Document-source construction cannot invent steps. Constrained CSV and
existing trainer profiles refuse the schema. Copied source text is
never labeled reasoning. Focused stepwise tests passed 10. Project
tracking, Ruff, the lock check, and `git diff --check` passed. The core
suite passed 2,447 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 17.8 pull request, require every
GitHub check, merge, and synchronize clean `main` before item 17.9.

## 2026-08-28: Item 17.8 merged; item 17.9 in progress

**Status:** Item 17.8 merged as PR #157 at
`d4070236512dbf4f1827de1500360bb2d41c535b` after all 18 GitHub checks
passed. Clean local `main` equaled `origin/main` there before 17.9
began.

Item 17.9 publishes ADR-0018 covering offline default, model identity,
supplied evidence, output identity, required review, isolation from
deterministic v1 claims, and dataset-project code execution. Decision A:
no compile-path generator in Phase 17. This PR adds no `GeneratorPass`.

**Next action:** Run the complete item 17.9 local gates, publish the
pull request, require every GitHub check, merge, and synchronize clean
`main` before item 17.10.

## 2026-08-28: Item 17.9 local gates green

**Status:** ADR-0018 records Decision A. Focused tests passed 39.
Project tracking, Ruff, the lock check, and `git diff --check` passed.
The core suite passed 2,452 tests with 17 deselected and the one
expected durability warning. No `GeneratorPass` was added.

**Next action:** Publish the item 17.9 pull request, require every
GitHub check, merge, and synchronize clean `main` before item 17.10.

## 2026-08-28: Item 17.9 merged; item 17.10 in progress

**Status:** Item 17.9 merged as PR #158 at
`dcd9a541add1c8fa81eb680e6aceb3671ebad509` after all 18 GitHub checks
passed. Clean local `main` equaled `origin/main` there before 17.10
began.

Item 17.10 adds adversarial family refusals, reproves SFT and Phase 16
kit goldens, skips generation, multimodal, pre-tokenized, and unmapped
profiles with records, and closes Phase 17. Do not start Phase 18 from
this packet.

**Next action:** Run the complete item 17.10 local gates, publish the
pull request, require every GitHub check, merge, and synchronize clean
`main`.

## 2026-08-28: Item 17.10 local gates green

**Status:** Adversarial family refusals pass. SFT and Phase 16 kit
goldens hold. Generation, multimodal, pre-tokenized, and unmapped
profiles are skipped with records. Focused tests passed 11. Project
tracking, Ruff, the lock check, and `git diff --check` passed. The core
suite passed 2,463 tests with 17 deselected and the one expected
durability warning. Phase 17 is marked completed.

**Next action:** Publish the item 17.10 pull request, require every
GitHub check, merge, and synchronize clean `main`. Do not start Phase
18 from this packet.
