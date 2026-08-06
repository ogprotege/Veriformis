# Veriformis Release Guide (Group 9)

**Status:** Active release-gate documentation for version `0.1.0` development alpha

**Last reviewed:** 2026-08-06 (Group 9 + beta-prep on `main` via PRs #14–#16)

**Next review:** Any public-release claim, packaging change, or CI gate change

This document defines the public release gates for Veriformis. Automated gates
prove the installable Python path and the golden raw-corpus compile. Signed and
notarized Mac distribution requires owner Apple Developer credentials and
recorded evidence. **Do not claim public release readiness until the full
checklist below has been executed with retained evidence on a clean Mac.**

Operator non-claims and any future **beta** cut criteria:
[beta-limitations.md](beta-limitations.md).

## What automated gates prove

| Gate | How | Evidence |
| --- | --- | --- |
| Lockfile integrity | `uv lock --check` | CI `test` job |
| Lint | `uv run ruff check src tests` | CI `test` job |
| Full suite | `uv run pytest -q` | CI matrix Python 3.11–3.13 (Ubuntu) + macOS 3.12 |
| Installable package | `scripts/release/smoke_install.sh` | CI `install-smoke` job |
| Golden product path | `scripts/release/golden_compile.sh` | CI `golden-compile` job + optional evidence artifact |
| Workspace migration | Ordinary pytest under `tests/regressions/` | Full suite (not a separate silent skip) |

## What automated gates do **not** prove

- Developer ID signing of the macOS workbench
- Apple notarization or staple
- Install of a signed/notarized `.app` on a clean Mac outside the developer machine
- Compatibility with a specific external Aptus release binary beyond handoff schema verify
- Type-check, coverage thresholds, or dependency audit as hard gates (optional follow-ups)

Those remain owner-executed checklist items.

## Local release smoke (Python)

From a clean checkout:

```bash
# One-shot local parity with automated gates (recommended before push):
bash scripts/release/check_local.sh

# Or step-by-step:
uv sync --extra test
uv lock --check
uv run ruff check src tests
uv run pytest -q
bash scripts/release/smoke_install.sh
bash scripts/release/golden_compile.sh
```


Optional: set `GOLDEN_EVIDENCE_DIR=/path/to/dir` when running
`golden_compile.sh` to retain per-objective evidence files.

After a wheel install, the golden path can use the installed CLI:

```bash
export VERIFORMIS_USE_PATH=1
bash scripts/release/golden_compile.sh
```

To retain a clean-path evidence pack (logs + digests only):

```bash
bash scripts/release/record_clean_path_evidence.sh
```

Packs land under `dev/active/group-9-public-release/evidence/` by default.

### Workspace upgrades (beta operators)

Workspaces use physical layout schema 1 and revision schema 3. If you open an
older verified workspace, run:

```bash
veriformis upgrade-workspace WORKSPACE
```

Do not hand-edit content-addressed objects or `HEAD`. Migration behavior is
covered by ordinary suite tests under `tests/regressions/`.

## Golden corpus

Source set: `tests/fixtures/acceptance/v1/raw/corpus/` (text, markdown, code).

Objectives (M1.1 acceptance):

1. `full_text` → seal → `verify --manifest-sha256 …` (`external_digest`);
   Aptus handoff is written but consumer verification is expected to report
   `backend-rejects-row-schema:text` (current Aptus MLX rejects plain text rows).
2. `continuation` (split ratio 400000 ppm) → seal → external_digest verify →
   `handoff-verify` with `status: accepted`.

Adversarial fixtures under `raw/adversarial/` are not part of the golden
release compile; they remain regression fixtures for cleaning and refusal paths.

## macOS workbench packaging

### Local unsigned dry-run (automated-capable)

On a developer Mac with Xcode and XcodeGen:

```bash
bash scripts/release/macos_package_local.sh
```

Produces under `dist/macos/`:

- a local archive / unsigned zip
- `RELEASE_STATE.json` with `signing: none`, `notarization: not-attempted`,
  and `public_release_ready: false`

This script intentionally does **not** claim a shippable public Mac product.

### Owner-executed signed + notarized path

Requires:

- Apple Developer Program membership
- Developer ID Application certificate in the login keychain
- App-specific password or API key for notarytool / `asc`
- Bundle identifier and Team ID configured for the Veriformis workbench

Recommended sequence (adjust names to the team’s cert and profile):

1. **Generate project**

   ```bash
   cd macos && xcodegen generate
   ```

2. **Archive with Developer ID signing** (do not use `CODE_SIGNING_ALLOWED=NO`)

   ```bash
   xcodebuild \
     -scheme Veriformis \
     -configuration Release \
     -archivePath dist/macos/Veriformis.xcarchive \
     archive
   ```

3. **Export / notarize** using the team’s preferred tool:

   - Apple `notarytool` + `stapler`, or
   - the repository-adjacent `asc` notarization workflow if configured for this
     product

4. **Staple** the notarization ticket to the exported `.app` or `.dmg`/`.zip`.

5. **Gatekeeper check** on a clean Mac (or a secondary account without
   developer tools):

   ```bash
   spctl --assess --type execute -v /path/to/Veriformis.app
   xcrun stapler validate /path/to/Veriformis.app
   ```

6. **Functional install proof** on that clean Mac:

   - launch the workbench or use the installed `veriformis` CLI
   - compile the golden corpus (or run `scripts/release/golden_compile.sh` with
     `VERIFORMIS_USE_PATH=1`)
   - retain `verify` external_digest output and `handoff-verify` `status: accepted`

7. **Aptus handoff evidence** (when a compatible Aptus build is available):

   - record Aptus version / commit
   - import the sealed bundle via the handoff descriptor
   - retain acceptance or failure logs; do not claim handoff success without logs

Record all of the above in a dated evidence note (path and SHA-256 of the
distributed artifact, notarization submission id, staple result, clean-Mac
command transcript).

### Honest release state

| State | Meaning |
| --- | --- |
| `local-unsigned` | Dry-run archive only |
| `signed-not-notarized` | Developer ID applied; not yet notarized |
| `notarized` | Notarized and stapled; Gatekeeper assess passes |
| `public-ready` | Notarized install + golden compile + handoff evidence retained |

Only `public-ready` with retained evidence supports a public release claim.

## Public release checklist

Copy this list into a dated release evidence file when attempting a ship.

### Automated (required green)

- [ ] CI matrix green on Python 3.11, 3.12, 3.13 (Ubuntu)
- [ ] CI macOS Python 3.12 job green (when enabled)
- [ ] `uv lock --check` green
- [ ] Ruff and full pytest green
- [ ] `scripts/release/smoke_install.sh` green
- [ ] `scripts/release/golden_compile.sh` green with both objectives
- [ ] Workspace migration regressions remain in the ordinary suite

### Owner Mac distribution (required for public Mac claim)

- [ ] Developer ID signed workbench archive
- [ ] Notarization accepted by Apple
- [ ] Staple validated
- [ ] Gatekeeper assessment passes on a clean Mac
- [ ] Golden corpus compile + external_digest verify + handoff-verify on that Mac
- [ ] Aptus-compatible handoff proof (or explicit deferral documented, not silent)

### Documentation honesty

- [ ] `docs/current-status.md` does not claim public readiness until this checklist is done
- [ ] Version and changelog (if published) match the shipped artifact digests
- [ ] Unsupported capabilities (OCR, cloud, LLM generation) remain non-claims

## Version and packaging notes

- Package name: `veriformis` (setuptools `src/` layout)
- Dynamic version: `veriformis.__version__` (currently `0.1.0`)
- Entry point: `veriformis = veriformis.cli:main`
- Build: `uv build` (wheel/sdist)
- Optional test extra: `uv sync --extra test`

Bumping a public version requires a deliberate version change, green automated
gates, and (for Mac binary claims) owner checklist evidence.

## Related docs

- [Current implementation status](current-status.md)
- [Development guide](development.md) (contributor checks and CI description)
- [macOS workbench](../macos/README.md)
- [Aptus Handoff Contract v1](contracts/aptus-handoff-v1.md)
- [Build roadmap Step 26](plans/2026-07-29-veriformis-roadmap.md)
