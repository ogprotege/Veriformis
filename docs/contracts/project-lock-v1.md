# Project Lock Contract v1

**Contract ID:** `veriformis.project-lock`

**Contract version:** `1`

**Schema:** `veriformis.project-lock/v1`

**Status:** Schema pin. A lock is not execute and does not replace `uv.lock`.
Independent-product item 19.4.

**Last reviewed:** 2026-08-31

## Purpose

Pin the digest of one `veriformis.project-spec/v1` object together with
the Veriformis version, Python major.minor version, and declared extra
presence so a later clean host can compare the same semantic identity.

## Pin

| Field | Rule |
| --- | --- |
| `contract_id` | `veriformis.project-lock` |
| `contract_version` | `1` |
| `schema_id` | `veriformis.project-lock/v1` |
| `spec_id` | Spec identity from the pin |
| `spec_digest` | SHA-256 of the spec payload excluding `spec_id` and null optional fields |
| `veriformis_version` | Installed package version |
| `python_version` | `major.minor` |
| `extras` | Sorted map of declared extra name to `empty` or `present` |
| `lock_id` | `derive_id("plk", …)` over the payload excluding `lock_id` and null optional fields |
| `workspace_head` | Optional revision identity. Required for resume. |
| `source_identities` | Optional sorted source identities. Required for resume. |

Unknown fields fail closed. Credentials cannot appear. The lock is not
`uv.lock` and does not upload. Locks without resume pins still load.
`spec-run` and `spec-resume` emit a lock with HEAD and source identities.
`spec-lock --workspace` pins those fields from an existing workspace.

## Exit codes

`spec-schema`, `spec-dry-run`, `spec-lock`, `env-inspect`, `spec-run`,
and `spec-resume` use `0` on success and `2` on invalid input or
identity drift. Partial publication `1` is unused on these surfaces.
