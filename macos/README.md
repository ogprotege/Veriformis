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
- Python package available as `veriformis` on `PATH`, or `uv` in a checkout

## Build

```bash
cd macos
xcodegen generate
xcodebuild -scheme Veriformis -configuration Debug build
```

Open `Veriformis.xcodeproj` after generation.

### Development CLI resolution

1. `VERIFORMIS_CLI` absolute path override  
2. `veriformis` on `PATH`  
3. `uv run --directory <repo> veriformis` when a repo root is found  

## Parity check

```bash
./macos/scripts/parity_check.sh
```

Runs the workbench stage sequence twice and asserts identical content-root,
assignment, partition digests, and manifest SHA-256.

## Exit gate

A user can complete raw sources → sealed `.vfbundle` (+ handoff) without the
terminal; digests match CLI.
