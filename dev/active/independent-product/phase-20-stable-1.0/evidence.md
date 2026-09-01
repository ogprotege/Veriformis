# Phase 20 Evidence

**Status:** Open

**Opened:** 2026-08-31

## Predecessor evidence

Phase 19 completed. Closeout merged as PR #180 at
`084e504a799b6c1c1cc130c8ee819b13de5d6bbe`. Clean local `main` equals
`origin/main` there. All declared dependencies (Phases 0–19) were complete
in `program.json`.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| Package version is `0.1.0` | `source-verified` | `src/veriformis/__init__.py` |
| PyPI classifier is `Development Status :: 3 - Alpha` | `source-verified` | `pyproject.toml` |
| Support-registry maturity is `development-alpha` | `source-verified` | `docs/governance/support-registry.json` |
| `PIPELINE_SCHEMA_VERSION` is `veriformis.pipeline/v1` | `source-verified` | `src/veriformis/recipes/pipeline_spec.py` |
| CLI and MCP names are disjoint from generator, install-extension, hub-upload, and quality-report | `source-verified` | CLI app; MCP tool manager |
| Package metadata has no `HF_TOKEN` | `source-verified` | `pyproject.toml` |
| Optional extras `trl`, `mlx-lm`, `columnar`, `axolotl`, `llama-factory`, `unsloth`, and `ocr` are empty | `source-verified` | `pyproject.toml` |
| Default `review_policy` is `none` | `source-verified` | `recipe_defaults()` |
| Quality gates remain `admitted_to_block is False` | `source-verified` | `src/veriformis/quality/gates.py` |
| Publication adapter `execute_allowed` is false | `source-verified` | `src/veriformis/publication/adapter.py` |
| GitHub workflows contain no `xcodebuild` | `source-verified` | `.github/workflows` |
| No 1.0 support-matrix contract exists yet | `source-verified` | `docs/contracts/` |
| Phase 19 closeout forbids starting Phase 20 from that packet | `source-verified` | Phase 19 `closeout.md` |

## Required item 20.1 evidence

- [x] Standard packet opened from clean `main` after Phase 19 closeout.
- [x] Phase 20 moved from `planned` to `in_progress` with this packet path.
- [x] L1 through L15 recorded.
- [x] Active tracking documents reconciled to Phase 20 in progress without
      claiming 1.0, a frozen matrix, signed Mac, or a version bump.
- [x] Baseline isolation tests added.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 20.2.

## Required item 20.2 evidence

- [x] Versioned `veriformis.support-matrix/v1` pin and contract document.
- [x] Loading is not a version bump. Product stays `0.1.0` development alpha.
- [x] Exclusions name Hub execute, public signed Mac, generator, plugin
      loader, Unsloth execute, default-parse `ocr-image`, published corpus
      tiers, quality-report command, hosted training, and required extras.
- [x] Python, CLI, and MCP emit the same catalog.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 20.3.

## Required item 20.3 evidence

- [x] Operator migration guide names workspace, bundle, mapping, recipe,
      export, and profile versions.
- [x] Revision 1 and 2 upgrade to 3; revision 4 is a no-op; unknown versions
      fail closed.
- [x] Pre-taxonomy workspace and `minimal-v1` bundle still load.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 20.4.

## Required item 20.4 evidence

- [x] License inventory: first-party MIT; extras empty; lockfile present.
- [x] Secret scan of src/scripts/examples; no Hub secrets in CI.
- [x] Parser threat model recorded; unknown suffix fails closed; OOXML
      disables entities and network.
- [x] Compile path has no network client. Publication execute stays false.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 20.5.

## Required item 20.5 evidence

- [x] Isolated wheel install of `veriformis-0.1.0`.
- [x] Golden compile through that CLI for `full_text` and `continuation`.
- [x] External-digest verify and transport accepted. Automatic Aptus
      handoff absent. No Aptus distribution in the venv.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 20.6.

## Required item 20.6 evidence

- [x] Skip record names signed/notarized/stapled Mac and no xcodebuild.
- [x] Support matrix `public_signed_mac` stays false.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 20.7.

## Required item 20.7 evidence

- [x] Sdist and wheel built and inspected. Version `0.1.0`. Console script
      present. Support matrix packaged. LICENSE in sdist. No binaries
      retained.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 20.8.

## Required item 20.8 evidence

- [x] Optional profiles frozen. Extras empty. Unsloth not executable.
      Isolated CI jobs continue-on-error. Exporter does not train.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 20.9.

## Required item 20.9 evidence

- [x] Support-lifecycle docs name semver, compatibility, profile cadence,
      deprecation, vulnerability response, and rollback. Operator docs
      stay honest to the frozen matrix. Version stays `0.1.0`.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [ ] Every GitHub check passes.
- [ ] PR merges and clean local `main` equals `origin/main` before 20.10.
