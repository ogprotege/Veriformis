# Phase 7 Evidence

**Status:** Complete — item 7.10 closeout observed on GitHub

**Opened:** 2026-08-23

## Predecessor evidence

Phase 6 completed. Item 6.7 merged as PR #67 at
`6995d17bef0d09f235b1c464e947c38c63dd313d` after all 14 GitHub checks passed.
The completion stamp merged as PR #69 at
`6c4694c2e1c523156cd7c8f34c12f258a3ce0b01`.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| CSV/JSON/JSONL ingest is document recovery, not row mapping | `source-verified` | `src/veriformis/parsers/structured.py` |
| Support registry listed planned import modes before 7.1 | `source-verified` | `docs/governance/support-registry.json` at Phase 6 closeout |
| Phase 5.5 reloaders are test-only | `source-verified` | Phase 5.5 closeout; `tests/exports/test_semantic_round_trip.py` |
| No `map` workspace stage exists | `source-verified` | `src/veriformis/workspace.py` revision v3 graph |

## Required item 7.1 evidence

- [x] Mode catalog packaged, canonical, and closed over the three identifiers.
- [x] Python, CLI, and MCP emit byte-identical discovery JSON.
- [x] Default compile remains document-source with no new required flag.
- [x] `dataset-row` and `mixed` refuse execution with the named later item.
- [x] Support registry and tracking checker bind implemented/planned modes.
- [x] ADR-0010 published; packet opened; Phase 6 merge cited.

## Required item 7.3 evidence

- [x] UTF-8 JSONL capture refuses invalid lines, empty files, and non-JSONL suffixes.
- [x] Mapping execution binds `mapped_value` evidence and refuses unmapped keys and three-turn messages.
- [x] Workspace revision v4 defines `parse → map → curate → split → format → validate → seal`.
- [x] Document-source v3 workspaces reject `map`; v4 workspaces reject `clean` / `construct`.
- [x] Four JSONL fixtures (`text`, `prompt_completion`, `instruction_output`, `messages`) map and seal.
- [x] Python / CLI / MCP parity on mapping-plan id, imported-record ids, and manifest digest.

## Required item 7.8 evidence

- [x] JSON capture admits a top-level array of objects or one object with a
      `records`/`rows` array; scalar files and non-object records fail closed.
- [x] CSV capture requires a header, comma, UTF-8, no trim/pad; jagged and
      nested rows fail closed; `messages` names `split-jsonl-directory` or `json`.
- [x] Document-source parse of the same JSON bytes remains a different parser
      path from dataset-row capture.
- [x] Round-trip matrix: JSONL × 4 schemas, JSON × 4, CSV × 3 flat, using
      production mapping plus existing generic export, not Phase 5.5 loaders.
- [x] Core pytest: 1951 passed, 1 deselected, expected transport warning.

## Required item 7.9 evidence

- [x] Rejection report `veriformis.mapping-rejection-report/v1` is content-addressed
      and ordered by row index.
- [x] Accepted rows still seal; rejected rows never appear in emitted partitions.
- [x] Tampering the report does not change the sealed bundle digest.
- [x] A corrected source produces a new mapping-plan id.
- [x] Python, CLI, and MCP write the same report identity.

## Required item 7.10 evidence

- [x] Packaged mapping templates cover the unique detector shapes and are
      digest-bound.
- [x] Operator guide `docs/mapping.md` states modes, confirmation, partitions,
      JSON/CSV, and non-claims.
- [x] U1–U7 judged against current-tree mapping tests.
- [x] `gap-existing-dataset-row-mapping` closed. Remaining bounds are later
      phases, not an open Phase 7 gap.
- [x] Phase 7 marked completed. Do not start Phase 8, 9, or 13.
- [x] Core pytest: 1956 passed, 1 deselected, expected transport warning.
- [x] After the Actions spending limit was increased, PR #80 passed all 14
      GitHub checks and `main` `ci` run 32617948069 succeeded on
      `b7bb7f0c2046fba87fd7c9da12f7d2ccb5c2c88f`.
