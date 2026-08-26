# Phase 12 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-25

**Closeout merge:** PR #112 at `892939f527974b69282296ded04eb3b43643554f`

## Exit-gate judgment

Passed. Optional local OCR is Tesseract 5 under ADR-0016. Pages classify as
digital, OCR, or merged. Digital text is never replaced. Confidence warn /
review / refuse retains refused text on `held_text`. `ocr-preview` is
read-only. Extra `ocr` is empty. Default parse still refuses image-only
PDF. `ocr-image` stays `explicitly_unsupported`. Do not start Phase 13
from this packet.

## Usability criteria

| ID | Judgment | Evidence |
| --- | --- | --- |
| U1 | Pass | Discovery still omits `ocr-image` from implemented families |
| U2 | Pass | Default parse of image-only PDF still `pdf.ocr-required` |
| U3 | Pass | Digital pages are never sent to a provider |
| U4 | Pass | Core pytest does not import Tesseract; extra is empty |
| U5 | Pass | `ocr-preview` on Python, CLI, and MCP |
| U6 | Pass | Tesseract provider opens no sockets |
| U7 | Pass | Handwriting remains a named limitation |

## Delivered scope

- 12.1 packet; OCR still refused.
- 12.2 evaluation; operator accepted Tesseract 5.
- 12.3 ADR-0016 and recovery identities.
- 12.4 digital / OCR / merged paths.
- 12.5 confidence thresholds.
- 12.6 preview and review hooks.
- 12.7 empty `ocr` extra and subprocess provider.
- 12.8 no-network, missing tessdata, corrupt raster, replay, closeout.

## Exclusions

Phase 13 quality intelligence. Cloud OCR. Handwriting. Promoting
`ocr-image` as default parse. Network model download.
