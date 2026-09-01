# Phase 20 Progress

Append-only. Corrections add a later entry.

## 2026-08-31: Phase 20 opened; item 20.1 in progress

**Status:** Packet created from clean `main` at
`084e504a799b6c1c1cc130c8ee819b13de5d6bbe`, PR #180 after the Phase 19
closeout. Phase 20 was `planned` with no packet. All declared dependencies
(Phases 0–19) were complete.

Item 20.1 records the current release boundary. Version is `0.1.0`. PyPI
classifier is `Development Status :: 3 - Alpha`. Support-registry maturity
is `development-alpha`. There is no 1.0 support-matrix pin, no version bump,
no signed Mac claim, no Hub execute, and no support-lifecycle document.
Phase 19 closeout still forbids starting Phase 20 from that packet; this
packet is the Phase 20 start.

**Next action:** Run the complete item 20.1 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 20.2.

## 2026-08-31: Item 20.1 local gates green

**Status:** The current release boundary is recorded without adding product
behavior. The focused isolation suite passed 19 tests including Phase 18
and Phase 19 closeout honesty. Project tracking, Ruff, the lock check, and
`git diff --check` passed. The core suite passed 2,642 tests with 17
deselected and the one expected durability warning.

**Next action:** Publish the item 20.1 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 20.2.

## 2026-08-31: Item 20.1 merged; item 20.2 in progress

**Status:** Item 20.1 merged as PR #181 at
`1f6660944fccd3bdcfdfe1ac88270866211bd613`. Clean local `main` equals
`origin/main` there.

Item 20.2 pins `veriformis.support-matrix/v1`. Loading is not a version
bump. The frozen claim is CLI-first independent core. Public signed Mac,
Hub execute, generator, plugin loader, Unsloth execute, default-parse
`ocr-image`, published corpus tiers, quality-report command, hosted
training, and required extras stay excluded.

**Next action:** Run the complete item 20.2 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 20.3.

## 2026-08-31: Item 20.2 local gates green

**Status:** The CLI-first 1.0 support matrix is pinned without a version
bump. Focused tests passed 18. Project tracking, Ruff, the lock check, and
`git diff --check` passed. The core suite passed 2,646 tests with 17
deselected and the one expected durability warning.

**Next action:** Publish the item 20.2 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 20.3.

## 2026-08-31: Item 20.2 merged; item 20.3 in progress

**Status:** Item 20.2 merged as PR #182 at
`aa91d49331ab5fec264593287baf89d3fbb116e1`. Clean local `main` equals
`origin/main` there.

Item 20.3 publishes `docs/migration.md` and proves workspace revisions 1
and 2 upgrade to 3, revision 4 stays, unknown layouts and revisions fail
closed, and mapping/recipe/export/profile v1 documents still load.

**Next action:** Run the complete item 20.3 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 20.4.

## 2026-08-31: Item 20.3 local gates green

**Status:** The operator migration guide is published. Focused tests passed.
Project tracking, Ruff, the lock check, and `git diff --check` passed. The
core suite passed 2,651 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 20.3 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 20.4.
