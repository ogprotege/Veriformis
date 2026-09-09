# Post-20 Defect Closure Plan

## Method

One branch, one commit per logical change, one reviewable pull request.
Every code change carries its regression test and its documentation update.
Canonical-stream-changing parser fixes bump the affected parser identity pin
and regenerate frozen fixtures through the documented generator; the fixture
diff is recorded in [progress.md](progress.md). No persisted stage schema
changes. D-07 was withdrawn after direct verification: the existing durable
fingerprint is lossless. Its algorithm and all persisted plans remain unchanged.

## Defect register

Severity: **B** ship-blocking or silent corruption; **C** correctness or
fail-closed gap; **H** claim honesty; **T** test or CI signal; **S**
scalability.

| ID | Sev | Location | Defect |
| --- | --- | --- | --- |
| D-01 | B | `pyproject.toml` package-data | `scale/*.json` not packaged; `scale-support` fails from an installed wheel |
| D-02 | B | `parsers/html.py` | UTF-8 HTML without `<meta charset>` decoded as Latin-1 with no diagnostic |
| D-03 | B | `parsers/structured.py`, `mapping/capture.py` | JSONL framed with `str.splitlines()`; U+2028/U+2029/U+0085 split records |
| D-04 | B | `macos/.../WorkbenchViewModel.swift` | Confirmed mapping plan written inside the CLI workspace before `parse`; dataset-row compile refuses |
| D-05 | B | `handoff/aptus_v1.py` | `consume` trusts descriptor-declared capabilities; masking and provenance identities unchecked |
| D-06 | B | `pipeline/service.py` `_seal_imported` | No partial-publication recovery, no `SealPartialPublicationError`, no durability warning |
| D-07 | B | `datasets/curation.py`, `bundle/verifier.py` | Withdrawn: exact fingerprint uses lossless JSON; NFC/NFD remain distinct |
| D-08 | C | `pipeline/service.py` `map_rows` | Rejection report written non-atomically after commit |
| D-09 | C | `cli.py`, `parsers/pdf.py`, `parsers/structured.py` | Funnel gaps and untyped parser exceptions |
| D-10 | C | `parsers/docx.py`, `diagnostics.py` | Default lxml parser for notes; no inflate cap; text-box text dropped or mislabeled |
| D-11 | C | `parsers/pdf.py` | Synthetic `Page N` headings undiagnosed; `Span.page` unset |
| D-12 | C | `parsers/html.py` | `<br>`/nested blocks glue words; tables, lists, `<pre>` flattened undiagnosed |
| D-13 | C | `parsers/structured.py` | JSON NaN/duplicate keys accepted; lossy floats; whitespace collapsed; CSV BOM kept |
| D-14 | C | `ocr/tesseract.py`, `ocr/thresholds.py` | Confidence never populated; thresholds dead |
| D-15 | C | `exports/*.py` renderers | Exact-byte renderers report source rows as candidates; membership check tautological |
| D-16 | C | `_archive_transport.py` | ZIP64 central-directory extra rejected; contract claims ZIP64 |
| D-17 | C | `pipeline/service.py`, `mapping/models.py` | Required review unresolvable on CLI/MCP; import `review_policy` unenforced |
| D-18 | C | `pipeline/service.py`, `goals/preflight.py` | `construct --goal` skips segmentation check preflight performs |
| D-19 | C | `automation/execute.py`, `automation/inspect.py` | Resume ignores env pins; pipeline content outside digest; stage goal override |
| D-20 | C | `mapping/finish.py`, `datasets/validation.py` | Import gates decorative; pass-through document gates |
| D-21 | C | `scale/baseline.py` | `cancel_observed`/`resume_observed` asserted, not observed |
| D-22 | C | `collection/plan.py` | Limits after hashing; duplicate owner depends on argv order |
| D-23 | C | `macos/` | Drop race; quit coordinator; PID-only kill; log-scraped digests; closed enums; unversioned history |
| D-24 | H | contracts, `current-status.md` | Phase 17 goals, presets, and row schemas never propagated |
| D-25 | H | `docs/cli.md`, `install.md`, `README.md` | Commands documented nowhere; `map` example fails |
| D-26 | H | architecture, governance, install docs | Stale replayer, extras, `ocr-image`, counts, CI claims |
| D-27 | T | `tests/handoff/test_defectclose_handoff.py` | Collected by no CI job |
| D-28 | T | `.github/workflows/ci.yml` | `profile-integration` installs nothing it tests |
| D-29 | T | `scripts/release/golden_compile.sh` | Self-referential digest; empty evaluation tolerated |
| D-30 | T | `tests/` | Missing negative tests for named fail-closed paths |
| D-31 | T | `tests/`, `ci.yml` | Duplicated helpers, cross-module imports, deprecated asyncio, unpinned actions |
| D-32 | S | `workspace.py`, `pipeline/service.py` | History re-verified and sources re-parsed per command |
| D-33 | S | `exports/service.py` | Source re-verified and rendered repeatedly; whole trees retained |
| D-34 | S | `quality/near_duplicates.py` | All-pairs O(n²) |
| D-35 | S | `workspace.py`, `contracts.py` | 1,214-line stage validator with duplicated tables |

## Phases and exit gates

Phases are sequenced 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. Each phase ends with the
full check set:

```bash
uv lock --check
uv run ruff check src tests
uv run python scripts/check_project_tracking.py
uv run pytest -q --ignore=tests/handoff -m "not aptus_integration and not profile_integration and not columnar_integration and not scale_benchmark"
git diff --check
```

Phase-specific gates:

1. New regression per closed defect; `AGENTS.md` suite timing corrected.
2. Tracking checker gains package-data, contract-vs-discovery, and count
   assertions; every audited-accurate document untouched.
3. Affected parser pins bumped; frozen fixtures regenerated through the
   documented generator; `docs/migration.md` entry; fixture diff recorded.
4. Phase 5.5 round-trip matrix and the 74-cell matrix green with regenerated
   pins; adversarial closeout suite green; pre-change bundles still verify.
5. Required review resolvable through Python, CLI, and MCP; preflight and
   construct agree on segmentation; resume refuses env-pin drift.
6. Matrix tests carry a `matrix` marker with their own job; named negative
   tests exist; golden compile compares a committed digest.
7. One `verify_history` per command; loaders read each artifact once.
8. Unsigned Debug `xcodebuild` job green; no public Mac claim.
