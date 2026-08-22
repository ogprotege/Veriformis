# Phase 5 Evidence

**Status:** In progress — items 5.1–5.3 merged; item 5.4 locally admitted,
pull-request publication and merge pending

**Opened:** 2026-08-21

## Predecessor evidence

Phase 4 completed at `a76e0fe3185b0e317cd453b9c28a1d2054e617dd`.
Its [closeout](../phase-04-verified-export-foundation/closeout.md) records the
verified export foundation and its adversarial exit proof. Phase 5 reuses that
foundation; it does not restate Phase 4 evidence as proof of a shipped generic
container.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| The roadmap authorizes split JSONL as the first Phase 5 implementation candidate for all current row schemas | `source-verified` | Independent product roadmap, Phase 5 |
| Generic derivatives must remain downstream of the canonical verified bundle | `source-verified` | ADR-0004 and Verified Export Contract v1 |
| Safe publication, receipt replay, membership equality, and independent verification are available from Phase 4 | `source-verified` | Phase 4 packet and verified-export sources |
| At baseline `a76e0fe`, production discovery contains no renderer/replayer and generic containers remain planned | `source-verified` | Phase 4 closeout, support registry, and implementation catalog at the opening baseline |
| The existing deterministic archive transport is the only archive contract Phase 5 may integrate | `source-verified` | ADR-0005 and roadmap work item 5.4 |
| Item 5.3 merged as PR #55 at `c6d7fc13a09a` before item 5.4 began | `source-verified` | Git commit and Phase 5 progress record |
| ADR-0006 defines `deterministic-export-pack-zip-v1` as a receipt-anchored post-export wrapper while preserving ADR-0005 and the three export selectors | `source-verified` | ADR-0006 and deterministic archive contract |

## Required item 5.1 evidence

- [x] Strict configuration/profile parsing and durable identity fixtures.
- [x] Exact semantic row and logical-partition preservation for every current
      row schema.
- [x] Safe configurable filename, collision, traversal, Unicode/case-alias,
      and reserved-name refusal.
- [x] Optional provenance alignment, omission, mutation, and tamper proof.
- [x] Deterministic README/data-card and closed destination-tree proof.
- [x] Receipt, unexpected-file, source-digest, membership, and output-tamper
      failure evidence.
- [x] Discovery, dry-run, inspect, execute, and verify parity across Python,
      CLI, MCP, and the CLI-backed Mac bridge.
- [x] Import round-trip or equivalent semantic replay proving identical rows
      and partitions.
- [x] Required focused, full, release, tracking, lint, parity, Mac, and diff
      gates recorded with exact observed results.
- [x] Capability/support, current-status, evidence-index, and packet records
      reconciled after the behavior is proved.

## Required phase exit evidence

- [ ] Every supported row schema round-trips through every compatible generic
      container with identical semantic rows and logical partitions.
- [ ] Tampering fails verification for every supported container.
- [ ] Nested CSV is refused before publication with an actionable alternative.
- [x] Generic export-pack archives reuse the existing deterministic transport
      and verifier.
- [ ] Dry-run sample rows and destination trees match execution.
- [ ] Operator guidance separates container choice, training objective, and
      consumer compatibility.

## Required item 5.2 evidence

- [x] Strict canonical dataset and provenance object contract tests pass for
      all four current row schemas.
- [x] Exact ordered train/evaluation payloads and complete aligned provenance
      reload without semantic or partition change.
- [x] Count, schema, objective, loss-policy, row-set, split-result, alignment,
      payload, provenance, and closed-tree mutation fail verification.
- [x] Request v1 works across shared surfaces and request v2 fails before
      source or destination access because this container has no options.
- [x] Focused, full, release, tracking, lint, parity, Mac, and diff gates pass;
      exact observed results are recorded below.
- [x] Capability/support, current-status, evidence-index, and packet records
      agree before the pull request merges.

## Required item 5.3 evidence

- [x] The fixed CSV dialect, exact ordered headers, fixed tree, data card, and
      mandatory provenance formats are frozen by a versioned contract.
- [x] `text`, `prompt_completion`, and `instruction_output` preserve exact
      string fields, row order, and train/evaluation membership.
- [x] Nested `messages`, non-string values, empty fields, schema/count drift,
      malformed quoting, and provenance misalignment fail closed.
- [x] Configured request v2 fails before source or destination access. After
      source admission reveals unsupported `messages`, selection fails before
      destination access with an actionable split JSONL or canonical JSON
      alternative.
- [x] Request v1 discovery, planning, execution, verification, and Mac request
      parity retain the shared verified-export contracts.
- [x] Capability/support, current-status, tracking, and packet records are
      reconciled without claiming trainer or spreadsheet compatibility.

