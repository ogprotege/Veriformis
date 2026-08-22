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
