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

## 2026-09-01: Item 20.3 merged; item 20.4 in progress

**Status:** Item 20.3 merged as PR #183 at
`0d9919af31d1dfdd7e13baafacf4420cac9b9f55`. Clean local `main` equals
`origin/main` there.

Item 20.4 records `docs/security.md`. First-party license stays MIT.
Unknown suffixes fail closed. OOXML XML disables entities and network.
Compile path has no network client. No required pip-audit CI job.

**Next action:** Run the complete item 20.4 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 20.5.

## 2026-09-01: Item 20.4 local gates green

**Status:** The security review is recorded. Focused tests passed. Project
tracking, Ruff, the lock check, and `git diff --check` passed. The core
suite passed 2,658 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 20.4 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 20.5.

## 2026-09-01: Item 20.4 merged; item 20.5 in progress

**Status:** Item 20.4 merged as PR #184 at
`484b6ff69682a64e4deb5b14d5bfd380236061c3`. Clean local `main` equals
`origin/main` there.

Item 20.5 retains isolated-wheel golden compile evidence under
`evidence/clean-machine-cli/`. Version `0.1.0`. No Aptus distribution.
`full_text` and `continuation` verify at `external_digest`.

**Next action:** Run the complete item 20.5 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 20.6.

## 2026-09-01: Item 20.5 local gates green

**Status:** Isolated-wheel golden compile evidence is retained. Focused
tests passed. Project tracking, Ruff, the lock check, and `git diff --check`
passed. The core suite passed 2,659 tests with 17 deselected and the one
expected durability warning.

**Next action:** Publish the item 20.5 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 20.6.

## 2026-09-01: Item 20.5 merged; item 20.6 in progress

**Status:** Item 20.5 merged as PR #185 at
`f47afdf35d2520d8a76bd0a2de91303dec6150e3`. Clean local `main` equals
`origin/main` there.

Item 20.6 skips signed, notarized, and stapled Mac with a record. GitHub
has no xcodebuild job. `public_signed_mac` stays false.

**Next action:** Run the complete item 20.6 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 20.7.

## 2026-09-01: Item 20.6 local gates green

**Status:** Signed Mac is skipped with a record. Focused tests passed.
Project tracking, Ruff, the lock check, and `git diff --check` passed.
The core suite passed 2,660 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 20.6 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 20.7.

## 2026-09-01: Item 20.6 merged; item 20.7 in progress

**Status:** Item 20.6 merged as PR #186 at
`94978a0ded5125e1c12f8e74aa1445572267eba7`. Clean local `main` equals
`origin/main` there.

Item 20.7 inspects sdist and wheel listings. Version `0.1.0`. Binaries
are not retained.

**Next action:** Run the complete item 20.7 local gates, publish the pull
request, require every GitHub check, merge, and synchronize clean `main`
before item 20.8.

## 2026-09-01: Item 20.7 local gates green

**Status:** Sdist and wheel listings are retained. Focused tests passed.
Project tracking, Ruff, the lock check, and `git diff --check` passed.
The core suite passed 2,661 tests with 17 deselected and the one expected
durability warning.

**Next action:** Publish the item 20.7 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 20.8.
