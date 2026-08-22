# Phase 6 Evidence

**Status:** Open — item 6.1 merged as PR #60; item 6.2 locally admitted
without claiming its own pull-request result

**Opened:** 2026-08-22

## Predecessor evidence

Phase 5 completed and its closeout merged as PR #59 at
`65cbd471e96d83f8dd65e2cda60e90f64a916e2b` after all 14 GitHub checks passed.
Its [closeout](../phase-05-generic-local-exports/closeout.md) records the three
generic exports, export-pack transport, round-trip matrix, dry-run preview, and
operator guide. Phase 6 reuses the taxonomy, construction, finished-dataset,
and export contracts; it does not restate Phase 5 evidence as proof of any
goal-first capability.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| Phase 6 depends on Phase 4 only; Phases 5 and 6 may run in parallel after Phase 4 | `source-verified` | `program.json` phase 6 `depends_on`; roadmap ordering rule 9.2 |
| Clean local `main` equals `origin/main` at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b`; full admission suite passes there (1,238 Python tests, Ruff, tracking, lock, diff) | `recorded-local` | 2026-08-22 opening run |
| Five named recipes map one-to-one to the five objective kinds; `PipelineService.construct` does not call `build_named_recipe` | `source-verified` | `src/veriformis/recipes/library.py`; `src/veriformis/pipeline/service.py` |
| Recipe defaults are literal in CLI, MCP, service, runner, library, constructors, and Swift | `source-verified` | Readiness review 2026-08-22 |
| No persisted field records the supervised region; `ROW_LOSS_POLICY` derives it from row schema | `source-verified` | `src/veriformis/taxonomy.py`; `src/veriformis/datasets/serialization.py` |
| Taxonomy v1 had six axes and no input-family axis at opening; superseded by item 6.2's seventh axis under ADR-0008 | `source-verified` | `docs/contracts/taxonomy-v1.md`; `src/veriformis/taxonomy.py` |
| Three objectives and two row schemas have no end-to-end seal test | `source-verified` | Readiness review 2026-08-22 over `tests/` |
| `instruction_text` is validated only for non-emptiness | `source-verified` | `src/veriformis/datasets/serialization.py`; `src/veriformis/pipeline/service.py` |

## Required item 6.1 evidence

- [x] Strict catalog model and packaged data tests: load, closure over the
      five objectives and four row schemas, recipe library binding, default
      representation membership, plain-language fields free of identifiers,
      and fail-closed rejection of malformed, tampered, duplicated, aliased,
      unknown, and missing entries.
- [x] Byte-identical canonical discovery across Python, CLI, and MCP, frozen
      as a shared fixture decoded by Swift with strict key-set validation.
- [x] Support registry and tracking checker bound to the catalog.
- [x] Contract, ADR, CLI, architecture, status, and program records updated.
- [x] Post-#59 reconciliation complete with PR #59 cited in every active
      record that previously disclaimed it.
- [x] Required focused, full, release, tracking, lint, parity, Mac, structured
      JSON, and diff gates recorded with exact observed results.

## Required phase exit evidence

- [ ] Every goal is selectable from plain language on every surface (U1).
- [ ] The preview shows the exact supervised region for every goal and
      representation, proved equal to the serialized target (U2).
- [ ] Identical recipe identifiers and outputs across surfaces for every
      acceptance cell (U3).
- [ ] Non-claims visible everywhere a goal is shown (U4).
- [ ] Preflight refuses incompatible selections before cost (U5).
- [ ] Scripted non-developer walkthrough executed and recorded (U6).

## Observed results

### Item 6.1 (2026-08-22, working tree on
`65cbd471e96d83f8dd65e2cda60e90f64a916e2b`)

| Gate | Observed |
| --- | --- |
| Focused goal tests (`tests/goals`) | 37 passed |
| Full Python (`uv run pytest -q`) | 1,275 passed, 1 intentional durability warning |
| Standalone release (`--ignore=tests/handoff -m "not aptus_integration"`) | 1,263 passed, 1 deselected |
| `scripts/release/check_local.sh` | PASS (clean wheel, golden compile, external digest, transport) |
| `macos/scripts/parity_check.sh` | PASS |
| macOS XCTest target | 72 passed, `TEST SUCCEEDED` |
| `scripts/check_project_tracking.py` and its regression | PASS (goal binding added) |
| `uv lock --check`, Ruff, structured JSON, fixture `cmp`, `git diff --check` | PASS |
| Independent adversarial review | One plain-language blocker and nine should-fix items found; all corrected and re-verified on this tree |

Item 6.1 subsequently passed all 14 GitHub checks (one timing-sensitive
Phase 5.6 adapter test needed a re-run on a slow runner) and merged as PR #60
at `7316d94faf2d6c23b7abb6fe200f154da47d398c`.

### Item 6.2 (2026-08-22, working tree on
`7316d94faf2d6c23b7abb6fe200f154da47d398c`)

| Gate | Observed |
| --- | --- |
| Focused goal and taxonomy tests (`tests/goals`, `tests/contracts/test_taxonomy_contract.py`) | 83 passed |
| Full Python (`uv run pytest -q`) | 1,308 passed, 1 intentional durability warning |
| Standalone release (`--ignore=tests/handoff -m "not aptus_integration"`) | 1,296 passed, 1 deselected |
| `scripts/release/check_local.sh` | PASS (clean wheel, golden compile, external digest, transport) |
| `macos/scripts/parity_check.sh` | PASS |
| macOS XCTest target | 72 passed, `TEST SUCCEEDED` |
| `scripts/check_project_tracking.py` and its regression | PASS (input-family suffix partition and registry binding added) |
| `uv lock --check`, Ruff, structured JSON, fixture `cmp`, `git diff --check` | PASS |
| Independent adversarial review | One blocker (`source-code` listed for the before/after goal although cleaning never edits code blocks) and six should-fix items (synthetic PDF `Page N` headings, universal `source-chunks-unavailable`, executable `CurationDefaults`, `balance_mode` spelling note, long lines, Mac seventh-axis disclosure); all corrected and re-verified on this tree |

Proofs recorded by tests: every goal's `curation_defaults` equal the
defaults `PipelineService.curate`, CLI `curate`, MCP `curate`, and the
recipe library execute; every representation's `compatible_generic_exports`
equal the production export catalog; for every implemented input family a
parsed sample supplies exactly the evidence each goal claims (cleaning edits
for the before/after goal, a real heading with body for the section goal, a
supported scalar on a non-synthetic node for the structural goal); the
taxonomy suffix partition equals `DECLARED_V1_EXTENSIONS`.

These are local observations. They do not claim publication, GitHub checks,
merge, or clean-main synchronization for the item 6.2 pull request.
