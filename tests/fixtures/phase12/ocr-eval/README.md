# Phase 12.2 OCR evaluation corpus

Original Veriformis fixture pages. Not third-party scans.

Each case is PDF standard Helvetica, rasterized with the pinned
`pypdfium2` renderer at 200 dpi. Image-only PDFs embed that raster and
have no text layer.

Handwriting is excluded (roadmap non-goal). CJK is not rasterized here
because standard-14 Helvetica has no CJK glyphs.

Rebuild with:

```bash
uv run python scripts/phase12_ocr_eval.py build
```

Do not treat this directory as a production importer.
