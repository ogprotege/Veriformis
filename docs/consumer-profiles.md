# Consumer Profile Freeze (Phase 20.8)

**Status:** Frozen optional adapters for the CLI-first 1.0 matrix

**Last reviewed:** 2026-09-01

Consumer profiles are optional adapters over a verified bundle. The
exporter does not train. Empty extras stay empty. A profile job failure
does not block the independent core.

## Frozen implemented optional adapters

`trl`, `mlx-lm`, `axolotl`, `llama-factory`, and `aptus` are implemented
export adapters. Discovery names accepted, transformed, and rejected
goals and rows. Sidecars are dataset-only.

## Frozen non-executable candidate

`unsloth` remains experimental and is not executable.

## Isolation

CI jobs `profile-integration (optional)`, `columnar-integration (optional)`,
and `aptus-integration (optional)` use `continue-on-error: true`. Core
required jobs do not install trainer extras.

See [Consumer Profile Admission v1](contracts/profile-admission-v1.md) and
[Support Matrix v1](contracts/support-matrix-v1.md).
