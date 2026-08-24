# Operator compile — 2026-08-24 Pascendi

Local, non-authoritative run note. Does not change product claims.

**When:** 2026-08-24T13:54:52Z

**Where:** `/Users/biscuit/Documents/Veriformis`

**Product:** Veriformis `0.1.0` on `main` at
`abdcce6474aadd33fcf38a5360b63a4f8d293a5c` (Phase 9 closed).

## Path

Document-source compile through seal, verify, and Finder-safe zip. No
dataset-row mapping. No generic columnar export. No TRL / MLX-LM /
Aptus adapter.

## Source

One Markdown file, logical path
`1907-09-08_pascendi-dominici-gregis.md`. Parser `markdown` 1.2.0. Pius X,
*Pascendi Dominici Gregis* (1907-09-08). Raw size 131,986 bytes.

## Recipe

- Objective: `full_text`
- Target row schema: `text`
- Review: none
- Cleaning: page-numbers + whitespace; 0 transform records
- Chunk: paragraph, size 1000, overlap 100

## Result

| Fact | Value |
| --- | --- |
| Parsed sources | 1 |
| Chunks | 31 |
| Candidates / accepted | 31 / 31 |
| Curated in / excluded / quarantined | 31 / 0 / 0 |
| Train / evaluation | 31 / 0 |
| Leakage groups | 1 |
| Validation | 17/17 passed |
| Bundle | `dataset-2026-08-24T13-54-52Z.vfbundle` |
| Manifest SHA-256 | `94b63232166aeedc9db797fdc0ec0167b2135d8c01bd3934635250a0a2245ace` |
| Seal grade | `self_consistent` |
| Transport zip | `dataset-2026-08-24T13-54-52Z.vfbundle.zip` (6 members) |
| Archive SHA-256 | `ab51ba97a960c6f15acb07a9706839060c914da3f41ffab6fa24d1d304ba7928` |
| Zip verify grade | `external_digest` |

Empty evaluation is expected: default split is leakage-safe by source
group, and one document is one group.

One train row is scrape front matter (`title` / `author` /
papalencyclicals.net metadata), not encyclical prose. The compiler
copied the file; it did not invent the row.
