# Axolotl SFT Export v1

**Selector:** `split-jsonl-directory` v1 + `consumer_id=axolotl` v1

**Status:** Implemented optional adapter. Taxonomy `axolotl` is
`implemented`. Loader conformance is item 10.7. Launch sidecar is item
10.8. No training launch.

**Last reviewed:** 2026-08-24

## Purpose

Map a verified Veriformis bundle onto Axolotl JSONL plus a dataset-only
YAML sidecar without changing membership, targets, or loss-policy IDs.

## Layout

```text
README.md
data/train.jsonl
data/evaluation.jsonl
export-receipt.json
metadata/dataset-card.json
metadata/axolotl-profile.json
metadata/axolotl-sft-launch.json
metadata/axolotl-sft.yaml
metadata/row-provenance.jsonl
```

`instruction_output` maps by identity onto alpaca keys. `messages` maps
by identity onto OpenAI `chat_template` keys. `prompt_completion` remaps
to alpaca (`prompt` → `instruction`, `completion` → `output`, empty
`input`). `text` maps by identity onto `completion`. Evaluation may be
empty; the YAML then omits `test_datasets`. Request v2 is refused.
`metadata/axolotl-sft.yaml` is constructed as exact bytes and does not
select `base_model`. The JSON launch sidecar records
`axolotl train metadata/axolotl-sft.yaml`. Veriformis does not launch
training.

## Non-goals

Installing Axolotl into core, preference/pre-tokenized/tools/vision
types, applying a chat template as a membership change, and Unsloth
emission.
