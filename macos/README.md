# Veriformis macOS Workbench (Group 7)

SwiftUI desktop adapter for the Veriformis dataset compiler.

## Design

- **Thin adapter only.** The app shells to the `veriformis` CLI (`PipelineService`).
- **Same digests as CLI.** Stage order and flags match
  `VeriformisCLI.compilePlan`.
- **Drag-and-drop sources**, objective picker, output folder, live log,
  sealed bundle + Aptus handoff reveal.

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

```bash
# From the repository root — once per machine / after dependency changes:
uv sync

cd macos
xcodegen generate
xcodebuild -scheme Veriformis -configuration Debug \
  -derivedDataPath /tmp/veriformis-dd build
open /tmp/veriformis-dd/Build/Products/Debug/Veriformis.app
```

Or open `Veriformis.xcodeproj` in Xcode and Run (⌘R) from this checkout.

On launch the log should show `CLI ready: …`. If you see **Could not locate the
veriformis CLI**, complete `uv sync` and relaunch a **Debug** build from this
repo (or set the overrides below).

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

The workbench remains a thin CLI adapter. Success is a sealed dataset product,
not a multi-format file converter.

## Packaging and release

Local unsigned dry-run (not public-ready):

```bash
bash scripts/release/macos_package_local.sh
```

Signed distribution, notarization, and clean-Mac install evidence are
owner-executed steps documented in [docs/release.md](../docs/release.md).
