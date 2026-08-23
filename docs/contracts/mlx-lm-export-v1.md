# MLX-LM LoRA Export v1

**Selector:** `split-jsonl-directory` v1 + `consumer_id=mlx-lm` v1

**Status:** Executable adapter. Taxonomy `mlx-lm` remains `planned` until
item 8.7. Loader conformance is item 8.5. Launch sidecar is item 8.6. No
training launch.

**Last reviewed:** 2026-08-23

## Purpose

Map a verified Veriformis bundle onto mlx-lm LoRA `train.jsonl` and optional
`valid.jsonl` without changing membership, targets, or loss-policy IDs.

## Layout

```text
README.md
train.jsonl
valid.jsonl          # omitted when evaluation is empty
export-receipt.json
metadata/dataset-card.json
metadata/mlx-lm-profile.json
metadata/mlx-lm-lora-launch.json
metadata/row-provenance.jsonl
```

`test.jsonl` is mlx-lm's `--test` file and is not emitted from Veriformis
evaluation. `instruction_output` assembles `prompt`/`completion`. Other
schemas map by identity. Request v2 is refused.
`metadata/mlx-lm-lora-launch.json` records the `--data` directory and
omits `valid.jsonl` when evaluation is empty. It names `--mask-prompt` as
the documented completion-only flag for chat and completions datasets. It
does not select a model, set iters, include `--train` in `command_argv`,
or launch training.

## Non-goals

Generic Hugging Face claims, tools/preference/vision types, launching
training, installing mlx-lm into core.
