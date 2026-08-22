# Phase 5 — Lossless Generic Local Exports

**Status:** Completed

**Started:** 2026-08-21

**Completed:** 2026-08-22

**Roadmap phase:** [Phase 5](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-5--ship-lossless-generic-local-exports)

**Predecessor:** [Phase 4 closeout](../phase-04-verified-export-foundation/closeout.md)

## Purpose

Ship trainer-neutral, lossless local derivatives of a verified canonical
`minimal-v1` bundle through the existing `ExportService`. Generic exports
preserve the exact semantic rows and logical partitions selected by the source
bundle; they do not create a second construction, curation, balancing, or
splitting pipeline.

## Phase boundary

Phase 5 owns generic split JSONL, canonical JSON, structurally lossless CSV,
generic export-pack archiving, semantic round-trip proof, exact dry-run
previews, and operator guidance. Item 5.1 owns only the split JSONL container.
Specific trainer compatibility and consumer profiles remain later work.

Every semantic export implementation must enter through the Phase 4 verified
export service and its plan, receipt, publication, and verification boundaries.
Post-export transport must consume that unchanged receipt-bound result through
the existing package boundary. Packet opening alone was not support evidence.
The separately admitted Phase 5.1 and 5.2 implementations support split JSONL
and canonical JSON respectively. Item 5.3's constrained CSV for the three flat
row schemas merged as PR #55. Item 5.4's receipt-anchored post-export transport
merged as PR #56 at `499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`.
Item 5.5's discovery-closed semantic round-trip fixture merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1`. It is test proof, not a
production importer or replayer. Item 5.6's bounded runtime preview merged as
PR #58 at `cd017941090c7352cb1d10f9a383042b954d4f2e`. Item 5.7 completes the
static operator guidance and closeout reconciliation locally; the item 5.7
pull request, GitHub checks, merge, and post-merge synchronization are not
claimed by this packet.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Seven-item execution sequence and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope decisions |
| [risks.md](risks.md) | Final risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |

## Current state

Phase 5 opened on 2026-08-21 from baseline
`a76e0fe3185b0e317cd453b9c28a1d2054e617dd`. Item 5.1 merged as PR #53 at
`4f12a55063c2721993b65cfbe30e68eaad55f87f`. Item 5.2's `json` v1 merged as
PR #54 at `f6a5d45f01e0b3117c259271bc59f3599a89dbb6`. Item 5.3's
`constrained-csv` v1 merged as PR #55 at `c6d7fc13a09a` with fixed
`data/train.csv` and `data/evaluation.csv`, a
dataset card, mandatory aligned provenance, README, and the shared receipt.
Every field is quoted with the frozen UTF-8/LF dialect. It admits `text`,
`prompt_completion`, and `instruction_output`, refuses `messages` with an
actionable JSON alternative, has no options, consumer, or trainer claim, and
changes no source row or logical partition.

Item 5.4 merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`. Its
`deterministic-export-pack-zip-v1` profile wraps one unchanged,
already-published export directory as `.vfexport.zip` under a separately
retained canonical `export-receipt.json` SHA-256. It reuses the existing
deterministic archive codec and `package` / `package-verify` family. It adds no
fourth renderer, request version, trainer or consumer profile, source-bound
archive verification, or Mac UI action. Local gates passed with 66 dedicated
tests, 448 integrated export/taxonomy/CLI tests, 1,195 full Python tests, 1,183
standalone release tests with one deselection and both golden flows, parity,
Mac 58-test, tracking, Ruff, JSON, diff, and corrected independent-review
evidence. See the
[deterministic archive contract](../../../../docs/contracts/bundle-transport-v1.md)
and [ADR-0006](../../../../docs/adr/0006-receipt-anchored-export-pack-transport.md).

Item 5.5 merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1`. Its frozen fixture closes over
the current catalog and current row
schemas: 11 compatible pairs strictly reload ordered, separate train and
evaluation payloads plus aligned provenance to the exact source `RowSet`, while
constrained CSV with `messages` refuses before publication and names both JSON
alternatives. One canonical semantic tamper per container fails strict reload.
Focused 16, integrated 453, full 1,211, standalone release 1,199 with one
deselection, parity, and 58 Mac tests passed. The fixture adds no public import
operation, production replayer, schema, taxonomy, or support change.

Item 5.6 started from that synchronized merge. `export dry-run` now returns the
unchanged plan plus one runtime-only `veriformis.export-dry-run-preview/v1`
object in response v2. The preview shows the first row of each non-empty
train/evaluation partition and a normalized, plan-derived destination tree that
includes `export-receipt.json`. Exact payloads larger than 64 KiB, or unable to
fit the bounded response, are omitted whole with an explicit reason; values are
never truncated or rewritten. This work adds no renderer, destination access,
persisted schema, selector, taxonomy entry, support promotion, or trainer claim.
Local admission passed with 60 focused, 480 integrated, 1,238 full Python, and
1,226 standalone release tests with one deselection; the intentional
durability-warning regression was the only warning. Clean-wheel and both
golden flows, parity, 66 Mac tests, tracking, lock, Ruff, structured JSON,
diff, and independent reviews also passed. Item 5.6 then passed its required
GitHub checks, merged as PR #58 at
`cd017941090c7352cb1d10f9a383042b954d4f2e`, and left clean synchronized
`main` before item 5.7 began.

Item 5.7 publishes the
[Generic Export Operator Guide](../../../../docs/generic-exports.md). It
explains when to choose line-oriented split JSONL, one self-describing canonical
JSON object, or constrained flat-schema CSV. It keeps that physical-container
choice separate from the already-fixed training objective, semantic row schema,
and any separately admitted consumer profile. The three generic exports remain
consumer-neutral and do not imply trainer compatibility. The static guidance,
capability/support review, and Phase 5 packet reconciliation are complete
locally. This local completion statement does not claim publication, GitHub
checks, merge, or clean-main synchronization for the item 5.7 pull request.
