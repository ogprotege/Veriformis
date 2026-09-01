# Publication Adapter Contract v1

**Contract ID:** `veriformis.publication-adapter`

**Contract version:** `1`

**Schema:** `veriformis.publication-adapter/v1`

**Status:** Schema pin. Loading a pin is not upload. ADR-0020 Decision A:
no Hub execute. Independent-product item 19.7.

**Last reviewed:** 2026-08-31

## Purpose

Name one optional publication intent over an already verified export.
The default local path has no upload. Hugging Face Dataset is a local
container, not Hub upload.

## Pin

| Field | Rule |
| --- | --- |
| `destination` | `hugging-face-hub` |
| `repository` | Nonempty repository name. Not an upload. |
| `visibility` | `private` or `public` |
| `revision` | Nonempty revision name |
| `credential_source` | `none` |
| `dry_run_required` | `true` |
| `execute_allowed` | `false` |
| `retry_allowed` | `false` |
| `generation_allowed` | `false` |
| `plugin_install_allowed` | `false` |
| `local_container_is_not_upload` | `true` |
| `adapter_id` | `derive_id("pub", …)` excluding `adapter_id` |

Unknown fields fail closed. Loading a pin is not upload.

## Limitations

- `no-execute`
- `no-hub-upload`
- `no-credentials-in-artifacts`
- `no-retry`
