# Phase 20 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-31

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 20; [program.json](../program.json); [project tracking policy](../../../../docs/governance/project-tracking.md). No desktop Phase 20 plan existed; this packet is derived from the roadmap Phase 20 section and the Phase 19 sequential-green-PR operating model.

**Predecessor:** Phase 19 closeout merged as PR #180 at
`084e504a799b6c1c1cc130c8ee819b13de5d6bbe`. Clean local `main` equaled
`origin/main` there when this packet opened.

Each numbered item is one sequential pull request. Every pull request must pass
focused tests, project tracking, Ruff, the lock check, `git diff --check`, the
core test suite, and every GitHub check, including both `install-smoke` copies
and both `project-spec-example` copies. Phase 20 does not change `macos/`
unless 20.6 is licensed by owner-signed evidence. Default: no Mac work.
GitHub remains the Python matrix; do not add an Xcode job. The pull request
then merges and leaves clean local `main` equal to `origin/main` before the
next item begins.

Phase 20 is the last independent-product roadmap phase. It does not invent a
Phase 21.

## Goal

Cut a supportable independent product whose claims are bounded by retained
evidence. The honest 1.0 is CLI-first. Unsupported candidates are excluded
rather than weakly claimed. The primary golden path contains no Aptus.

## Architecture

`PipelineService` owns policy. CLI and MCP are adapters. The frozen 1.0
support matrix is a read-only pin over the existing support registry and
implemented contracts. Loading a pin is not a new capability. A version or
maturity change is the last item, not the first.

## Locks

| ID | Lock |
| --- | --- |
| L1 | Sequential green PRs; packet opening is 20.1; closeout folds into 20.10. |
| L2 | Honesty only in 20.1. No matrix freeze, version bump, signed Mac, Hub, or lifecycle docs in 20.1. |
| L3 | Version stays `0.1.0` development alpha until 20.10 after the evidence index is complete. |
| L4 | Freeze only capabilities whose evidence gates passed. Exclude unsupported candidates rather than weakly claiming them. |
| L5 | Honest 1.0 is CLI-first independent core. Public signed/notarized Mac is not in the 1.0 matrix unless 20.6 produces owner-signed evidence. Default: skip with a record. |
| L6 | ADR-0020 Decision A stands. No Hub execute. Loading a publication pin is not upload. |
| L7 | ADR-0017 Decision A and ADR-0018 Decision A stand. No plugin loader. No generator. |
| L8 | Empty extras stay empty. Consumer-profile failure does not block core unless that profile is frozen into the 1.0 matrix at 20.8. |
| L9 | Default `review_policy` stays `none`. Quality stays preview-only. No quality-report command. No heuristic blocks seal. |
| L10 | Existing SFT, Phase 16, Phase 17, Phase 18, and Phase 19 goldens stay byte-identical. |
| L11 | PipelineService owns policy. CLI and MCP are adapters. No second catalog. No Swift policy. |
| L12 | Hosted training stays out of scope. Family-to-trainer chrome stays out of scope. GitHub xcodebuild stays out. |
| L13 | The primary golden path contains no Aptus. |
| L14 | Maturity/version change only in 20.10 after evidence. If evidence cannot support a 1.0 claim, keep `0.1.0` and freeze the matrix as alpha. |
| L15 | Phase 20 is the last independent-product roadmap phase. Do not invent a Phase 21 from this packet. |

## Checklist

### 20.1 Open the stable-1.0 packet

**Branch:** `phase20/01-stable-packet`

- [ ] Confirm Phase 19 complete and clean `main` at PR #180.
- [ ] Create the standard packet and move Phase 20 to `in_progress`.
- [ ] Record L1 through L15 and reconcile active tracking documents.
- [ ] Add isolation tests for the current release boundary.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

No support-matrix freeze, version bump, signed Mac, Hub execute, migration
guide, security report, or support-lifecycle document is permitted in this
item.

