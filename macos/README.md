# Veriformis macOS Workbench

SwiftUI desktop adapter for the Veriformis dataset compiler. This is an unsigned development
app for version `0.1.0` alpha. It provides compile, mapping, review-packet, and
verified-export flows over the CLI, with a run sheet and live log.

## Design

- **Thin adapter only.** The app shells to the `veriformis` CLI (`PipelineService`).
- **Same digests as CLI.** Stage order and flags match
  `VeriformisCLI.compilePlan`.
- **Sidebar:** Home / Compile / Review / Exports / History / Settings.
- **Compile:** Compiler path (`document-source`, `dataset-row`, or `mixed`),
  Sources, Goal (catalog picker), mapping confirm-then-map on dataset-row,
  copyable CLI equivalent, and a sealed `.vfbundle`. Aptus is optional
  Integrations, not required. Unconfirmed mapping plans cannot compile.
  Family goals wait for a confirmed mapping that binds their schema.
- **Taxonomy help:** asynchronously loaded from `veriformis taxonomy`; the app
  does not maintain a second taxonomy help catalog.
- **Run sheet:** progress %, stage chips, expandable live log.

## Requirements

- macOS 14+
- Xcode 15+ (Xcode 26 tested in development)
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) only when regenerating the project or using the packaging script; normal Debug builds use the checked-in project
- Python **3.11+** and [uv](https://docs.astral.sh/uv/) for the compiler backend
- A synced checkout (`uv sync` from the repo root at least once) so
  `.venv/bin/veriformis` exists, **or** `veriformis` on your PATH

> **GUI apps do not use your Terminal PATH.** Double-clicking the `.app` will
> not see tools that only exist via shell profile unless they live in a standard
> location (`~/.local/bin`, Homebrew) or the app finds the repo `.venv` / Debug
> embedded repo root.

## Build and run locally

**Recommended (one command):** builds Debug, kills old instances, opens the
correct app, and passes CLI paths via `open --env` (plain `export` + `open`
does **not** inject env into GUI apps on macOS):

```bash
# From the repository root:
uv sync
./script/build_and_run.sh
```

The compatibility path `bash macos/scripts/run_workbench.sh` delegates to that
same script. Optional modes are `--verify`, `--debug`, `--logs`, and
`--telemetry`. GitHub may run an unsigned Debug `xcodebuild test` of this
scheme with `continue-on-error`. That job is not a public Mac claim.

Manual equivalent:

```bash
uv sync
xcodebuild -project macos/Veriformis.xcodeproj -scheme Veriformis -configuration Debug \
  -derivedDataPath /tmp/veriformis-dd CODE_SIGNING_ALLOWED=NO build
killall Veriformis 2>/dev/null || true
open -n --env "VERIFORMIS_CLI=$PWD/.venv/bin/veriformis" \
     --env "VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT=$PWD" \
     /tmp/veriformis-dd/Build/Products/Debug/Veriformis.app
```

Or open `Veriformis.xcodeproj` in Xcode and Run (⌘R) from this checkout.

On launch the **Log** panel should show `Workbench bootstrap…` then
`CLI ready: …`. If you still see a missing-CLI alert, read the bootstrap
diagnostic lines in that log (PATH, plist root, venv path).

### Development CLI resolution (order)

1. `VERIFORMIS_CLI` absolute path override  
2. `veriformis` on PATH **or** common install locations  
3. `<repo>/.venv/bin/veriformis` when the checkout root is known  
4. `uv run --directory <repo> veriformis` (`uv` from PATH or common locations)  

Repo root discovery: `VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT` env, Debug
Info.plist key (from `project.yml`), walk up from CWD, walk up from the `.app`.

```bash
# Optional explicit launch from Terminal (repo root):
open -n --env "VERIFORMIS_CLI=$PWD/.venv/bin/veriformis" \
  --env "VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT=$PWD" \
  /tmp/veriformis-dd/Build/Products/Debug/Veriformis.app
```

### CLI-backed taxonomy help

The workbench invokes the read-only `veriformis taxonomy` command
asynchronously and renders the returned implemented training families,
objectives, semantic rows, physical containers, consumer profiles, and loss
policies. Loading and unavailable states stay explicit; the app does not fall
back to a stale Swift taxonomy catalog. Run `veriformis taxonomy` in Terminal
to inspect the same JSON used by the help surface.

## Post-20 operation integrity

Source-drop callbacks collect file URLs under a lock and preserve provider
order. HTTP URLs cannot enter the file selection through a drop callback.
The CLI still owns collection and parser admission.

Every CLI operation belongs to the workbench process registry. Quit closes
launch admission, cancels compile, discovery, preflight, mapping, export, and
review tasks, and waits for their children and UI completions. Superseded
requests remain registered until their processes finish.

The launcher creates a new process group atomically with `posix_spawn`.
Cancellation sends TERM and then KILL after the grace interval. The leader
remains an unreaped child until the final group signal. Delayed timers cannot
signal after reaping. Remaining group members are terminated when the leader
exits, and both output pipes drain before completion. This covers descendants
that remain in the owned group; it does not supervise a hostile executable
that deliberately leaves that group.

Split, seal, and package use the versioned JSON receipts described in
[the CLI reference](../docs/cli.md#machine-receipts-for-workbench-commands).
Truncated stdout, an invalid digest, or a mismatched destination refuses a
successful workbench result. Logs remain diagnostics. Explicit chunk strategy,
size, and overlap reach both chunk and construct.

Catalog discovery preserves valid new objective and row-schema identifiers
and the CLI's ordering. Existing mapped-family choices still require mapping
confirmation. Unknown goals go through CLI preflight. The app's semantic row
verifier retains an explicit supported set and refuses unknown payload shapes.
Trust grades, overwrite policy, and admission statuses remain closed.

Local `run-history.json` uses a version-1 envelope. A legacy array is copied
byte-for-byte to `run-history.legacy-v0.json` before migration. Unknown versions,
unreadable history, conflicting backups, and files changed after loading are
preserved. The History view displays the failure and disables further history
writes for that session. This does not change compiler evidence schemas or
create a public Mac release claim.

## Parity check

```bash
./macos/scripts/parity_check.sh
```

Runs the workbench stage sequence twice and asserts identical content-root,
snapshot/report IDs, complete file bindings, and manifest SHA-256. It also
asserts that the default path writes no Aptus sibling.

The standalone launch smoke uses an explicit installed CLI path, builds the
checked-in Xcode project, launches a fresh process, confirms its PID, and then
cleans it up:

```bash
VERIFORMIS_CLI="$PWD/.venv/bin/veriformis" \
  bash macos/scripts/standalone_workbench_smoke.sh
```

This is functional build/launch evidence, not signing or notarization evidence.

## Supported operator flows and limits

Document-source Compile runs preflight and the complete compile, seal,
external-digest verify, and transport sequence. Use two independent sources
for a non-empty evaluation partition. For an intentionally single-group
compile, Recipe settings exposes Allow empty evaluation partition.

Dataset-row Compile detects and confirms a mapping for one selected row-source
file, previews it, and runs map through seal and verification. Ordinary
imported SFT rows use record-level leakage groups; advanced families apply
their own grouping rules. Mixed mode refuses fused document and row inputs.
Use the CLI for a confirmed plan bound to multiple imported source files.

Exports selects an existing sealed bundle and a new destination path. Even an
empty existing destination is refused. Dry-run exposes the plan and destination
tree; confirmation enables execute; Verify export checks against the source.
The app does not turn a self-consistent bundle into external evidence by
reading its own manifest. An external digest comes from the matching retained
compile result or selected history entry; other bundles can use the explicit
self-consistent policy.

Goal preview appears after document-source compilation. Mapping preview is the
imported-row preview. `quality-report` is available through CLI and Python for
both paths; this app has no quality-report dashboard. The Review screen wraps
packet exchange; completing required construction review still uses the CLI
`construct --review-packet` flow. Required imported-row review remains refused.

## Exit gate

A user can complete raw sources → sealed `.vfbundle` without the terminal;
digests match CLI. Optional consumer-integration artifacts have separate
evidence and do not define workbench success.

## Private beta vision

Owner plan for KISS navigation, compile (not convert) framing, live run log,
and phased debugger UX:

[docs/plans/2026-08-06-private-beta-workbench.md](../docs/plans/2026-08-06-private-beta-workbench.md)

**Phase 1** (implemented): sidebar Home / Compile / History / Settings, run
sheet with progress % and live log, history persistence, settings for CLI and
default output:

[dev/active/private-beta-workbench/phase-1-design.md](../dev/active/private-beta-workbench/phase-1-design.md)

**Phase 2** (implemented): failure stage/exit/log tail, copy digests, reveal
artifacts, re-run from History/last settings:

[dev/active/private-beta-workbench/phase-2-design.md](../dev/active/private-beta-workbench/phase-2-design.md)

Operator install (CLI + workbench): [docs/install.md](../docs/install.md)

The workbench remains a thin CLI adapter. Success is a sealed dataset product,
not a general-purpose file converter.

## Packaging and release

Local unsigned dry-run (not public-ready):

```bash
bash scripts/release/macos_package_local.sh
```

Signed distribution, notarization, and clean-Mac install evidence are
owner-executed steps documented in [docs/release.md](../docs/release.md).
