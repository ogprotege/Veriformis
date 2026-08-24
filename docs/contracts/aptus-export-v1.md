# Aptus Export v1

**Selector:** `split-jsonl-directory` v1 + `consumer_id=aptus` v1

**Status:** Implemented optional adapter. Taxonomy `aptus` is
`implemented`. The sibling `aptus-handoff-v1` descriptor remains. Default
seal still does not write that descriptor. No training launch.

**Last reviewed:** 2026-08-24

## Purpose

Map a verified Veriformis bundle onto identity JSONL for Aptus-admitted
schemas without changing membership, targets, or loss-policy IDs, and
without giving Aptus special product authority over generic export.

## Layout

```text
README.md
data/train.jsonl
data/evaluation.jsonl
export-receipt.json
metadata/dataset-card.json
metadata/aptus-profile.json
metadata/aptus-launch.json
metadata/row-provenance.jsonl
```

Admitted schemas are `instruction_output`, `messages`, and
`prompt_completion`. All three map by identity. Plain `text` is refused.
Request v2 is refused. Extra is empty. The launch sidecar records
`veriformis handoff` as the optional sibling CLI fragment and
`writes_sibling_handoff: false`. External-digest and assignment checks
remain operator-supplied. Veriformis does not launch Aptus.

## Non-goals

Replacing the sibling handoff CLI, writing the descriptor on default
seal, admitting `text` rows, and training launch.
