# Phase 5 Progress Log

This file is append-only by dated entry. Corrections are recorded in later
entries rather than deleting earlier history.

## 2026-08-21 — Phase 5 started

**Status:** In progress

**Predecessor:** Phase 4 completed and merged as PR #52 at
`a76e0fe3185b0e317cd453b9c28a1d2054e617dd`. The Phase 5.1 branch was created
from clean local `main` equal to the local `origin/main` reference at that
commit.

**Starting facts reviewed:**

- Phase 4 supplies strict verified-source admission, planning, deterministic
  evidence boundaries, atomic publication, receipts, verification, and
  cross-surface operations.
- At the opening baseline, the production implementation catalog and
  discovery result are empty; generic container support remains planned.
- Split JSONL is the first Phase 5 candidate and is intended to preserve every
  current semantic row schema and logical partition.
- Canonical partition JSONL already exists inside the source bundle, but a
  generic derivative requires its own profile, safe output bindings,
  dependencies, receipt, and independent verification.
- Configurable partition filenames must not rename or alter logical partition
  identities.
- Generic export-pack archiving will reuse the existing deterministic
  transport in item 5.4; it is not part of item 5.1.

**Next action:** Complete item 5.1 by freezing the split JSONL profile and
configuration, implementing it through the verified export service, and
recording focused, adversarial, round-trip, cross-surface, and required
repository evidence before any support promotion.

## 2026-08-21 — Item 5.1 locally complete

**Status:** Local implementation and admission gates passed; pull-request
merge pending.

The production catalog now contains exactly `split-jsonl-directory` v1 with no
consumer profile, all four current row schemas, and a
`portable_exact_bytes` claim. Request v1 retains the safe `train` /
`evaluation` layout and includes aligned provenance. Additive request v2
requires the complete canonical `veriformis.split-jsonl-options/v1` object and
may change only safe partition filename stems or omit provenance. Discovery,
response, the ten persisted export models, the source bundle, and workspace
contracts remain unchanged.

The container emits payload-only canonical partition JSONL, deterministic
README and data card, optional exact train-then-evaluation provenance, and the
shared receipt. Exact round trips covered `text`, `prompt_completion`,
`instruction_output`, and nested `messages`; publication and source-bound
verification rejected every file tamper and changed option plan. Python, CLI,
MCP, and Mac request/plan parity passed without a trainer compatibility claim.

Observed gates on the reconciled working tree:

- 45 dedicated split JSONL tests passed; 288 combined
  export/taxonomy/verified-contract tests passed.
- Full Python passed 1,039 tests with only the expected exercised transport
  durability-warning regression warning.
- The standalone release gate passed 1,027 core tests with 1 deselected and
  the same expected warning, then passed lock, clean-wheel installation, both
  golden compile/external-digest/transport flows, and installed-CLI smoke.
- The complete macOS target passed 56 tests; standalone workbench/CLI parity
  passed.
- Project tracking, Ruff, lock integrity, 15 tracked JSON files, 10 tracked
  shell files, 387 changed-document local links, and `git diff --check` passed.

**Next action:** Resolve any independent final-review finding, publish the
Phase 5.1 pull request, require its GitHub checks to pass, merge it, and
synchronize clean local `main` before beginning item 5.2.

## 2026-08-22 — Item 5.2 canonical JSON implemented

**Status:** Local implementation, admission, and repository gates passed;
independent code, security, and documentation reviews found no blocker;
pull-request publication and merge remain.

Phase 5.1 merged as PR #53 at
`4f12a55063c2721993b65cfbe30e68eaad55f87f`, and the item 5.2 branch began from
clean local `main` equal to `origin/main` at that commit. Production discovery
adds `json` v1 with no consumer profile, all four current row schemas, and a
`portable_exact_bytes` claim.

The fixed closed tree contains deterministic `README.md`, one canonical
`dataset.json`, mandatory aligned `metadata/row-provenance.json`, and the
shared receipt. The dataset object carries explicit schema, objective, loss,
row-set, split-result, partition-order, count, and trainer-non-claim metadata;
its train and evaluation arrays contain payload objects only. The provenance
object carries the complete train-then-evaluation Finished Dataset v1 sequence.
`dataset.json` alone bears complete membership scope.

Canonical JSON has no container options: historical request v1 selects it,
while configured request v2 fails before source or destination access. The ten
persisted verified-export v1 models, discovery v1, response v1, source bundle,
logical membership, and trainer-neutral boundary remain unchanged.

**Observed gates:** The dedicated canonical-JSON suite passed 33 tests; the
focused export/taxonomy/verified-contract gate passed 322 tests; and full
Python passed 1,073 tests with only the expected transport durability-warning
regression warning. Standalone release passed 1,061 tests with 1 deselected and
the expected warning, then passed lock, Ruff, clean-wheel installation, and
both golden compile/external-digest/transport flows. CLI/workbench parity
passed, the full Mac target passed 57 tests with `TEST SUCCEEDED`, and tracking,
JSON validity, and diff checks passed. Final code review found no blocker.