## Required item 5.4 evidence

- [x] The profile ID, `.vfexport.zip` suffix, external canonical-receipt
      digest, exact no-wrapper member set, deterministic ZIP encoding, and
      runtime-only archive receipt are frozen by ADR-0006 and the single
      deterministic archive contract.
- [x] Each of the three current generic export directories packages twice to
      identical archive bytes without changing its inner plan, receipt, file
      bindings, source trust grade, rows, ordering, or logical partitions.
- [x] Only `portable_exact_bytes` plans are admitted; source packaging and
      archive verification both refuse `semantic_content_only` until an exact
      profile-bound semantic replayer exists.
- [x] `package` and `package-verify` require exactly one manifest or export-
      receipt digest, select no profile by suffix, and retain legacy
      `.vfbundle.zip` bytes and behavior.
- [x] Missing, extra, duplicate, wrapper, traversal, alias, link, directory,
      comment, encryption, compression, metadata, size, CRC, receipt-anchor,
      member-digest, canonical-byte, target-inside-source, existing-target,
      cleanup, and durability-warning cases satisfy the frozen failure boundary.
- [x] Verification reconstructs only receipt-validated paths, streams member
      bytes under explicit limits, and reuses expected-plan export-directory
      verification without a general extraction operation.
- [x] Runtime output reports archive identity and embedded plan/receipt facts
      without adding a persisted schema, upgrading source trust, or calling the
      result source-bound.
- [x] Taxonomy and support identify a transport physical container while
      production export discovery remains exactly `split-jsonl-directory`,
      `json`, and `constrained-csv` v1.
- [x] Focused, required repository, legacy transport, governance, and
      independent-review results are observed and recorded before item 5.4 is
      called complete or published.
- [x] Documentation makes no trainer, consumer, MCP, Mac UI, signing,
      encryption, compression, remote-publication, or maturity claim.

## Observed results

The opening record above remains historical. The following results were
observed locally on the Phase 5.1 working tree based on
`a76e0fe3185b0e317cd453b9c28a1d2054e617dd`; raw runner logs were not retained.

| Evidence | Result | Grade | Limitation |
| --- | --- | --- | --- |
| Dedicated split JSONL contract | 45 passed | `recorded-local` | Container-specific fixtures, not the later Phase 5.5 consolidated matrix |
| Export/taxonomy/verified-contract integration | 288 passed at the focused gate | `recorded-local` | Later full run is the complete repository count |
| Full Python | 1,039 passed; one expected durability-warning regression warning | `recorded-local` | Local Python 3.12; CI supplies the matrix |
| Standalone release | 1,027 passed, 1 deselected; clean wheel and both golden compile/transport flows passed | `recorded-local` | Optional Aptus integration remains separate |
| macOS XCTest | 56 passed | `recorded-local` | Local unsigned Debug test build |
| CLI/workbench parity | PASS | `recorded-local` | Temporary artifacts were not retained |
| Governance and structure | Tracking, lock, Ruff, 15 JSON, 10 shell, 387 changed-document local links, and diff checks passed | `recorded-local` | Counts describe this working tree |

The recorded evidence above proves the admitted JSONL container, exact
membership and round-trip preservation, deterministic bytes, safe
configuration, and shared
surface behavior. Canonical JSON item 5.2 adds its separate fixed-tree contract
and implementation under the local evidence below. Constrained CSV item 5.3
then adds the flat-schema-only fixed tree described after the historical 5.2
record. None of these increments claims export-pack archives, shared Phase 5.5
fixtures, dry-run sample previews, trainer compatibility, scale, or Phase 5
completion.

### Item 5.2 observed results — 2026-08-22

| Evidence | Result | Grade | Limitation |
| --- | --- | --- | --- |
| Dedicated canonical JSON contract | 33 passed | `recorded-local` | Container-specific fixtures, not the later Phase 5.5 consolidated matrix |
| Export/taxonomy/verified-contract integration | 322 passed | `recorded-local` | Focused integration gate; full run is the complete repository count |
| Full Python | 1,073 passed; one expected transport durability-warning regression warning | `recorded-local` | Local Python 3.12; CI supplies the matrix |
| Standalone release | 1,061 passed, 1 deselected; clean wheel and both golden compile/external-digest/transport flows passed | `recorded-local` | Optional Aptus integration remains separate |
| macOS XCTest | 57 passed; `TEST SUCCEEDED` | `recorded-local` | Local unsigned Debug test build |
| CLI/workbench parity | PASS | `recorded-local` | Temporary artifacts were not retained |
| Governance and structure | Tracking, lock, Ruff, JSON validity, and diff checks passed | `recorded-local` | Final code, security, and documentation reviews found no blocker; GitHub remains |

