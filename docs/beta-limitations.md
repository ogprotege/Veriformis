# Veriformis Beta Limitations

**Status:** Active limitations register for any future **beta** cut of `0.1.0`

**Last reviewed:** 2026-09-02 (post-20 remainder honesty)

**Maturity today:** Development **alpha** — this document exists so a beta cut
can be honest. **Do not treat the current tag as beta** until the beta cut
checklist in [release.md](release.md) and the
[beta readiness audit](../dev/active/group-9-public-release/beta-readiness-audit.md)
are closed and the product is deliberately re-labeled.

This page is the non-negotiable “what we will not claim” list. It does not
replace contracts or [current status](current-status.md).

## Supported beta surface (intended CLI beta)

When a CLI beta is declared, support means:

| Area | Supported |
| --- | --- |
| Install | `pip` / `uv` wheel or editable checkout; console entry `veriformis` |
| Python | 3.11, 3.12, 3.13 |
| Host OS for CI-proven path | Ubuntu (matrix) and macOS (Python 3.12 job) |
| Product path | Offline local compile: parse → … → seal → verify |
| Optional Aptus integration | Sibling descriptor and consumer check for accepted row schemas; not part of core beta readiness |
| Determinism | Offline deterministic v1; no LLM generation in the pipeline |

Default **beta packaging choice:** **CLI-first**. The SwiftUI workbench under
`macos/` is a thin adapter for developers; a signed/notarized workbench is
**not** part of CLI beta unless the owner checklist in [release.md](release.md)
is completed and the beta announcement says so explicitly.

## Hard non-claims

These are permanent or deferred product boundaries. Beta does not soft-pedal them.

1. **No default-parse `ocr-image`.** Image-only PDFs still refuse. Optional
   Tesseract 5 exists under extra `ocr`, which stays empty. `ocr-preview` is
   not default parse.
2. **No network model generation.** The dataset pipeline does not call LLMs or
   remote generation services (Group 8 remains optional and owner-gated).
3. **No multi-user service, accounts, cloud, billing, or telemetry.**
4. **No “finished dataset” without seal + verify.** Intermediate clean state is
   not a handoff product unless a `full_text` recipe selects retained text as
   the construction target — and even then curation through seal still apply.
5. **No silent rewrite of split or curation by a consumer integration.** A
   consumer profile must not invent membership or replace Veriformis policy.
6. **No public-ready or production claim** without the full public checklist
   (especially signed/notarized Mac install evidence when claiming a Mac app).
7. **Quality-report is preview, not a gate.** `veriformis quality-report`
   emits `veriformis.quality-report/v1`. It does not block seal.
8. **Unsigned Debug xcodebuild is not a public Mac claim.** GitHub may run
   the Debug scheme with `continue-on-error`. `public_signed_mac` stays false.

## Operator limitations (beta-critical)

### Optional Aptus row schemas

This section applies only when the Aptus integration is explicitly selected.
It does not constrain standalone compile, seal, verification, or beta
readiness.

Current checked-in Aptus adapter policy:

- **Accepts:** `prompt_completion`, `instruction_output`, `messages`
- **Rejects:** plain `text`

Consequences:

- Objective **`full_text`** produces `text` rows. Seal and `external_digest`
  verify succeed. **`handoff-verify` is expected to reject** with
  `backend-rejects-row-schema:text`. That is contract-correct, not a compile bug.
- For Aptus-bound beta workflows, prefer **`continuation`** (or another recipe
  that yields an accepted supervised schema). See
  [Aptus Handoff Contract v1](contracts/aptus-handoff-v1.md).

Seal success **never** alone means “Aptus will train this.” The repository's
`handoff-verify` proves adapter self-conformance, not compatibility with a live
named Aptus build. A compatibility claim also requires retained evidence from
that exact external build.

### Inputs

Supported raw families include text, Markdown, DOCX, selected source code,
HTML, digitally-born PDF, CSV, JSON, and JSONL as documented in
[current status](current-status.md). Unsupported paths fail closed. Do not
assume every PDF is recoverable.

### Workspaces

- Physical layout schema 1; revision schema 3.
- Use `upgrade-workspace` for verified older revision schemas; do not hand-edit
  content-addressed objects or `HEAD`.
- Interrupting a stage is safe for durability rules already tested; do not
  treat a half-written external bundle path as sealed.

### Surfaces

| Surface | Beta expectation |
| --- | --- |
| CLI (`veriformis`) | Primary beta surface |
| `PipelineService` | Supported for embedders; same stage policy as CLI |
| MCP (`veriformis mcp`) | Local constrained adapter; not a multi-tenant server |
| SwiftUI workbench | Optional developer UI; requires Xcode/XcodeGen; unsigned unless owner-signed |
| Recipes / YAML | Deterministic named recipes and v1 pipeline specs only |

### Dependencies

The wheel currently installs runtime dependencies including PDF, YAML, and MCP
stacks even for pure CLI compile. That is accepted for alpha/early beta; a
slimmer extra split is a later packaging improvement, not a silent guarantee
of a minimal footprint today.

### Quality tooling not gated

Beta does **not** require mypy, coverage thresholds, or dependency CVE gates in
CI. Required automated gates are lockfile, Ruff (selected rules), core pytest
matrix, clean-wheel installed-CLI smoke, and standalone golden compile.
Optional adapter checks run separately and do not gate beta readiness. See
[development.md](development.md).

## Failure posture

Veriformis **fails closed** on unsupported input, malformed or stale state,
identity mismatch, evidence mismatch, and replay mismatch. Dense diagnostic
text is expected; treat non-zero exit as untrusted output.

## What “beta-ready” still requires

Closing this limitations page alone does **not** make a beta. Before any
beta label or external invite:

1. Green CI on `main` (matrix + install-smoke + golden-compile).
2. Retained clean-path evidence (wheel install + golden compile transcript).
3. This limitations page linked from the README maturity note.
4. Explicit support statement matching the table above.
5. Deliberate version/label decision (`0.1.0` alpha vs `0.1.0bN` vs “beta candidate”).

Public Mac app claims additionally require owner signing/notarization evidence
per [release.md](release.md).

## Related

- [Current implementation status](current-status.md)
- [Release guide](release.md)
- [Product contract](product-contract.md)
- [Aptus Handoff Contract v1](contracts/aptus-handoff-v1.md)
- [Beta readiness audit](../dev/active/group-9-public-release/beta-readiness-audit.md)
