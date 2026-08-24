# LLaMA-Factory SFT Export v1

**Selector:** `split-jsonl-directory` v1 + `consumer_id=llama-factory` v1

**Status:** Implemented optional adapter. Taxonomy `llama-factory` is
`implemented`. Loader conformance is item 10.7. Launch sidecar is item
10.8. No training launch.

**Last reviewed:** 2026-08-24

## Purpose

Map a verified Veriformis bundle onto LLaMA-Factory alpaca or sharegpt
JSONL plus `dataset_info.json` without changing membership, targets, or
loss-policy IDs.

## Layout

```text
README.md
data/train.jsonl
data/evaluation.jsonl
data/dataset_info.json
export-receipt.json
metadata/dataset-card.json
metadata/llama-factory-profile.json
metadata/llama-factory-sft-launch.json
metadata/row-provenance.jsonl
```

`instruction_output` maps by identity onto alpaca keys. `messages` remaps
to sharegpt `conversations` with `from`/`value` tags `human` and `gpt`.
`prompt_completion` remaps to alpaca. `text` maps by identity onto the
pre-training `text` column. `dataset_info.json` `file_name` values are
relative to `data/`. Evaluation may be empty; the evaluation dataset
name is then omitted. Request v2 is refused. The launch sidecar records
`llamafactory-cli train` without `--train`. Veriformis does not launch
training.

## Non-goals

Installing LLaMA-Factory into core, history/KTO/ranking/tools/vision
types, and Unsloth emission.
