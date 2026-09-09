# Bounded product polish, 2026-09-09

The review baseline is `main` at `7f3cce6a42d63762c0f4d649cd68cdf334290554`,
the PR #203 merge after PR #204 at
`23bdc20b4667a1bd8381debd233d4d12a3bdd87a`. Both post-20 work packets are
complete. This is a bounded correction pass, not another phase.

## Completed PR #203

The imported quality preview was reviewed against current main. Its original
instruction/output and messages paths failed because the preview assumed a
`completion` target. The corrected binding preserves supplied fields, applies
the imported schema's context and target rules, and keeps preview v1
non-enforcing. All eight schemas have regression coverage. Document-source
report bytes match current main. See the
[PR #203 evidence](2026-09-09-quality-report-dataset-row.md).

PR #203 merged after all 24 GitHub check results succeeded on
`d9176bb036535bfade2d90a176f58e1795eb0fd3`. No review comments or unresolved
threads were present. Local main was synchronized before this pass.

## Corrections

Current operator instructions distinguish document-source workspace schema 3
from imported schema 4, the 17 document validation gates from the 13 imported
gates, and source grouping from ordinary imported record grouping. Examples
use fresh destinations and include quality previews. Columnar capabilities,
optional OCR requirements, export JSON text, and unsigned Mac setup match the
implemented boundaries.

The Mac export picker now requests a new destination name. An existing empty
directory is refused by the CLI, so the old folder chooser could not provide
a usable destination. Export digest evidence now belongs to the selected
bundle. Profile filtering uses that bundle's verified dry-run schema instead
of the compile form. Changing a profile retains only schema display evidence;
it invalidates the plan and requires another dry-run and confirmation.

Successful imported-row compiles now direct the operator to Mapping preview
instead of launching unsupported document-source goal preview. Result labels
say compiled preview, supervised target, and preview diagnostics. The
workbench does not train or run the quality-report command.

Completed roadmaps and packets remain archived in place with current index
labels. Historical observations, test counts, and phase-time claims remain
unchanged. The evidence index now links every Phase 8–19 closeout. DOC-002,
DOC-006, DOC-009, DOC-010, and DOC-011 are closed with explicit evidence.

## Observations

Three Mac regression assertions failed on the pre-fix implementation: stale
manifest evidence, schema inherited from the compile form, and document-only
preview after imported compilation. After correction, all 13 focused Mac
tests passed, including real imported compilation and export dry-run through
the repository CLI. The existing-empty-destination CLI reproduction failed
with its intended no-replace error and left the empty directory unchanged.

## Operator and Mac verification

The documented two-source continuation walkthrough, full-text compilation,
explicit messages compilation, and imported text-row walkthrough each produced
one train and one evaluation row. All four bundles verified with separately
retained manifest digests. The imported example initially refused files outside
the checkout; explicit `--source-root` on detect and preview corrected it.

Quality reports were byte-identical across repeated reads and left workspace
file hashes unchanged on all four fixtures. Eleven compatible generic exports
across split JSONL, canonical JSON, and constrained CSV passed source-bound
verification. Nested messages correctly refused CSV. All four bundle archives
and eleven receipt-bound export archives passed transport verification.
A test-harness assumption initially treated the default continuation schema as
messages; the completed run selected messages explicitly and derived export
expectations from actual row keys. No compiler behavior was changed for that
harness correction.

| Fixture | Manifest SHA-256 |
| --- | --- |
| messages | `37f96e2191765b8ea396c995cd2c408809600ac866f817235d16aa6542e3ce9f` |
| document | `8f31a6aa23c5b35e8cda2d550a8b40c7c409260356c80506d329a05e4f3c8a4d` |
| fulltext | `5c6a7200450f37e4e02ebba7f3b4987bb608b30d8adb05217e1a1f4d1a2b2685` |
| imported | `1977f23ab97b4437b8a541ad1e4a6fcaf042df81cfdac5f4a096ef11849d6661` |

The unsigned Mac gate passed 124 XCTest cases, including the real 74-cell
acceptance matrix, imported mapping through sealing, and the new selected-
bundle export regressions. Optional Aptus/profile/columnar tests passed:
35 passed, 2914 deselected, zero skips, with required libraries and offline
flags. Adapter self-conformance, parity, the project-spec example, and Python
sdist/wheel metadata inspection passed. These do not establish a live trainer
or signed Mac release claim.

A manual picker check could not be observed: the native UI tool failed to
start its pipe on three attempts, including after a reset. The tested app
launched, then the temporary instance was closed without starting work.
Interactive picker selection remains a named verification gap. The native
build and automated flow results above are observed; visual interaction is not.

## Final local gates

`bash scripts/release/check_local.sh` passed with Python 3.12: 2913 passed,
32 deselected, and one expected staging-link RuntimeWarning. Lock, Ruff,
clean-wheel installation, both standalone golden compiles, external-digest
verification, and transport passed. The earlier run's two wording assertions
were corrected without removing a boundary or skipping a test; its failure
log is retained alongside the final pass.

Project tracking passed. Four focused tracking/preview assertions and eighteen
focused extension/export assertions passed. Repository-wide Ruff, structured
JSON checks, `git diff --check`, and 502 local documentation targets passed.
Required GitHub checks and review state are recorded by the polish pull request;
local observations do not substitute for that publication gate.

## Preservation and disposition

Before any archival move, the complete takeover backup and all six local-only
files were copied to
`~/Documents/Veriformis-Archives/2026-09-09-product-closeout/`.
`preservation-manifest.json` records file sizes, modes, SHA-256 values, and
symbolic-link targets. A separate reread matched both copies to the originals.
No original was moved or deleted.

| Local-only original | Disposition |
| --- | --- |
| `.codex/environments/environment-2.toml` | Active machine configuration; remains local |
| `veriformis-operator-finish-plan.md` | Historical, superseded by the completed operator work and frozen C7; do not rerun its corpus build instructions |
| `veriformis-format-matrix-plan.md` | Historical fixture ideas; superseded as an execution plan by implemented fixtures, current guides, and defect closure |
| `veriformis-remaining-lanes-plan.md` | Historical baseline; profile, columnar, fixture, and mapping work now implemented |
| `veriformis-quality-report-dataset-row-design.md` | Historical design, superseded by merged PR #203 |
| `veriformis-trainer-extras-design.md` | Retained boundary decision; old pins are historical, trainer extras remain empty |

The takeover directory at
`/private/tmp/veriformis-cursor-takeover-20260909-135711/` remains untouched.
Its complete durable copy is `takeover-backup/` under the archive above.
The six file copies are under `local-only-originals/`. None is committed.

## Retained boundaries

Version remains 0.1.0 development alpha with claim
`cli-first-independent-core`. C7 and unrelated work are untouched. Quality
reports remain previews and do not gate seal. The Mac workbench is an unsigned
development application, not a public signed release. Its imported mapping
chooser wraps one source file; multi-source confirmed plans use the CLI.
Mixed document/row fusion is refused. Required review evidence is applied
through the CLI/Python/MCP construction path; the Mac review view exchanges
packets and does not itself apply a construct receipt.

No training, generator, Hub execution, plugin expansion, or new phase was
added. Manual Mermaid rendering, the versioned legacy `aptus-row-shape` gate
ID, and remaining historical architecture line coordinates stay recorded as
maintenance debt. They are not unfinished stages of the completed plan.
