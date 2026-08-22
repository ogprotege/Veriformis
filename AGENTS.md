# AGENTS.md

Repository-specific guidance for coding agents. See `CLAUDE.md` for product
doctrine, architecture, and the authoritative commands/checks list. See
`README.md` and `docs/install.md` for the operator/contributor setup and the
full CLI surface.

## Cursor Cloud specific instructions

Veriformis is a local-first Python CLI (`veriformis`) managed by `uv`. The only
runnable product on this Linux cloud VM is the CLI; the SwiftUI macOS workbench
under `macos/` (`./script/build_and_run.sh`) requires Xcode/macOS and cannot be
built or run here.

- The dev environment has no long-running services. There is nothing to start;
  work by invoking the CLI directly (`uv run veriformis ...`).
- `uv` is installed at `~/.local/bin` and is on PATH for interactive/login
  shells (the installer added it to `~/.bashrc` and `~/.profile`). In a bare
  non-interactive shell it may be absent — if `uv` is not found, run
  `export PATH="$HOME/.local/bin:$PATH"` (or `. "$HOME/.local/bin/env"`) first.
- Standard commands (sync, lint, test, lock check) live in `CLAUDE.md` and
  `README.md`. The core test invocation is
  `uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"`; the
  `tests/handoff` suite and the `aptus_integration` marker are optional Aptus
  integration checks that are intentionally excluded from the core gates.
- The full core suite is filesystem-heavy. Timing varies widely by VM: it can
 run in ~90s on fast disks but has been observed to take ~11–12 minutes on
 slower cloud storage (~1878 tests). It is not hung — allow generous time. One
 test (`tests/bundle/test_defectclose_transport.py`) intentionally emits a
 `RuntimeWarning` about an unremovable staging link; that warning is expected
 and not a failure.
- End-to-end compile (`parse → clean → chunk → construct → curate → split →
  format → validate → seal → verify`) needs at least two independent sources to
  produce a non-empty evaluation partition under default split rules. With a
  single leakage group, pass `--allow-empty-evaluation` to `curate`.
- Output is deterministic: the same sources produce the same manifest SHA-256
  across runs. Retain the `manifest.json` digest (`sha256sum`) out of band to
  get an `external_digest` (rather than `self_consistent`) verification grade.
