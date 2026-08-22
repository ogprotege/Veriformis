# Phase 5 Evidence

**Status:** Complete — items 5.1–5.6 merged; item 5.7 operator guidance and
Phase 5 closeout locally admitted without claiming its own pull-request result

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
| Item 5.4 merged as PR #56 at `499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8` before item 5.5 began | `source-verified` | Git commit and Phase 5 progress record |
| Item 5.5 merged as PR #57 at `c72b8e9ec7bc2746d74404226aa086d497e15db1` before item 5.6 began | `source-verified` | Git commit and Phase 5 progress record |
| Item 5.6 passed all 14 GitHub checks and merged as PR #58 at `cd017941090c7352cb1d10f9a383042b954d4f2e` before item 5.7 began | `source-verified` | GitHub pull-request state, Git commit, and Phase 5 progress record |

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

- [x] Every supported row schema round-trips through every compatible generic
      container with identical semantic rows and logical partitions.
- [x] Tampering fails verification for every supported container.
- [x] Nested CSV is refused before publication with an actionable alternative.
- [x] Generic export-pack archives reuse the existing deterministic transport
      and verifier.
- [x] Dry-run sample rows and destination trees match execution.
- [x] Operator guidance separates container choice, training objective, and
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

## Required item 5.5 evidence

- [x] A frozen fixture defines explicit train and evaluation payloads for all
      four current row schemas and pins its canonical SHA-256.
- [x] Discovery closure proves exactly 11 compatible current
      container/schema pairs and the sole constrained-CSV/`messages` negative.
- [x] Every positive case materializes production-rendered bytes as ordinary
      files and strictly reloads separate ordered train and evaluation rows,
      aligned provenance, and the exact source `RowSet` and `row_set_id`.
- [x] Split JSONL uses a strict independent test loader; canonical JSON uses its
      strict contract models plus independent `RowSet` reconstruction;
      constrained CSV uses its exact contract loader rather than the ingest
      recovery parser.
- [x] The incompatible CSV case refuses before publication, leaves the
      destination absent, and names split JSONL v1 and canonical JSON v1.
- [x] One canonical semantic payload tamper per current container fails strict
      reload while exhaustive file/member tampering remains in each container's
      dedicated suite.
- [x] Focused, integrated, full, release, parity, Mac, tracking, lock, lint,
      structured-file, diff, and independent-review gates pass without adding
      a production importer, replayer, public surface, persisted schema,
      taxonomy entry, or support claim.

## Required item 5.6 evidence

- [x] Strict response-v2 and `veriformis.export-dry-run-preview/v1` contract
      tests pin exact fields, literals, ordering, and bounded canonical bytes.
- [x] Every current container and row schema produces ordinal-zero samples for
      each non-empty partition in train-then-evaluation order, with exact
      decoded payload values and canonical digest/byte-size metadata.
- [x] Empty evaluation yields no evaluation sample; payloads over 65,536 bytes
      and payloads excluded by the response budget are omitted whole with the
      exact closed reason and are never truncated or rewritten.
- [x] The sorted root-relative destination tree equals plan-derived parent
      directories and planned files plus `export-receipt.json`; no absolute,
      staging, temporary, or undeclared path appears.
- [x] Preview uses the same admitted source, strict `RowSet`, plan identity,
      profile, and container options as execute, without invoking a renderer or
      accessing, creating, publishing, or mutating a destination.
- [x] Python, CLI, MCP, and CLI-backed Mac dry-run responses are canonically
      identical; non-dry-run response-v1 behavior remains unchanged.
- [x] Dedicated, integrated, full, standalone release, parity, Mac, tracking,
      lock, lint, structured-file, diff, and independent-review gates pass with
      exact observed results recorded before item 5.6 is locally admitted.
- [x] Active documentation and evidence records agree that no persisted model,
      request/discovery schema, selector, taxonomy entry, support state,
      renderer, consumer profile, or trainer claim changed.

## Required item 5.7 evidence

- [x] One discoverable operator guide explains when to choose split JSONL,
      canonical JSON, or constrained CSV using only shipped contract claims.
- [x] The guide separates training objective, semantic row schema, physical
      container, and named consumer profile as distinct decisions.
- [x] The exact compatibility matrix is preserved: JSONL and JSON admit all
      four current row schemas; constrained CSV admits the three flat schemas
      and refuses nested `messages` with both JSON alternatives.
- [x] The guide preserves train/evaluation separation, payload/provenance
      separation, the canonical-bundle authority, source-bound export
      verification, and receipt-anchored optional transport.
- [x] README, install, CLI, documentation index, status, product, architecture,
      governance, WIP, program, support, evidence, and packet records agree.
- [x] Support registry semantics remain unchanged: the three shipped generic
      containers retain null consumer profiles and no trainer compatibility.
- [x] Required repository, structured-file, local-link, diff, and independent
      documentation-review gates pass with exact observed results recorded
      before local closeout is called complete.

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

