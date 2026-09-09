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
| `spec_digest` | Embedded pipeline: SHA-256 of the spec payload excluding `spec_id` and null optional fields. External reference: SHA-256 of canonical `{spec: payload, pipeline_ref_sha256: SHA256(raw reference bytes)}` |
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

Resume compares every recorded environment field: Veriformis version,
Python major.minor, and declared extra presence. The extra map describes
package declarations, not installed dependency versions; `uv.lock` remains
the dependency pin. External references resolve relative to the spec file.
Execution decodes the same captured reference bytes that it hashes. The
returned lock retains that digest even if the reference changes during the
run. Old reference locks without this content binding refuse resume.
Embedded-pipeline digests remain unchanged.

## Exit codes

`spec-schema`, `spec-dry-run`, `spec-lock`, `env-inspect`, `spec-run`,
and `spec-resume` use `0` on success and `2` on invalid input or
identity drift. Partial publication `1` is unused on these surfaces.