**Next action:** Publish item 5.2, require every GitHub check to pass, merge,
and synchronize clean local `main` before item 5.3.

## 2026-08-22 — Item 5.3 constrained CSV implemented

**Status:** Local implementation and admission reconciliation complete;
pull-request publication and merge remain.

Item 5.2 merged as PR #54 at
`f6a5d45f01e0b3117c259271bc59f3599a89dbb6`, and item 5.3 began from that
synchronized baseline. Production discovery adds consumer-neutral
`constrained-csv` v1 with `portable_exact_bytes` determinism for `text`,
`prompt_completion`, and `instruction_output`. Nested `messages` is not a CSV
schema: after source admission reveals it, selection fails before destination
access and directs the operator to split JSONL or canonical JSON.

The fixed closed tree contains fully quoted UTF-8/LF `data/train.csv` and
`data/evaluation.csv`, deterministic `README.md`,
`metadata/dataset-card.json`, mandatory train-then-evaluation
`metadata/row-provenance.jsonl`, and the shared receipt. Ordered headers are
frozen by row schema; embedded line endings and exact Unicode field content
are preserved inside quotes. Strict reload re-renders exact bytes and rejects
empty values, non-string values, count/schema/alignment drift, mutation,
missing files, and unexpected files.

Historical request v1 selects this fixed tree. Request v2 and container
options are refused before source or destination access. The verified-export
persisted models, source bundle, rows, ordering, and logical partition
membership remain unchanged. Local admission covers the dedicated container
contract, shared export/taxonomy contracts, cross-surface request-v1 parity,
tamper/refusal behavior, tracking, and documentation reconciliation. The
dedicated suite passed 47 tests; the integrated export/taxonomy/verified-
contract gate passed 371; full Python passed 1,121 with only the expected
transport warning; the standalone release gate passed 1,109 with one
deselection plus the clean wheel and both golden flows; parity passed; and the
complete Mac target passed 58 tests with `TEST SUCCEEDED`. Independent review
found no executable blocker; its two promotion-evidence blockers were
corrected before publication.

**Next action:** Publish item 5.3, require every GitHub check to pass, merge,
and synchronize clean local `main` before item 5.4.

## 2026-08-22 — Item 5.3 merged; item 5.4 started

**Status:** Item 5.3 merged as PR #55 at `c6d7fc13a09a`. Item 5.4 local
implementation and admission are in progress; publication and merge remain
pending.

The synchronized item 5.3 baseline retains exactly three production export
renderers: `split-jsonl-directory`, canonical `json`, and `constrained-csv` v1.
Item 5.4 defines `deterministic-export-pack-zip-v1` as an optional post-export
transport with suffix `.vfexport.zip`. Packaging requires the separately
retained SHA-256 of canonical `export-receipt.json` and includes exactly that
receipt plus its complete bound file set under the deterministic stored-ZIP
envelope shared with ADR-0005.

The integration extends the existing `package` / `package-verify` family under
ADR-0006 and the single deterministic archive contract. It does not add an
export selector, request version, persisted export field, trainer or consumer
profile, source-bound archive verification, MCP operation, or Mac UI action.
The embedded source trust grade must remain unchanged, and legacy manifest-
anchored `.vfbundle.zip` behavior must remain byte-compatible.

No item 5.4 test counts or admission results are recorded yet.

**Next action:** Complete the focused transport, adversarial, legacy-
compatibility, tracking, and required repository gates; record exact observed
results; resolve independent review findings; then publish and merge only after
every required check is green.

## 2026-08-22 — Item 5.4 locally admitted

**Status:** Local implementation, evidence, and independent-review
reconciliation complete; pull-request publication, GitHub evidence, and merge
remain pending.

`deterministic-export-pack-zip-v1` is locally admitted as an optional
receipt-anchored post-export transport with suffix `.vfexport.zip`. It admits
only `portable_exact_bytes`, archives exactly canonical
`export-receipt.json` plus the receipt-declared files, requires the separately
retained canonical receipt digest, and preserves the embedded source trust
grade. The ten persisted export v1 models, three renderer selectors, export
request/discovery surfaces, MCP surface, and Mac UI remain unchanged. Legacy
manifest-anchored `.vfbundle.zip` arguments, behavior, and bytes remain
compatible.

The dedicated export-pack suites passed 66 tests. The integrated
export/taxonomy/CLI gate passed 448. Full Python passed 1,195 with one
intentional durability-warning regression warning. The standalone release
gate passed 1,183 with one deselection, plus lock validation, a clean wheel,
and both golden flows. CLI/workbench parity passed. The complete Mac target
passed 58 tests with `TEST SUCCEEDED`. Tracking, Ruff, JSON validity, and diff
checks were green.

Independent contract review found an all-three-container coverage gap and
stale/exact-only records; both were corrected. Independent code review found
bundle-compatibility and archive path-stability blockers; both were corrected
and the re-review was clear. These are local results, not GitHub evidence.

**Next action:** Publish the item 5.4 pull request, require every GitHub check
to pass, merge, and synchronize clean local `main` before item 5.5. Items
5.5–5.7 and Phase 5 closeout remain open.