Item 5.4 was implemented and locally admitted as the receipt-anchored
`.vfexport.zip` transport. The following results remain local observations,
not GitHub results. Item 5.4 subsequently merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`.

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
the unchanged three-renderer discovery boundary.

### Item 5.5 local admission — 2026-08-22

Item 5.5 was locally admitted as a frozen, discovery-closed conformance fixture
and subsequently merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1`. The following results remain local
observations, not GitHub results.

| Evidence | Result | Grade | Limitation |
| --- | --- | --- | --- |
| Dedicated semantic round-trip matrix | 16 passed | `recorded-local` | Test-only conformance proof, not a production importer or replayer |
| Export/taxonomy/verified-contract/tracking integration | 453 passed | `recorded-local` | Covers the shared export surface and consolidated matrix |
| Full Python | 1,211 passed; one intentional durability-warning regression warning | `recorded-local` | Local Python run; no GitHub matrix result is claimed |
| Standalone release | 1,199 passed, 1 deselected; lock, clean wheel, and both golden flows passed | `recorded-local` | Optional Aptus integration remains separate |
| CLI/workbench parity | PASS | `recorded-local` | Item 5.5 adds no CLI, MCP, or Mac operation |
| macOS XCTest | 58 passed; `TEST SUCCEEDED` | `recorded-local` | Local unsigned Debug test build |
| Governance and structure | Tracking, lock, Ruff, fixture/evidence JSON validity, and diff checks passed | `recorded-local` | Documentation-only reconciliation followed the executable gates |
| Independent adversarial review | No blockers; focused 16-test result reproduced | `recorded-local` | Review is local, not a GitHub review claim |

The matrix covers split JSONL and canonical JSON across `text`,
`prompt_completion`, `instruction_output`, and `messages`, plus constrained
CSV across the three flat schemas: 11 positive pairs total. It also covers the
sole constrained-CSV/`messages` refusal. Each positive case writes ordinary
files, reloads separate ordered train/evaluation payloads and complete aligned
provenance, and reconstructs the exact source `RowSet` identity. The fixture
includes comma, quote, tab, NUL, CR/LF/CRLF, formula-looking, NFC/NFD, and
non-BMP strings. One semantic tamper per container fails. At that historical
5.5 checkpoint, items 5.6–5.7 remained open; item 5.6 is locally admitted in
the section below, while item 5.7 operator guidance remains open.

### Item 5.6 local admission — 2026-08-22

The runtime preview implementation and its required evidence passed locally on
the item 5.6 working tree based on
`c72b8e9ec7bc2746d74404226aa086d497e15db1`. These observations are local; no
GitHub, publication, merge, or clean-main synchronization result is claimed.

| Evidence | Result | Grade | Limitation |
| --- | --- | --- | --- |
| Preview/API/adapter focus | 60 passed | `recorded-local` | Runtime transport proof, not persisted export evidence |
| Export/taxonomy/verified-contract/tracking integration | 480 passed | `recorded-local` | Covers the current catalog and contract boundary |
| Full Python | 1,238 passed; one intentional durability-warning regression warning | `recorded-local` | Local Python run; no GitHub matrix result is claimed |
| Standalone release | 1,226 passed, 1 deselected; lock, clean wheel, and both golden flows passed | `recorded-local` | Optional Aptus integration remains separate |
| CLI/workbench parity | PASS | `recorded-local` | No new Mac UI operation exists |
| macOS XCTest | 66 passed; `TEST SUCCEEDED` | `recorded-local` | Local unsigned Debug test build |
| Governance and structure | Tracking, lock, Ruff, fixture/evidence JSON validity, and diff checks passed | `recorded-local` | Reconciled after executable gates |
| Independent review | Code, documentation, boundary, and adversarial test audits found no remaining blocker | `recorded-local` | Review is local, not a GitHub review claim |

The positive matrix executes and strictly reloads all 11 compatible current
container/schema pairs, comparing each preview payload, canonical byte size,
and SHA-256 to ordinal zero of the published partition. Exact payloads through
65,536 bytes remain complete; over-limit, evaluation-first response-budget,
train-second response-budget, and metadata-only refusal paths are pinned.
Retained plan-bound evidence makes forged omission labels fail closed. Empty
evaluation, exact Unicode/control transport, normalized destination trees,
one source snapshot, no renderer or destination access, non-dry-run response-v1
compatibility, and strict CLI-backed Mac v2 decoding all pass. The ten persisted
verified-export models, requests, discovery, production catalog, taxonomy, and
support state remain unchanged. At that local-admission checkpoint, item 5.7
had not begun; item 5.6 later merged as PR #58 at
`cd017941090c7352cb1d10f9a383042b954d4f2e` after all 14 GitHub checks passed.

### Item 5.7 and Phase 5 local closeout — 2026-08-22

Item 5.7 is a documentation-only operator-guidance and reconciliation change
on the working tree based on PR #58's merge commit
`cd017941090c7352cb1d10f9a383042b954d4f2e`. The observations below do not
claim publication, GitHub checks, merge, or clean-main synchronization for the
item 5.7 pull request.

