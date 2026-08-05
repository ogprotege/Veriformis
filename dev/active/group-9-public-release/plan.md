# Group 9 Public Release Gates Plan

**Status:** Automated gates implemented; owner Mac remainder open

**Roadmap scope:** Step 26

## Outcome

Establish supported-platform CI, package-install smoke, golden raw-corpus
compile/verify/handoff evidence, release documentation, and a macOS packaging
runbook. Signing and notarization require owner Apple Developer credentials and
are documented as manual release states, not silent skips.

## Fixed decisions

1. CI matrix: Python 3.11, 3.12, 3.13 on Ubuntu; optional macOS Python job.
2. Every PR runs `uv lock --check`, Ruff, pytest, wheel build + install smoke,
   and golden-corpus compile through external_digest + handoff-verify.
3. `scripts/release/` owns reproducible local/CI smoke entry points.
4. macOS app packaging scripts produce an unsigned/local-signed archive path;
   notarization is a documented owner step with recorded evidence.
5. Migration verification remains covered by existing revision migration tests
   in the ordinary suite.
6. Do not claim public release readiness until the documented release checklist
   is executed with recorded evidence on a clean Mac.

## Exit gate (product)

A clean supported Mac can install the product, compile the golden raw corpus,
verify final bundles, and hand them to a compatible Aptus release with
independently recorded evidence. Automated gates prove the installable Python
path and golden corpus; signed/notarized Mac distribution is the owner-executed
checklist.
