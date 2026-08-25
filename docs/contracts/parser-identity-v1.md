# Parser Identity Contract v1

**Contract ID:** `veriformis.parser-identity`

**Contract version:** `1`

**Status:** Implemented through independent-product Phase 11.7. Parse-report
bytes are unchanged.

**Last reviewed:** 2026-08-25

## Purpose

Name the parser kind, version string already stored on `SourceRef` and
`veriformis.parse-report/v1`, runtime libraries, and recovery-quality status.

Recovery quality is the parse-report `status`: `complete`, `degraded`, or
`refused`. Digitally-born PDF with a text layer is `complete` or `degraded`.
Image-only PDF is `refused` with limitation `ocr-unsupported`.

## Pins

| Kind | Version field |
| --- | --- |
| `text` | `PARSER_VERSION` in `parsers/text.py` |
| `markdown` | `PARSER_VERSION` in `parsers/markdown.py` |
| `docx` | `PARSER_VERSION` in `parsers/docx.py` |
| `html` | `PARSER_VERSION` in `parsers/html.py` |
| `pdf` | `PARSER_VERSION` in `parsers/pdf.py` |
| `csv` / `json` / `jsonl` | `CSV_PARSER_VERSION`, `JSON_PARSER_VERSION`, `JSONL_PARSER_VERSION` |

Runtime library versions are read from installed distributions and are not
part of source identity. Source identity remains logical path plus raw SHA-256.

## Non-goals

Changing golden parse-report digests. Process isolation. OCR.