| Evidence | Result | Grade | Limitation |
| --- | --- | --- | --- |
| Phase 5 exit semantics | All 11 compatible current container/schema pairs preserve exact rows and separate logical partitions; CSV/messages refusal and canonical semantic tamper evidence remain green | `recorded-local` | Executable proof was delivered by items 5.1–5.6; item 5.7 changes documentation only |
| Full Python | 1,238 passed; one intentional durability-warning regression warning | `recorded-local` | Local Python run; GitHub's version matrix remains separate publication evidence |
| Standalone release | 1,226 passed, 1 deselected; lock, clean wheel, and both golden compile/external-digest/transport flows passed | `recorded-local` | Optional Aptus integration remains separate |
| macOS XCTest | 66 passed; `TEST SUCCEEDED` | `recorded-local` | Local unsigned Debug test build |
| CLI/workbench parity | PASS | `recorded-local` | Temporary parity artifacts were not retained |
| Governance and structure | Tracking, tracking regression, lock, Ruff, structured JSON, and diff checks passed; 489 local link/image occurrences passed across 35 changed/new Markdown files | `recorded-local` | Five external links were skipped; external crawling and Mermaid rendering are not automated gates |
| Independent review | Guidance and closeout audits found no product, contract, support-registry, or documentation blocker | `recorded-local` | Local read-only review, not a GitHub review claim |

The exact syntax-aware local-link audit is retained below so the summarized
count is reproducible. It parses changed and untracked Markdown through
MarkdownIt, checks local path existence and Markdown fragments, and reports but
does not crawl external links.

<!-- phase5-link-audit-script -->
```python
import pathlib
import re
import subprocess
import urllib.parse

from markdown_it import MarkdownIt

root = pathlib.Path(".").resolve()
changed = subprocess.check_output(
    ["git", "diff", "--name-only", "--diff-filter=ACM", "--", "*.md"],
    text=True,
).splitlines()
untracked = subprocess.check_output(
    ["git", "ls-files", "--others", "--exclude-standard", "--", "*.md"],
    text=True,
).splitlines()
files = sorted(set(changed + untracked))
markdown = MarkdownIt("commonmark")


def destinations(text):
    result = []

    def walk(tokens):
        for token in tokens or []:
            if token.type == "link_open":
                result.append(token.attrGet("href"))
            elif token.type == "image":
                result.append(token.attrGet("src"))
            if token.children:
                walk(token.children)

    walk(markdown.parse(text))
    return [destination for destination in result if destination is not None]


def anchors(path):
    tokens = markdown.parse(path.read_text(encoding="utf-8"))
    found = set()
    seen = {}
    for index, token in enumerate(tokens[:-1]):
        if token.type != "heading_open" or tokens[index + 1].type != "inline":
            continue
        label = tokens[index + 1].content.strip().lower()
        slug = re.sub(r"[^\w\-\s]", "", label, flags=re.UNICODE)
        slug = re.sub(r"\s", "-", slug)
        occurrence = seen.get(slug, 0)
        seen[slug] = occurrence + 1
        if occurrence:
            slug = f"{slug}-{occurrence}"
        found.add(slug)
    return found


anchor_cache = {}
checked = 0
passed = 0
external = 0
failures = []
for relative_path in files:
    source = root / relative_path
    for destination in destinations(source.read_text(encoding="utf-8")):
        parsed = urllib.parse.urlsplit(destination)
        if parsed.scheme or parsed.netloc:
            external += 1
            continue
        checked += 1
        raw_path = urllib.parse.unquote(parsed.path)
        if not raw_path:
            target = source
        elif raw_path.startswith("/"):
            target = root / raw_path.lstrip("/")
        else:
            target = source.parent / raw_path
        target = target.resolve()
        valid = target.exists()
        reason = "missing path"
        if valid and parsed.fragment:
            if target.is_file() and target.suffix.lower() == ".md":
                if target not in anchor_cache:
                    anchor_cache[target] = anchors(target)
                valid = (
                    urllib.parse.unquote(parsed.fragment).lower()
                    in anchor_cache[target]
                )
                reason = "missing anchor"
            else:
                reason = "fragment target is not Markdown"
        if valid:
            passed += 1
        else:
            failures.append((relative_path, destination, reason))

print(
    f"changed_markdown_files={len(files)} local_links_checked={checked} "
    f"passed={passed} failed={len(failures)} "
    f"external_links_skipped={external}"
)
for failure in failures:
    print("FAIL", *failure, sep=" | ")
```
<!-- /phase5-link-audit-script -->

The [Generic Export Operator Guide](../../../../docs/generic-exports.md)
documents when to use split JSONL, canonical JSON, or constrained CSV without
making container choice determine training objective, row schema, or consumer
compatibility. It preserves train/evaluation separation, payload/provenance
separation, the canonical-bundle authority, source-bound export verification,
and receipt-anchored optional transport. Split JSONL and canonical JSON retain
all four current schemas; constrained CSV retains the three flat schemas and
refuses nested `messages` with both JSON alternatives.

No runtime source, test behavior, persisted schema, request, response,
discovery entry, selector, taxonomy entry, support state, renderer, consumer
profile, or trainer claim changed in item 5.7. The three production generic
descriptors retain null consumer profiles. Phase 5 is locally complete; Phase 6
remains planned and must not begin until the item 5.7 pull request is green,
merged, and clean local `main` equals `origin/main`.