The canonical tests cover all four current row schemas, the fixed exact-byte
tree, explicit partition/schema metadata, mandatory train-then-evaluation
provenance, source `RowSet` reconstruction and identity closure, request-v2
refusal, and mutation/tamper failure. Release, clean-wheel, golden, parity,
Mac, tracking, lock, lint, JSON, and diff gates passed. Final code, security,
and documentation reviews found no blocker. GitHub results remain separate
publication evidence.

### Item 5.3 local admission — 2026-08-22

The constrained-CSV contract and implementation freeze a fully quoted
UTF-8/LF codec for the three flat row schemas, exact ordered headers, separate
train and evaluation files, deterministic dataset-card and README sidecars,
mandatory train-then-evaluation provenance, and the shared receipt. Exact-byte
reload, payload/provenance binding, mutation and closed-tree checks, request-v1
surface parity, request-v2 refusal, and the actionable nested-`messages`
alternative are the admission boundary. The container claims neither trainer
nor spreadsheet compatibility and does not rewrite formula-like strings.

| Evidence | Result | Grade | Limitation |
| --- | --- | --- | --- |
| Dedicated constrained CSV contract | 47 passed | `recorded-local` | Container-specific fixtures, not the later Phase 5.5 consolidated matrix |
| Export/taxonomy/verified-contract integration | 371 passed | `recorded-local` | Full export surface plus taxonomy, verified-export, and tracking contracts |
| Full Python | 1,121 passed; one expected transport durability-warning regression warning | `recorded-local` | Local Python 3.12; GitHub supplies the 3.11–3.13 matrix |
| Standalone release | 1,109 passed, 1 deselected; clean wheel and both golden compile/external-digest/transport flows passed | `recorded-local` | Optional Aptus integration remains separate |
| macOS XCTest | 58 passed; `TEST SUCCEEDED` | `recorded-local` | Local unsigned Debug test build; the first sandboxed launch was retried outside the sandbox |
| CLI/workbench parity | PASS | `recorded-local` | Temporary artifacts were not retained |
| Governance and structure | Tracking, lock, Ruff, JSON validity, 437 scoped local Markdown links, and diff checks passed | `recorded-local` | Independent review found no executable blocker; two promotion-evidence blockers were corrected before publication |

The dedicated tests cover all three admitted flat schemas, independent literal
headers, exact quote-all bytes, embedded CR/LF/CRLF and Unicode, null and
empty-field distinctions, header-only evaluation, strict data-card/provenance
reconstruction, actionable `messages` and request-v2 refusal, repeated
rendering, every-file tamper, and closed-tree verification. Item 5.3 merged as
PR #55 at `c6d7fc13a09a` after this local record. The historical
counts above remain local evidence and are not rewritten as GitHub results.

### Item 5.4 local admission — 2026-08-22

Item 5.4 is implemented and locally admitted as the receipt-anchored
`.vfexport.zip` transport. The following results are local observations, not
GitHub results; pull-request publication and merge remain pending.

| Evidence | Result | Grade | Limitation |
| --- | --- | --- | --- |
| Dedicated export-pack suites | 66 passed | `recorded-local` | Focused transport, CLI, and adversarial coverage |
| Export/taxonomy/CLI integration | 448 passed | `recorded-local` | Integrated exports, taxonomy, verified-contract, Pipeline, CLI, and transport scope |
| Full Python | 1,195 passed; one intentional durability-warning regression warning | `recorded-local` | Local Python run; no GitHub matrix result is claimed |
| Standalone release | 1,183 passed, 1 deselected; lock, clean wheel, and both golden flows passed | `recorded-local` | Optional Aptus integration remains separate |
| CLI/workbench parity | PASS | `recorded-local` | No new Mac export-pack UI operation exists |
| macOS XCTest | 58 passed; `TEST SUCCEEDED` | `recorded-local` | Local unsigned Debug test build |
| Governance and structure | Tracking, Ruff, JSON validity, and diff checks passed | `recorded-local` | Scoped local reconciliation checks |
| Independent contract review | Found an all-three-container coverage gap and stale/exact-only records; both were corrected | `recorded-local` | Review findings were resolved before local admission |
| Independent code review | Found bundle-compatibility and archive path-stability blockers; both were corrected and re-reviewed clear | `recorded-local` | Clear re-review is local, not a GitHub review claim |

This evidence covers all three current exact-byte export directories,
`portable_exact_bytes`-only admission, the receipt-derived closed archive,
legacy bundle byte compatibility, path stability, tamper/refusal behavior, and
the unchanged three-renderer discovery boundary. Items 5.5–5.7 and the
phase-wide exit proof remain open.
