# Operator Troubleshooting (Phase 20.9)

**Status:** Fail-closed operator notes for the frozen CLI-first matrix

**Last reviewed:** 2026-09-01 (independent-product Phase 20.9)

This page stays honest to the frozen support matrix.
This page is not a version bump.

| Symptom | What it means | What to do |
| --- | --- | --- |
| Unknown suffix | The compiler refuses unsupported input. | Use a supported extension. Unknown suffix fails closed. |
| Image-only PDF | Default parse names `ocr-image` and refuses. | `ocr-image` remains explicitly unsupported. Extra `ocr` stays empty. |
| `veriformis: command not found` | The console script is not on PATH. | `uv run veriformis` or put `.venv/bin` on PATH. |
| Empty evaluation partition | One leakage group under default split rules. | Pass `--allow-empty-evaluation` to `curate` only when that is intentional. |
| Trainer extra missing | Optional extras stay empty. | The exporter does not train. Install a trainer yourself if you want one. |
| Hub upload | Hub execute is excluded. | There is no Hub execute. |
| Signed Mac app | Public signed Mac is not in the matrix. | Use the CLI. The workbench is a local-dev thin adapter. |
| GitHub xcodebuild | Unsigned Debug scheme only; `continue-on-error`. | This is not a public Mac claim. `public_signed_mac` stays false. |
| `quality-report` command | Quality stays preview-only. | The quality-report command is preview, not a gate. |

See also [install.md](install.md) Troubleshooting,
[support-lifecycle.md](support-lifecycle.md), and
[Support Matrix v1](contracts/support-matrix-v1.md).
