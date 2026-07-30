# CLI Reference

**Last reviewed:** 2026-07-29 after Group 3 completion

This reference describes the implemented Veriformis `0.1.0` stage-command CLI.
The Group 3 runtime is complete. `PipelineService` and thin CLI conversion
remain Group 4 work.

## Run the CLI

From a development checkout:

```bash
uv sync --extra test
uv run veriformis --help
```

The installed console command is `veriformis`.

## Supported inputs

`parse` accepts explicit files with these extensions:

- documents: `.txt`, `.md`, `.markdown`, `.docx`;
- source code: `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`,
  `.rb`, `.sh`.

Source code enters as one language-tagged code block. Directories, PDF, HTML,
CSV, JSON, JSONL, and other extensions are not supported in `0.1.0`. Text
inputs must be UTF-8.

## Complete raw-source example

The default split requires a non-empty evaluation partition, so use at least
two independent source groups:

```bash
uv run veriformis parse source-a.md source-b.md -o build/workspace
uv run veriformis clean build/workspace
uv run veriformis chunk build/workspace --strategy paragraph
uv run veriformis construct build/workspace --objective full_text
uv run veriformis curate build/workspace
uv run veriformis split build/workspace
uv run veriformis format build/workspace
uv run veriformis validate build/workspace
uv run veriformis seal build/workspace -o build/example.vfbundle
uv run veriformis verify build/example.vfbundle
```

The final command reports `self_consistent`. `seal` prints the manifest
SHA-256. Retain it outside the bundle and supply it for external binding:

```bash
uv run veriformis verify build/example.vfbundle \
  --manifest-sha256 EXPECTED_MANIFEST_SHA256
```

A matching expected digest produces `external_digest`.

For one leakage group, use `curate --allow-empty-evaluation` only when an empty
evaluation partition is intentional.

## Workspace and artifacts

Commands exchange immutable artifacts through this workspace layout:

```text
WORKSPACE/
├── workspace.json
├── HEAD
├── LOCK
├── objects/sha256/<prefix>/<digest>
├── revisions/<revision-id>/revision.json
└── .txn/
```

The physical layout is schema 1. Active revisions use schema 3. `HEAD` names
the current immutable revision and its logical output map.

| Stage | Logical output keys |
| --- | --- |
| Parse | `registry`; per-source `raw`, `canonical`, `document`, `diagnostics` |
| Clean | `transforms`; per-source `document`, `cleaning-plan`, `block-derivations` |
| Chunk | `chunks` |
| Construct | `recipe`, `result` |
| Curate | `plan`, `result` |
| Split | `result` |
| Format | `row-set`, `train`, `evaluation`, `provenance` |
| Validate | `snapshot`, `report` |
| Seal | `manifest`, `attestation` |

Every successful stage commits a revision atomically. Rerunning an upstream
stage invalidates every descendant. Older revisions remain immutable history.
Workspace open verifies the complete parent chain and all referenced object
digests.

If `HEAD` becomes visible but final directory sync cannot be confirmed, the
command succeeds and prints `warning[commit-durability]`. Preserve the
workspace and verify it after storage is stable.

## Commands

### `upgrade-workspace`

```text
veriformis upgrade-workspace WORKSPACE
```

The command verifies the current history and applies every supported revision
migration. It migrates v1 to v2 and then v2 to v3 when both are needed.

The v2 to v3 migration preserves parse, clean, chunk, and construct facts. It
adds curate and split as absent. It resets legacy format, validate, and seal
state to absent because those artifacts do not satisfy the finished-dataset
contract. Historical revisions and objects remain intact. Running the command
on a current workspace is a no-op.

### `parse`

```text
veriformis parse PATHS... -o WORKSPACE [--source-root ROOT]
```

The command captures raw bytes before parsing and commits all paths together.
Each source ID binds its logical path and raw SHA-256. Same-basename inputs
remain distinct when their logical paths differ. Distinct logical sources with
identical bytes also remain distinct.

`--source-root` defines the stable root for logical paths. It defaults to the
current directory. Every input must resolve beneath it. Adding another file to
a parse batch does not change an existing source identity.

The parse revision stores the source registry and each source's raw bytes,
canonical extracted text, strict document IR, and mandatory parse report.
Error diagnostics prevent commit. Before `HEAD` advances, the transaction
cross-validates the registry, source descriptors, canonical text, IR
projection, and diagnostics.

The output directory may be new or an existing revision workspace. It may not
be a non-empty unrelated directory. Replacing parse state invalidates all later
stages.

### `clean`

```text
veriformis clean WORKSPACE [--rules NAME,NAME] [--custom REGEX]
```

Built-in rules are:

- `page-numbers`
- `headers-footers`
- `whitespace`
- `urls`
- `emails`
- `special-chars`
- `lowercase`

With no option, clean uses `page-numbers` and `whitespace`. Supplying
`--rules` or `--custom` replaces that default selection. `--custom` adds one
regular-expression removal rule. There is no replacement-text option.

