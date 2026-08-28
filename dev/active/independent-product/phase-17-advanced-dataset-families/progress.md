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
