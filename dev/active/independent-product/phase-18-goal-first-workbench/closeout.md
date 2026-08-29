# Phase 18 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-29

## Exit-gate judgment

Passed. The goal-first Mac workbench is a thin CLI adapter over
`PipelineService`. A first-time test user can add sources, choose a
goal, compile a sealed independently verified `.vfbundle`, export a
generic derivative, and optionally wrap review packets without Aptus or
the terminal. Document-source, dataset-row, and mixed are the compiler
paths. Mapping is confirm-then-map. Export always shows the source
bundle and receipt. Default `review_policy` stays `none`. Swift owns no
dataset policy. ADR-0017, ADR-0018, and ADR-0019 Decision A stand.
Existing SFT, Phase 16, and Phase 17 goldens stay unchanged. Do not
start Phase 19 from this packet.

## Usability criteria

| ID | Judgment | Evidence |
| --- | --- | --- |
| Thin adapter | Pass | ADR-0019; `veriformis.workbench-adapter/v1`; Swift is a process adapter |
| Goal-first IA | Pass | Home/Compile copy; Aptus optional Integrations; copyable CLI equivalent |
| Compiler paths | Pass | ADR-0010 `document-source`, `dataset-row`, `mixed`; mixed fused refused |
| Confirm-then-map | Pass | Detect does not confirm; unconfirmed plans cannot compile |
| Inspectable settings | Pass | Preset and goal contract bind; overrides stay explicit |
| Pre-publication samples | Pass | ResultView samples; quality preview-only; no renderer |
| Export | Pass | Discover, dry-run, inspect, operator-confirmed execute, verify; generic first |
| Review | Pass | review-export/import/submit; default `none`; corrections are new identities |
| Accessibility | Pass | Labels, keyboard, copyable CLI; English v1 |
| No second catalog | Pass | Shared-service catalog; loading a pin is not execute |
| No Phase 19 | Pass | Packet and ledger forbid starting Phase 19 |

## Delivered scope

- 18.1 packet and workbench isolation.
- 18.2 ADR-0019 Decision A and `veriformis.workbench-adapter/v1`.
- 18.3 goal-first Home/Compile copy and CLI equivalent.
- 18.4 ADR-0010 modes and confirm-then-map.
- 18.5 inspectable preset and goal contract.
- 18.6 pre-publication samples; quality preview-only.
- 18.7 Exports wrap; generic containers first; named profiles only for admitted schemas.
- 18.8 Review wrap; default `review_policy` none.
- 18.9 accessibility, keyboard, CLI equivalents. Virtualization and full localization skipped.
- 18.10 adversarial refusals and closeout.

## Exclusions

Family-to-trainer mapping UI. Generator UI. Plugin UI. Hub upload.
Signed/notarized public Mac. GitHub xcodebuild job. Virtualization.
Full localization. Compile-path generator. Untrusted loader. Phase 19
publication.

## Remaining debt

Signed and notarized Mac remains the Group 9 owner remainder and is
outside this packet. Family-to-trainer chrome waits for independently
admitted adapters. A later phase may propose Decision B for a narrow
offline generator only with a new ADR that supersedes ADR-0018. Public
plugins wait for a new ADR that supersedes ADR-0017.

## Skip record

Family-to-trainer mapping UI is skipped because Phase 17 did not pin
those adapters. Generator UI is skipped under ADR-0018 Decision A.
Plugin UI is skipped under ADR-0017 Decision A. Hub upload is skipped
as out of scope. Signed/notarized Mac remains the Group 9 owner
remainder. GitHub xcodebuild is not licensed. Virtualization is skipped
because source lists have no measured bottleneck. Full localization is
skipped: English v1 (`developmentRegion = en`). Same honesty as Phase
15.5–15.8, the 16.10 public-plugin skip, and the 17.10 generator skip.

Do not start Phase 19 from this packet.
