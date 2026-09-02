# Post-20 Claim Honesty

**Status:** Remainder packet. Not a roadmap phase.

**Opened from:** Phase 20 closeout at `7a776ca` / PR #190.

This is a new remainder packet after independent-product Phase 20. It is
not Phase 21. Do not invent a Phase 21 from this packet or from the
Phase 20 packet.

Phase 20 closed on 2026-09-01 at `7a776ca` (`Merge pull request #190`).
Version remains `0.1.0` development alpha. The frozen claim is
`cli-first-independent-core`.

Hosted training and required trainer extras are out of product. Hub
execute, generator, and plugin loader stay behind ADR Decision B
(ADR-0020, ADR-0018, ADR-0017). This packet does not supersede those
ADRs. It does not train, add extras, bump the version, start Hub,
generator, plugins, or default-parse `ocr-image`.

Authorized remainder items:

- A thin `veriformis quality-report` CLI over the existing Python
  preview. That command is preview, not a gate.
- Unsigned Debug `xcodebuild` on GitHub only. The job builds and tests
  the same Debug scheme `./script/build_and_run.sh` uses, with
  `continue-on-error` so it cannot fail the independent compiler. This
  is not a public Mac claim. `public_signed_mac` stays false. No signing
  secrets, notarize, or staple.

This packet also holds docs honesty: live copy must not treat Phase 20
as the current critical path.