For each source, clean creates and replays a source-scoped plan. The plan binds
configuration, operations, allowed paths, locations, before and after digests,
character and byte counts, warnings, and a portable parse-input digest. The
revision stores cleaned IR, the exact plan, block derivations, and the combined
transform log.

A rule that would remove more than 30 percent of its target is skipped and
reported. Current prose rules do not edit inline code, code blocks, math, or
other literal payloads. Repeating clean with unchanged current configuration
is a no-op.

### `chunk`

```text
veriformis chunk WORKSPACE \
  [--strategy paragraph|fixed|sliding|sentence|structure] \
  [--size 1000] \
  [--overlap 100]
```

`paragraph` is the default. `size` and `overlap` are character counts.
`overlap` affects fixed and sliding strategies.

- `paragraph` groups blocks without exceeding `size` when possible.
- `fixed` creates fixed character windows with optional overlap.
- `sliding` uses overlapping windows.
- `sentence` groups heuristic English sentence splits up to `size`.
- `structure` starts sections at headings and applies paragraph grouping.

Every chunk has a source-scoped identity and reconstructible
`SourceEvidence`. Chunks never cross body, footnote, or endnote regions.

### `construct`

```text
veriformis construct WORKSPACE --objective OBJECTIVE \
  [--source SOURCE_ID_OR_LOGICAL_PATH]... \
  [--target-row-schema ROW_SCHEMA] \
  [--split-ratio-ppm 500000] \
  [--require-review]
```

Objectives and exact fields are:

| Objective | Fields |
| --- | --- |
| `full_text` | `text` |
| `continuation` | `prompt`, `completion` |
| `section_reconstruction` | `heading`, `section` |
| `before_after_transformation` | `before`, `after` |
| `structured_field` | `input`, `fields` |

The command makes no LLM call and has no `summary` objective.

Without `--source`, construction selects every current source. Repeat the
option to select an exact subset by source ID or logical path. Unknown or
duplicate selections fail closed.

`--target-row-schema` accepts `text`, `prompt_completion`,
`instruction_output`, or `messages`. It defaults to `text` for `full_text` and
`prompt_completion` otherwise. Full text requires `text`. Other objectives
require a supervised row schema.

`--split-ratio-ppm` applies only to continuation construction and must be from
1 through 999999. It controls the prompt and completion boundary. It is not the
later train and evaluation ratio.

By default, construction-integrity decisions accept valid candidates.
`--require-review` leaves them pending because the current CLI does not ingest
completed review evidence. The Python construction API supports separate
review values.

The command commits canonical `recipe` and `result` artifacts. Before commit,
the workspace reconstructs all selected upstream inputs and requires exact
semantic equality with fresh construction replay.

### `curate`

```text
veriformis curate WORKSPACE \
  [--minimum-target-characters 1] \
  [--balance-mode none|primary-source-cap] \
  [--maximum-records-per-primary-source COUNT] \
  [--evaluation-ratio-ppm 500000] \
  [--require-evaluation | --allow-empty-evaluation] \
  [--split-seed veriformis-v1] \
  [--instruction TEXT]
```

This command fixes the complete `FinishedDatasetPlan` and applies its curation
policy. Curation runs minimum target filtering, source-scoped conflict
quarantine, exact deduplication, optional primary-source cap, and coverage
closure in that order.

`--balance-mode none` is the default. `primary-source-cap` requires a positive
`--maximum-records-per-primary-source`. A maximum is invalid in `none` mode.

`--evaluation-ratio-ppm` is the requested partition ratio, from 1 through
999999. Evaluation is required by default. `--allow-empty-evaluation` permits a
sole leakage group to remain entirely in train. It does not force evaluation
empty when two or more groups exist.

`--split-seed` enters the deterministic group order. `--instruction` is
required only when the recipe selected `instruction_output`. It is rejected
for all other row schemas.

The command commits `plan` and `result`. It prints included, excluded, and
quarantined counts plus coverage blockers. A curation result with blockers
remains auditable, but later validation cannot pass.

### `split`

```text
veriformis split WORKSPACE
```

Split reads the plan fixed during `curate`. It has no policy options because a
second policy surface could contradict that plan.

Included records connect through shared source IDs, equal raw-source digests,
multi-source joins, and inherited exact-dedup-family relations. Complete
transitive components become indivisible leakage groups. Assignment is
deterministic from the bound ratio and seed. No group crosses partitions.

When evaluation is required, fewer than two groups fails with `split-invalid`.
The committed result records groups, assignments, requested and realized
counts, and an assignment digest.

### `format`

```text
veriformis format WORKSPACE
```

Format has no `--format` option. It reads the row schema from the bound recipe
and finished plan. It consumes construction records, curation decisions, and
authoritative assignments. It never projects chunks directly.

