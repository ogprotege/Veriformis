# TRL SFT Export v1

**Selector:** `split-jsonl-directory` v1 + `consumer_id=trl` v1

**Status:** Implemented optional adapter. Taxonomy `trl` is `implemented`.
Loader conformance is item 8.5. Launch sidecar is item 8.6. No training
launch.

**Last reviewed:** 2026-08-23

## Purpose

Map a verified Veriformis bundle onto TRL SFTTrainer language-modeling or
prompt-completion columns without changing membership, targets, or
loss-policy IDs.

## Layout

```text
README.md
data/train.jsonl
data/evaluation.jsonl
export-receipt.json
metadata/dataset-card.json
metadata/trl-profile.json
metadata/trl-sft-launch.json
metadata/row-provenance.jsonl
```

Partitions are JSONL objects. `instruction_output` is assembled into
`prompt` / `completion` (`prompt` is `instruction`, or `instruction` plus a
newline and `input` when `input` is nonempty). `text`, `prompt_completion`,
and `messages` map by identity. Evaluation may be empty. Request v2 is
refused. `metadata/trl-sft-launch.json` records DatasetDict `data_files`
and a dataset-only `trl sft --dataset_name json` fragment. It does not
select a model, set hyperparameters, or launch training.

## Non-goals

Generic Hugging Face claims, preference/stepwise/tools/vision types,
round-trip reconstruction of assembled prompts, installing TRL into core,
and MLX-LM emission.
