# Phase 8 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-23

## Exit-gate judgment

Passed. TRL SFT and MLX-LM LoRA are implemented optional adapters over a
verified bundle. Official-schema harnesses load DatasetDict-compatible
dicts and mlx-lm filenames without installing trainer wheels. Incompatible
rows fail in Veriformis. One bundle exports to both profiles with identical
membership and targets. Sidecars do not launch training. Core pytest still
passes without trainer extras.

Item 8.7 is this closeout pull request. Do not start Phase 9, 10, or 13
from this packet.

## Usability criteria

| ID | Judgment | Current-tree evidence |
| --- | --- | --- |
| U1 | Pass | `tests/profiles/test_discovery_closeout.py` — admission names accepted, transformed, and rejected goals/rows |
| U2 | Pass | `tests/exports/test_phase8_profile_isolation.py` — candidates refuse as Phase 10; extras stay empty |
| U3 | Pass | `tests/profiles/test_trl.py`, `tests/profiles/test_mlx_lm.py` — membership and loss-policy IDs unchanged |
| U4 | Pass | `tests/profiles/test_conformance.py`, `tests/profiles/test_discovery_closeout.py` — preference/tools/system/multi-assistant refused in Veriformis |
| U5 | Pass | `tests/profiles/test_admission.py` — Python / CLI / MCP admission identity |
| U6 | Pass | `tests/profiles/test_sidecars.py` — `launches_training` false; no subprocess |
| U7 | Pass | `tests/profiles/test_discovery_closeout.py` — one bundle, both profiles, same row-set identity and train rows |

## Delivered scope

- 8.1 opened the packet and published ADR-0012 (PR #82).
- 8.2 pinned official TRL and MLX-LM admission records with empty extras (PR #83).
- 8.3 emitted the TRL SFT adapter (PR #84).
- 8.4 emitted the MLX-LM LoRA adapter (PR #85).
- 8.5 added official-schema harnesses and optional profile-integration CI (PR #86).
- 8.6 emitted dataset-only launch sidecars (PR #87).
- 8.7 promoted `trl` and `mlx-lm` to implemented, named accepted/transformed/rejected goals and rows, and closed the phase.

## Remaining bounds (not Phase 8 gaps)

- Parquet / Arrow / Hugging Face Dataset remain Phase 9.
- Axolotl, LLaMA-Factory, Unsloth, and Aptus-as-profile remain Phase 10.
- Quality heuristics remain Phase 13.
- The exporter does not train.

## Verification summary

Local core gates for item 8.7 and the subsequent GitHub `ci` results are
recorded in `evidence.md`. Phase 9 may begin under its own packet when the
operator asks. Do not start Phase 9, 10, or 13 from this closeout.
