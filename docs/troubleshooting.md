# Operator Troubleshooting (Phase 20.9)

**Status:** Fail-closed operator notes for the frozen CLI-first matrix

**Last reviewed:** 2026-09-01 (independent-product Phase 20.9)

This page stays honest to the frozen support matrix.
This page is not a version bump.

| Symptom | What it means | What to do |
| --- | --- | --- |
| Unknown suffix | The compiler refuses unsupported input. | Use a supported extension. Unknown suffix fails closed. |
| Image-only PDF | Default parse refuses with `pdf.ocr-required` (limitation `ocr-unsupported`). | The `ocr-image` input family remains explicitly unsupported. `veriformis ocr-preview PDF` runs optional local Tesseract 5 when it is installed; extra `ocr` stays empty. |
| HTML refused as `html.charset-unknown` / `html.charset-invalid` | The capture is not valid UTF-8 and declares no usable charset, or declares one that cannot decode it. | Re-save the page as UTF-8 or add a correct `<meta charset>`. Veriformis never guesses an encoding. |
| `veriformis: command not found` | The console script is not on PATH. | `uv run veriformis` or put `.venv/bin` on PATH. |
| Empty evaluation partition | One leakage group under default split rules. | Pass `--allow-empty-evaluation` to `curate` only when that is intentional. |
| Trainer extra missing | Trainer extras stay empty. | The exporter does not train. Install a trainer yourself if you want one. |
| `export execute` refuses and names extra `columnar`; `parse --mode dataset-row` refuses a `.parquet` / `.arrow` file | PyArrow and Datasets are not installed. | `uv sync --extra columnar` (or `pip install "veriformis[columnar]"`), then rerun. |
| Hub upload | Hub execute is excluded. | There is no Hub execute. |
| Signed Mac app | Public signed Mac is not in the matrix. | Use the CLI. The workbench is a local-dev thin adapter. |
| GitHub xcodebuild | Unsigned Debug scheme only; `continue-on-error`. | This is not a public Mac claim. `public_signed_mac` stays false. |
| `quality-report` command | Quality stays preview-only. | The quality-report command is preview, not a gate. |

See also [install.md](install.md) Troubleshooting,
[support-lifecycle.md](support-lifecycle.md), and
[Support Matrix v1](contracts/support-matrix-v1.md).
