# Phase 8 Progress

Append-only. Corrections add a later entry.

## 2026-08-23 — Phase 8 opened; item 8.1 in progress

**Status:** Packet created from clean `main` at
`64a7799c27d1a489f01d77d8ba399910c95c0712` (PR #81 after PR #80).

Item 8.1 publishes ADR-0012 and keeps `trl` / `mlx-lm` planned. Generic
exports stay `consumer_id` null. Selecting those identifiers refuses with the
later item. Do not emit trainer files.

Focused isolation tests passed (8). Tracking, Ruff, structured JSON, and
diff check passed. Core pytest passed 1964 with 1 deselected and the
intentional transport durability warning.

**Next action:** Publish the item 8.1 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 8.2.

## 2026-08-23 — Item 8.1 merged; item 8.2 in progress

**Status:** Item 8.1 merged as PR #82 at `799d56f` after all 14 GitHub
checks passed. Local `main` equals `origin/main` at that SHA.

Item 8.2 pins official TRL and MLX-LM admission records as packaged
`admission-v1.json`, declares empty extras `trl` and `mlx-lm`, and exposes
byte-identical discovery on Python, CLI `profile-admissions`, and MCP
`profile_admissions`. Both records remain `state: planned`. Export still
refuses `consumer_id=trl|mlx-lm`. Trainer packages are not installed.

Focused isolation and admission tests passed (14). Tracking, Ruff, lock,
structured JSON, and diff check passed. Core pytest passed 1970 with 1
deselected and the intentional transport durability warning.

**Next action:** Publish the item 8.2 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 8.3.

## 2026-08-23 — Item 8.2 merged; item 8.3 in progress

**Status:** Item 8.2 merged as PR #83 at
`7351904e58c67c925a3a878af350335620306260` after all 14 GitHub checks
passed. Local `main` equals `origin/main`.

Item 8.3 emits the TRL SFT adapter over `split-jsonl-directory` v1 with
`consumer_id=trl`. Mapped JSONL plus profile metadata. Taxonomy remains
planned. Core does not import TRL. MLX-LM still refuses.

Focused TRL and discovery tests passed. Tracking, Ruff, JSON, and diff
check passed. Core pytest passed 1975 with 1 deselected and the
intentional transport durability warning.

**Next action:** Publish the item 8.3 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 8.4.

## 2026-08-23 — Item 8.3 merged; item 8.4 in progress

**Status:** Item 8.3 merged as PR #84 at
`fe326c8e1aac18ce2e795f6d4618566a56ff22b5` after all 14 GitHub checks
passed. Local `main` equals `origin/main`.

Item 8.4 emits the MLX-LM LoRA adapter: required `train.jsonl`, optional
`valid.jsonl` when evaluation is nonempty, no `test.jsonl`. Taxonomy remains
planned. Core does not import mlx-lm.

Focused MLX-LM and discovery tests passed. Tracking, Ruff, JSON, and diff
check passed. Core pytest passed 1982 with 1 deselected and the
intentional transport durability warning.

**Next action:** Publish the item 8.4 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 8.5.

## 2026-08-23 — Item 8.4 merged; item 8.5 in progress

**Status:** Item 8.4 merged as PR #85 at
`056a0754f162242b1eddc0fda447bdac51cf9f0c` after all 14 GitHub checks
passed.

Item 8.5 adds an official-schema harness (Dataset.from_list-compatible
dicts, mlx-lm filenames) without installing trainer wheels. Optional
`profile_integration` tests skip unless extras are present. Optional CI
job is continue-on-error.

Core pytest passed 1992 with 3 deselected. Tracking and Ruff passed.

**Next action:** Publish the item 8.5 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 8.6.