One included record produces one payload row and one provenance row. The
command commits:

- `row-set`, the strict semantic row-set artifact;
- `train`, payload-only training JSONL;
- `evaluation`, payload-only evaluation JSONL; and
- `provenance`, one combined aligned metadata stream.

`text` rows contain only `text`. Prompt-completion rows contain only `prompt`
and `completion`. Instruction rows contain only `instruction`, `input`, and
`output`. Message rows contain only the exact two-turn `messages` value.

Rows are sorted by record ID within each partition. Provenance is train first,
then evaluation, with zero-based partition ordinals and exact payload digests.

### `validate`

```text
veriformis validate WORKSPACE
```

Validate has no format option. It builds one exact snapshot and runs all 17
required gates in this order:

1. `construction-replay`
2. `record-lifecycle`
3. `curation`
4. `deduplication`
5. `quality`
6. `balance`
7. `coverage`
8. `split`
9. `leakage`
10. `row-binding`
11. `objective`
12. `schema`
13. `encoding`
14. `masking`
15. `partition-nonempty`
16. `aptus-row-shape`
17. `snapshot`

The command prints every gate status and finding, then the snapshot and
revision IDs. It commits `snapshot` and `report`. A valid failing report is
committed with failed stage status and the command exits 1.

`aptus-row-shape` proves only current schema shape. It does not prove Aptus
bundle intake or backend partition enforcement.

### `seal`

```text
veriformis seal WORKSPACE -o OUTPUT.vfbundle
```

For a fresh publication, the destination must not exist. Seal loads one current
complete revision, rebuilds the exact validation report, and requires equality
with the saved passing report. If an earlier attempt published the exact bundle
but failed before committing workspace receipts, a retry may recover only after
external-digest verification and byte-for-byte comparison. It never overwrites
the destination.

It publishes exactly:

```text
OUTPUT.vfbundle/
├── data/train.jsonl
├── data/evaluation.jsonl
├── metadata/row-provenance.jsonl
├── validation.json
├── manifest.json
└── attestation.json
```

Seal writes into a private temporary sibling, copies the validated payload
bytes without reserialization, writes the deterministic manifest and
attestation, syncs and independently verifies the temporary bundle, rechecks
the expected workspace revision, and atomically promotes the directory. It
then commits the exact manifest and attestation bytes as workspace receipts.

The command prints the bundle path, manifest SHA-256, verification grade, and
seal revision. Fresh internal publication verification reports
`self_consistent`. Exact receipt recovery reports `external_digest` because the
retry supplies the expected manifest digest. Retain the printed digest outside
the bundle when external binding matters.

Bundle promotion and receipt commit cannot share one atomic filesystem action.
If publication becomes visible but receipt commit fails, the command reports
the visible path and digest with the failure. It does not overwrite or claim
rollback.

### `verify`

```text
veriformis verify BUNDLE [--manifest-sha256 EXPECTED_SHA256]
```

The verifier uses only bundle bytes and the optional expected digest. It does
not read a workspace or trust producer state. It requires the exact file and
directory set, safe canonical paths, regular files, valid link policy, exact
sizes, digests, record counts, row and provenance alignment, a passing bound
validation report, and correct attestation binding.

It reports:

- `self_consistent` when all internal checks agree; or
- `external_digest` when those checks pass and the supplied expected manifest
  SHA-256 matches.

A co-located attestation alone never produces an external trust claim.

### `preview`

```text
veriformis preview PATH [--rules NAME,NAME] [--custom REGEX] [--source-root ROOT]
```

Preview parses one raw source or reads one workspace, creates the same
source-scoped cleaning plan used by clean, replays it, and prints transform
counts, removed byte counts, warnings, the plan ID, and before and after text
samples. It writes nothing.

Use `--source-root` to match the locator selected by parse. Given identical
locator, bytes, parser, rules, and configuration, raw preview, workspace
preview, and clean produce the same plan ID.

### `version`

```text
veriformis version
```

Prints `0.1.0`.

## Exit status

| Status | Meaning |
| --- | --- |
| `0` | Command completed |
| `1` | Validation failed, seal failed, verification failed, or required state for one of those commands was invalid |
| `2` | Unsupported input, invalid option, workspace failure, or another typed error from earlier stage commands |

Errors use `error[stable-code]: message` when a typed code exists.

## Deferred CLI work

Group 4 adds a typed `PipelineService`, converts this CLI into a thin adapter,
and proves the dual-objective M1.1 raw-source path through both direct API and
CLI. YAML automation remains later work.

## Related documentation

- [Product contract](product-contract.md)
- [Integrity Contract v1](contracts/integrity-v1.md)
- [Dataset Construction Contract v1](contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](contracts/finished-dataset-v1.md)
- [Current implementation status](current-status.md)
- [Architecture](architecture.md)
- [Development guide](development.md)
- [Build roadmap](plans/2026-07-29-veriformis-roadmap.md)
