# Phase 11 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-25

## Exit-gate judgment

Passed. A mixed directory produces a deterministic collection plan. Hidden,
unsupported, duplicate, and symlink members are counted. Limits fail closed.
CLI `parse` of a directory and of its files accept the same sources. The Mac
no longer walks folders. Archives are not ingested. No new input family is
named implemented. Image-only PDF still refuses as `ocr-image`.

Items 11.1–11.8 are this closeout pull request. Do not start Phase 12 or 13
from this packet.

Local gates: ruff pass; tracking pass; lock check pass; core pytest 2112
passed, 16 deselected, one expected durability warning.

## Usability criteria

| ID | Judgment | Evidence |
| --- | --- | --- |
| U1 | Pass | `test_parse_directory_matches_explicit_files`; Swift expand no longer enumerates |
| U2 | Pass | Hidden/unsupported/duplicate tests |
| U3 | Pass | `test_max_files_fails_closed` |
| U4 | Pass | `test_symlink_is_refused_and_not_followed` |
| U5 | Pass | Existing file-list parse tests remain |
| U6 | Pass | Taxonomy input families unchanged |
| U7 | Pass | Empty-text PDF still refused |

## Delivered scope

- 11.1 packet and ADR-0015.
- 11.2 collection plan v1.
- 11.3 `collect` inventory; parse/preflight expansion.
- 11.4 archive skip.
- 11.5 hardening matrix.
- 11.6 isolation skip.
- 11.7 parser identity pins.
- 11.8 no new families; closeout.

## Exclusions

OCR. Archive ingest. Parser subprocesses. EPUB, sheets, decks, mail,
notebooks, XML, subtitles, extra code suffixes. Phase 13 quality facts.
