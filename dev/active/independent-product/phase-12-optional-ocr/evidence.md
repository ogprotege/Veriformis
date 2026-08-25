# Phase 12 Evidence

**Status:** Open — item 12.1

**Opened:** 2026-08-25

## Predecessor evidence

Phase 11 completed. Items 11.1–11.8 merged as PR #104 at
`e856af96043c9876affa275b5246e83541254d9d`.

Operator compile of Pius X *Pascendi Dominici Gregis* at
`/Users/biscuit/Documents/Veriformis` (`2026-08-24T13-54-52Z`): `full_text`
/`text`, 31 train / 0 evaluation, manifest
`94b63232166aeedc9db797fdc0ec0167b2135d8c01bd3934635250a0a2245ace`. Seal
`self_consistent`; zip `external_digest`. Recorded in
[operator-compile-2026-08-24-pascendi.md](../operator-compile-2026-08-24-pascendi.md).

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| `ocr-image` is explicitly unsupported | `source-verified` | `src/veriformis/taxonomy.py` |
| Empty-text PDF refuses with `pdf.ocr-required` and `ocr-unsupported` | `source-verified` | `src/veriformis/parsers/pdf.py` |
| Digitally born PDF extracts the text layer via pypdfium2 | `source-verified` | `src/veriformis/parsers/pdf.py` |
| There is no `ocr` extra | `source-verified` | `pyproject.toml` |
| Collection ingest does not change suffix dispatch | `source-verified` | Phase 11 closeout; ADR-0015 |

## Required item 12.1 evidence

- [x] Packet opened; Phase 12 `in_progress`; Phase 11 merge cited.
- [x] `ocr-image` remains explicitly unsupported and is absent from
      implemented discovery.
- [x] Empty-text PDF still refuses; digitally born PDF still extracts text.
- [x] No `ocr` extra; lock extras list unchanged; OCR engine packages absent
      from the lock.
- [x] Core parse does not import OCR libraries.
- [x] Focused isolation tests, tracking, Ruff, lock, and diff check.

## Local gates (2026-08-25)

- `uv lock --check`
- `uv run ruff check src tests`
- `uv run python scripts/check_project_tracking.py` PASS
- focused parser/taxonomy/isolation/tracking: 47 passed
- core pytest: 2117 passed, 16 deselected, 1 expected durability warning
- `git diff --check` clean
