# Veriformis macOS Workbench (Group 7 + private beta Phases 0–1)

SwiftUI desktop adapter for the Veriformis dataset compiler. On `main` this is
the **private beta** shell: compile (not convert) framing, KISS navigation, and
a run sheet with live log.

## Design

- **Thin adapter only.** The app shells to the `veriformis` CLI (`PipelineService`).
- **Same digests as CLI.** Stage order and flags match
  `VeriformisCLI.compilePlan`.
- **Sidebar:** Home / Compile / History / Settings.
- **Compile:** drag-and-drop sources, objective picker, output folder, sealed
  bundle + Aptus handoff.
- **Run sheet:** progress %, stage chips, expandable live log.

## Requirements

- macOS 14+
- Xcode 15+ (Xcode 26 tested in development)
- [XcodeGen](https://github.com/yonaskolb/XcodeGen)
- Python **3.11+** and [uv](https://docs.astral.sh/uv/) for the compiler backend
- A synced checkout (`uv sync` from the repo root at least once) so
  `.venv/bin/veriformis` exists, **or** `veriformis` on your PATH

> **GUI apps do not use your Terminal PATH.** Double-clicking the `.app` will
> not see tools that only exist via shell profile unless they live in a standard
> location (`~/.local/bin`, Homebrew) or the app finds the repo `.venv` / Debug
> embedded repo root.

## Build and run (private beta / dogfood)

**Recommended (one command):** builds Debug, kills old instances, opens the
correct app, and passes CLI paths via `open --env` (plain `export` + `open`
does **not** inject env into GUI apps on macOS):

```bash
# From the repository root — on branch with the workbench fix:
bash macos/scripts/run_workbench.sh
```

Manual equivalent:

```bash
uv sync
cd macos
xcodegen generate
xcodebuild -scheme Veriformis -configuration Debug \
  -derivedDataPath /tmp/veriformis-dd build
killall Veriformis 2>/dev/null || true
open --env "VERIFORMIS_CLI=$PWD/../.venv/bin/veriformis" \
     --env "VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT=$(cd .. && pwd)" \
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
export VERIFORMIS_CLI="$PWD/.venv/bin/veriformis"
export VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT="$PWD"
open /tmp/veriformis-dd/Build/Products/Debug/Veriformis.app
```

## Parity check

```bash
./macos/scripts/parity_check.sh
```

Runs the workbench stage sequence twice and asserts identical content-root,
assignment, partition digests, and manifest SHA-256.

## Exit gate

A user can complete raw sources → sealed `.vfbundle` (+ handoff) without the
terminal; digests match CLI.

## Private beta vision

Owner plan for KISS navigation, compile (not convert) framing, live run log,
and phased debugger UX:

[docs/plans/2026-08-06-private-beta-workbench.md](../docs/plans/2026-08-06-private-beta-workbench.md)

**Phase 1** (implemented): sidebar Home / Compile / History / Settings, run
sheet with progress % and live log, history persistence, settings for CLI and
default output:

[dev/active/private-beta-workbench/phase-1-design.md](../dev/active/private-beta-workbench/phase-1-design.md)

Operator install (CLI + workbench): [docs/install.md](../docs/install.md)

The workbench remains a thin CLI adapter. Success is a sealed dataset product,
not a multi-format file converter.

## Packaging and release

Local unsigned dry-run (not public-ready):

```bash
bash scripts/release/macos_package_local.sh
```

Signed distribution, notarization, and clean-Mac install evidence are
owner-executed steps documented in [docs/release.md](../docs/release.md).
