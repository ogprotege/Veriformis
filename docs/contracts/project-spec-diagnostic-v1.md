# Project Spec Diagnostic Contract v1

**Schema:** `veriformis.project-spec-diagnostic/v1`

**Status:** Runtime diagnostic payload. Independent-product item 19.4.

**Last reviewed:** 2026-08-31

## Purpose

Name one complete machine-readable failure for project-spec execute and
resume. Truncated JSON fails closed. Default human CLI text stays.

## Pin

| Field | Rule |
| --- | --- |
| `schema_id` | `veriformis.project-spec-diagnostic/v1` |
| `code` | Error code from the raised exception |
| `message` | Error message |
| `spec_id` | Optional spec identity when load succeeded |
| `stage` | Optional stage name |

A truncated object, a non-object, or a payload missing `schema_id`,
`code`, or `message` fails closed. CLI prints `error[code]: message`
then one complete JSON diagnostic line and exits `2`.

## Limitations

- Diagnostic emission is not Hub upload.
- A diagnostic is not a second policy engine.