### 20.2 Freeze the 1.0 support matrix from evidence

**Branch:** `phase20/02-support-matrix`

- [x] Pin a versioned 1.0 support matrix over the current support registry
      and implemented contracts: platforms, Python, macOS claim, inputs,
      goals, semantic rows, containers, profiles, corpus tiers, and optional
      extras.
- [x] Name exclusions explicitly: Hub execute, public signed Mac, generator,
      plugin loader, Unsloth execute, default-parse `ocr-image`, published
      corpus tiers, quality-report command, hosted training.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 20.3 Complete migration paths

**Branch:** `phase20/03-migration-completeness`

- [x] Prove every supported workspace, bundle, mapping, recipe, export, and
      profile version still loads or has an `upgrade-workspace` path.
- [x] Publish an operator migration guide. Do not invent silent schema jumps.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 20.4 Run license, vulnerability, parser-threat, secret, reproducibility, and provenance review

**Branch:** `phase20/04-security-review`

- [x] Inventory declared licenses. Scan for secrets. Record the parser threat
      model. Prove artifact reproducibility and provenance for the Python
      path. Do not add a required cloud scanner or new runtime dependency.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 20.5 Retain clean-machine CLI evidence without Aptus

**Branch:** `phase20/05-clean-machine-cli`

- [x] Run the golden CLI path on a clean install. Retain logs, manifests,
      expected digests, exports, receipts, and verification reports. Primary
      path contains no Aptus.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 20.6 Skip signed Mac with a record

**Branch:** `phase20/06-signed-mac-skip`

- [ ] Public signed/notarized Mac is not in the 1.0 matrix. Skip with a
      record unless the owner supplies signed, notarized, stapled evidence
      in this item. Do not add GitHub xcodebuild.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 20.7 Inspect Python sdist and wheel artifacts

**Branch:** `phase20/07-python-artifacts`

- [ ] Build and inspect sdist and wheel. Install in supported environments.
      Golden compile uses only declared dependencies. Existing
      `install-smoke` remains a required CI job.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 20.8 Freeze consumer profiles as optional isolated adapters

**Branch:** `phase20/08-profile-freeze`

- [ ] Name accepted optional profiles and excluded candidates. Isolated
      profile jobs do not block core unless a profile is frozen into the
      1.0 matrix as required. Empty extras stay empty. The exporter does
      not train.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 20.9 Publish support-lifecycle documentation

**Branch:** `phase20/09-support-lifecycle`

- [ ] Semantic versioning, compatibility windows, upstream profile review
      cadence, deprecation notice, vulnerability response, and release
      rollback. User, mapping, goal, export, profile, troubleshooting,
      security, privacy, and migration docs stay honest to the frozen
      matrix.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 20.10 Change maturity/version only after evidence and close Phase 20

**Branch:** `phase20/10-version-and-closeout`

- [ ] Evidence index complete and reviewed. If the frozen matrix and
      retained gates support a CLI-first 1.0 claim, bump version and
      classifier with explicit Mac/Hub/generator/plugin non-claims. If
      they do not, keep `0.1.0` development alpha and say so.
- [ ] Adversarial closeout. Do not invent a Phase 21 from this packet.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

## Skip rules

| Item | Skip only when |
| --- | --- |
| 20.1–20.5, 20.7–20.10 | Do not skip. |
| 20.6 signed/notarized Mac | Skip with a record unless the owner supplies signed, notarized, stapled evidence in this item. Default skip. |
| Hub execute, generator, plugin loader, hosted training, quality-report command, GitHub xcodebuild, family-to-trainer | Forbidden / out of scope. Record at closeout. |
| Making empty extras required | Forbidden. |

## Exit gate

Every 1.0 claim links to a passing clean-machine, contract/conformance,
performance, security, or migration result. The primary golden path contains
no Aptus. Unsupported candidates are explicitly excluded rather than weakly
claimed. Version and maturity change only after that evidence exists.
