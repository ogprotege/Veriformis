# Support Lifecycle (Phase 20.9)

**Status:** Operator-facing support policy for the frozen CLI-first matrix

**Last reviewed:** 2026-09-01 (independent-product Phase 20.9)

This page records semantic versioning, compatibility windows, upstream
profile review cadence, deprecation notice, vulnerability response, and
release rollback for the frozen CLI-first matrix.
This page is not a version bump.
Version remains `0.1.0` development alpha.

## Semantic versioning

The Python package uses SemVer.

- MAJOR: an incompatible change to a frozen contract, a workspace or
  bundle revision without an `upgrade-workspace` path, or a sealed
  identity that previously loaded.
- MINOR: an additive implemented capability that existing loaders still
  accept.
- PATCH: a defect fix that preserves identities and loaders.

Loading `veriformis.support-matrix/v1` is not a version tag.
Item 20.10 retained `0.1.0` because sealed manifests bind
`veriformis_version` and existing goldens stay byte-identical.

## Compatibility windows

Supported Python: 3.11, 3.12, and 3.13. CI proves Ubuntu 3.11–3.13 and
macOS 3.12. Workspace physical layout is 1. Revisions 1 and 2 upgrade to
3. Revision 4 dataset-row is a no-op.
Unknown versions fail closed.

Contract v1 documents remain loadable. Unknown fields fail closed. See
[migration.md](migration.md).

Public signed Mac, Hub execute, generator, plugin loader, hosted
training, required extras, quality-report command, and published corpus
tiers stay excluded.

## Upstream profile review cadence

Optional adapters `trl`, `mlx-lm`, `axolotl`, `llama-factory`, and
`aptus` are dataset-only. Official consumer schemas can change. Review
cadence: when a profile pin is admitted, record the official-schema
review date on that pin. A later upstream change does not silently
expand the frozen matrix. Isolated CI jobs use `continue-on-error` and
cannot block the independent core. Unsloth is not executable.
The exporter does not train.

## Deprecation notice

A frozen matrix capability is not removed in a patch. Deprecation
requires a dated notice here and in [current-status.md](current-status.md),
at least one remaining loadable release, and a fail-closed replacement
or upgrade path.
This page does not deprecate any frozen matrix capability.

## Vulnerability response

See [security.md](security.md). There is no required pip-audit or OSV CI
job. An owner may run an optional scanner. Report first-party defects
against the MIT-licensed source. A live credential in `src/`,
`scripts/`, `examples/`, or `docs/` is a defect. Parsers fail closed.
There is no compile-path network client.

## Release rollback

Python install rollback is pinning the previous wheel. Workspace objects
are content-addressed. `HEAD` advances only after semantic replay. Do
not hand-edit content-addressed objects. `upgrade-workspace` is the
supported migration. A failed seal does not publish a bundle. There is
no public signed Mac artifact to roll back.

## Operator docs

User, mapping, goal, export, profile, troubleshooting, security,
privacy, and migration pages stay honest to the frozen matrix:

- [Install](install.md)
- [Existing-dataset import](mapping.md)
- [CLI goals](cli.md)
- [Generic exports](generic-exports.md)
- [Consumer profiles](consumer-profiles.md)
- [Troubleshooting](troubleshooting.md)
- [Security and privacy](security.md)
- [Migration](migration.md)
