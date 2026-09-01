# Phase 20 Closeout

**Status:** Complete

**Last reviewed:** 2026-09-01

## Exit-gate judgment

Passed. The frozen CLI-first support matrix, migration, security,
clean-machine CLI evidence, signed-Mac skip, Python artifacts, optional
profiles, and support-lifecycle docs are complete.
Version remains `0.1.0` development alpha.
A `1.0.0` tag would rewrite sealed bundle identities and the Phase 19
project-spec fingerprint because manifests bind `veriformis_version`.
Existing SFT, Phase 16, Phase 17, Phase 18, and Phase 19 goldens stay byte-identical.
L14 keeps `0.1.0` when a version claim cannot be made without that rewrite.
The frozen matrix claim stays `cli-first-independent-core`.
Do not invent a Phase 21 from this packet.

## Delivered scope

- 20.1 packet and honesty locks. Isolation tests. PR #181.
- 20.2 CLI-first support-matrix pin. Not a version bump. PR #182.
- 20.3 operator migration guide. Unknown versions fail closed. PR #183.
- 20.4 license, parser-threat, secret, and provenance review. PR #184.
- 20.5 clean-machine CLI evidence without Aptus. PR #185.
- 20.6 signed Mac skipped with a record. PR #186.
- 20.7 sdist and wheel inspect. Binaries not retained. PR #187.
- 20.8 optional profiles frozen and isolated. PR #188.
- 20.9 support-lifecycle and troubleshooting docs. PR #189.
- 20.10 evidence reviewed; version retained; adversarial closeout.

## Exclusions

Public signed Mac. Hub execute. Generator. Plugin loader. Unsloth
execute. Default-parse `ocr-image`. Published corpus tiers.
Quality-report command. Hosted training. Required trainer extras.
GitHub xcodebuild. A `1.0.0` version tag. Phase 21.

## Remaining debt

Signed and notarized Mac remains the Group 9 owner remainder. A later
operator license that supersedes ADR-0020 Decision B would be required
before Hub execute. A later item that is allowed to rewrite sealed
identities would be required before a `1.0.0` tag.

Do not invent a Phase 21 from this packet.
