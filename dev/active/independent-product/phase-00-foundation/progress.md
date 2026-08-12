# Phase 0 Progress Log

This file is append-only by dated entry. Corrections are added as later entries
rather than erasing the earlier record.

## 2026-08-11 — Independent product evidence baseline

**Status:** Complete

**Baseline:** `7d116e9c09fb4c64f38b2db2572f820a83c53dba`

**Work completed:** Reviewed the repository architecture, product contracts,
parsers, objectives, serializers, bundle, Aptus adapter, Mac workbench,
existing plans, tests, and official trainer documentation. Created the
independent product analysis and authoritative Phase 0–20 roadmap.

**Evidence:** Lock and Ruff passed; 658 Python tests passed; CLI/workbench
parity passed; 12 Xcode tests passed; local links and `git diff --check`
passed. These were observed local results; raw runner logs are not committed.

**Decisions:** The verified Veriformis bundle remains consumer-neutral; Aptus
is optional; training goal, semantic row, physical container, and consumer
profile are independent axes.

**Remaining:** Build the continuous tracking machinery and complete Phase 0.

## 2026-08-11 — Phase 0.1 tracking system started

**Status:** In progress

**Work completed:** Defined the machine program ledger, support registry,
evidence index, governance policy, documentation debt register, ADR set,
standard phase packet, and planned regression check.

**Files:** `dev/active/independent-product/`, `docs/governance/`, `docs/adr/`,
`docs/evidence/`, root WIP, and tracking regression files.

**Evidence:** Final automated and repository checks remain open until the
implementation and documentation reconciliation are complete.

**Risks:** The current support registry can validate literal code constants but
cannot automatically judge every semantic claim; human review remains
mandatory. The owner corpus matrix is not yet available and remains a Phase 0
gate.

**Next action:** Implement and run the automated drift checker, mirror phase
state in WIP, then record final results.

## 2026-08-11 — Phase 0.1 tracking system completed

**Status:** Complete

**Work completed:** Added the machine program ledger, code-bound support
registry, evidence grades/index, governance and documentation-debt records,
standard phase packet, four accepted ADRs, granular WIP phase table, automated
drift checker, pytest regression, and contributor/agent/development guidance.

**Verification:** `uv lock --check` passed; Ruff passed; the project tracking
check passed; 659 Python tests passed; CLI/workbench parity passed; 12 Xcode
tests passed; changed/new local documentation links resolved; and
`git diff --check` passed.

**Evidence grade:** Recorded local. The Xcode result bundle is temporary under
`/tmp/veriformis-phase0-dd`; raw console logs are not committed. The commands
and exact summarized results are retained in `evidence.md` and the evidence
index for reproducible rerun.

**Decisions:** ADR-0001 through ADR-0004 accepted. Phase 0 remains
`in_progress`; Phase 1 is not authorized to start until the remaining Phase 0
gate passes.

**Remaining:** Sanitized owner corpus/demand matrix, remaining active-document
reconciliation, and Phase 0 closeout.

**Next action:** Define and populate the privacy-preserving corpus and workflow
demand matrix without storing private source content.

## 2026-08-11 — Phase 0.4 corpus and demand evidence completed

**Status:** Complete

**Work completed:** Added the versioned corpus-demand JSON Schema, a
content-blind filesystem metadata scanner, the governed demand matrix, and a
focused regression suite. The scanner aggregates counts, byte sizes, declared
input suffixes, source families, size buckets, hidden entries, symlinks, and
bundle context without opening files or emitting filenames, paths, content
hashes, timestamps, or undeclared extension names.

**Evidence:** The scanner reproduced the committed aggregate for all 16
tracked files under `tests/fixtures`. A separate local-only observation counted
89 files and two bundle directories under the untracked retained GUI test root;
it is labeled `recorded-local` and is not required by CI. Three focused tests
passed, Ruff passed for the scanner and test, and Draft 2020-12 schema
validation passed locally.

**Decisions:** Generic split JSONL export is provisionally first because the
canonical bundle already binds JSONL partitions and standalone export is an
accepted requirement. Additional containers, new input types, OCR, and every
named consumer profile remain unranked where actual owner-corpus or workflow
frequency evidence is missing. Test-fixture frequency is not treated as
customer demand.

**Limitations:** No privacy-preserving aggregate from a representative owner
source corpus or actual trainer-run inventory has been retained. Consequently,
the matrix records exact evidence-collection gates rather than inventing a
priority among JSON, CSV, Parquet, Arrow, Hugging Face Dataset, or named trainer
profiles.

**Next action:** Reconcile remaining active documentation, then run the Phase 0
closeout gates and update the program-wide state records.

## 2026-08-11 — Phase 0 completed

**Status:** Complete

**Work completed:** Reconciled the active architecture tree around the
implemented `PipelineService` composition root, thin CLI/MCP adapters, and
SwiftUI CLI shell. Corrected obsolete command/dependency counts, historical
contract deferrals, fragile CLI citations, and canonical-destination language.
Separated the trainer-neutral public-release criterion from optional Aptus
integration evidence. Reconciled current status, WIP, support and evidence
records, documentation health/debt, and this phase packet.

**Verification:** Lock resolution passed with 50 packages. Ruff passed across
`src`, `tests`, and `scripts`. The project tracking check passed. The full
Python suite passed with 662 tests. CLI/workbench parity passed with all five
then-current compared digests equal. Xcode ran 12 tests with zero failures.
Active/local Markdown targets and `git diff --check` passed.

**Evidence limits:** Results are dated local observations; raw Python and
parity logs were not retained. Xcode's result bundle is temporary under
`/tmp/veriformis-phase0-closeout-dd-escalated`. The first sandboxed Xcode run
could not reach `testmanagerd`; the authorized rerun outside that sandbox
passed. Representative owner-corpus composition, actual trainer frequency,
required container frequency, and scale targets remain unavailable and are
explicitly unranked.

**Decision:** Phase 0 satisfies its exit gate and is `completed`. Phase 1 may
begin only after its standard packet and acceptance tests are established.
