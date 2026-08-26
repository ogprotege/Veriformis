# Contributing to Veriformis

Veriformis is an alpha dataset compiler with strict source-fidelity and integrity goals. Contributions should improve the implemented product without overstating guarantees that the code does not yet provide.

## Start with the current contract

Before changing code, read:

- [Product contract](docs/product-contract.md)
- [Integrity Contract v1](docs/contracts/integrity-v1.md)
- [Dataset Construction Contract v1](docs/contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](docs/contracts/finished-dataset-v1.md)
- [Dataset Taxonomy Contract v1](docs/contracts/taxonomy-v1.md)
- [Deterministic Archive Transport v1](docs/contracts/bundle-transport-v1.md)
- [Verified Export Contract v1](docs/contracts/verified-export-v1.md)
- [Split JSONL Export Contract v1](docs/contracts/split-jsonl-export-v1.md)
- [Canonical JSON Export Contract v1](docs/contracts/canonical-json-export-v1.md)
- [Constrained CSV Export Contract v1](docs/contracts/constrained-csv-export-v1.md)
- [Goal Catalog v1](docs/contracts/goal-catalog-v1.md)
- [Recipe Preset v1](docs/contracts/recipe-preset-v1.md)
- [Row Mapping v1](docs/contracts/row-mapping-v1.md)
- [Existing-dataset import](docs/mapping.md)
- [ADR-0006: Receipt-Anchored Export-Pack Transport](docs/adr/0006-receipt-anchored-export-pack-transport.md)
- [ADR-0012: Consumer Profile as Optional Adapter](docs/adr/0012-consumer-profile-as-optional-adapter.md)
- [ADR-0013: Columnar Containers as Optional Generic Exports](docs/adr/0013-columnar-containers-as-optional-generic-exports.md)
- [ADR-0014: Independently Admitted Consumer Profiles](docs/adr/0014-independently-admitted-consumer-profiles.md)
- [ADR-0016: Optional Local Tesseract 5 OCR](docs/adr/0016-optional-local-tesseract-ocr.md)
- [Quality Report v1](docs/contracts/quality-report-v1.md)
- [Aptus Handoff Contract v1](docs/contracts/aptus-handoff-v1.md)
- [Current implementation status](docs/current-status.md)
- [Project tracking and evidence policy](docs/governance/project-tracking.md)
- [Active independent-product ledger](dev/active/independent-product/program.json)
- [Support registry](docs/governance/support-registry.json)
- [Install guide](docs/install.md)
- [Architecture](docs/architecture.md)
- [CLI reference](docs/cli.md)
- [Development guide](docs/development.md)
- [Release guide](docs/release.md)
- [Beta limitations](docs/beta-limitations.md)
- [macOS workbench](macos/README.md)
- [Independent product roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md)

The roadmap is ordered. Historical Groups 1–7, Group 9 automated gates,
beta-prep, and private beta workbench Phases 0–2 are implemented.
Independent-product Phases 0–12 are complete on `main`. Phase 12 closeout
merged as PR #112 at `892939f527974b69282296ded04eb3b43643554f`. Optional
Tesseract 5 OCR is classified, thresholded, previewable, and isolated
under empty extra `ocr`. Default parse still refuses image-only PDF.
`ocr-image` stays explicitly unsupported. Phase 13 quality intelligence
is complete with previewable gates and labeled fixtures. No heuristic
blocks seal. Phase 14 review workflows are in progress at item 14.1.
Do not start Phase 15 from that packet.
Phase 10 implements Axolotl, LLaMA-Factory, and Aptus as optional
adapters under ADR-0014; `unsloth` remains a non-executable candidate.
Extras stay empty.
Consult the
[completed Phase 4 packet](dev/active/independent-product/phase-04-verified-export-foundation/README.md)
and the machine ledger before changing the verified-export boundary. The typed
service,
verified source view, strict v1 model contracts, source-trust admission, and
read-only source-derived plan population and semantic-membership enforcement are
merged through item 4.7. Phase 4.8 adds a private
production-empty implementation catalog and strict discovery, dry run,
self-described inspect, operator-confirmed no-replace execute, and source-bound
verify operations through `PipelineService`, CLI, MCP, and the CLI-backed Mac
bridge. It merged as PR #50 at
`fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`, with review corrections in PR #51
at `d91542fe12c5a492de578ad060836a7d65999e42`; Phase 4.9 completes the
adversarial closeout. Those remain historical Phase 4 facts: its production
catalog closed empty. Phase 5.1–5.3 install exact-byte
`split-jsonl-directory`, canonical `json`, and `constrained-csv` v1
implementations; Phase 5.4 adds only their post-export archive transport.
Neither adds a semantic replayer or trainer-specific profile. Request v1 uses split JSONL's
`train` / `evaluation` names and aligned provenance and canonical JSON's fixed
tree; it also selects constrained CSV's fixed quoted-CSV tree. Request v2
applies only to split JSONL and must provide the complete
`veriformis.split-jsonl-options/v1` object to change the safe filename stems or
omit provenance. Canonical JSON and constrained CSV refuse configured
requests. Constrained CSV admits the flat `text`, `prompt_completion`, and
`instruction_output` schemas and refuses `messages` before publication with a
split JSONL or canonical JSON alternative. No surface may
change rows, ordering, curation, split policy, or partition membership.
Item 5.4 merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`:
`deterministic-export-pack-zip-v1` packages one unchanged, already-published
export directory as `.vfexport.zip` under an externally retained canonical
receipt digest. It is not a fourth renderer, source-bound verification,
consumer/trainer profile, MCP operation, or Mac UI promise. Phase 5.5's merged
PR #57 fixture is test proof only: it strictly reloads all compatible
container/schema pairs from ordinary files and adds no production importer,
replayer, public surface, persisted schema, taxonomy, or support claim. Item
5.6 adds only one bounded runtime dry-run response: an unchanged plan, exact
ordinal-zero samples for non-empty partitions, and a normalized plan-derived
tree plus `export-receipt.json`. Preserve complete payloads through the 65,536-
byte inclusion ceiling, whole-row omission above it or under response-budget
pressure, ASCII-safe exact-value transport, and the no-renderer
and no-destination boundary. Do not promote a persisted schema, selector,
taxonomy, support state, consumer, or trainer claim. Item 5.6 merged as PR #58
at `cd017941090c7352cb1d10f9a383042b954d4f2e`; the completed Phase 5
[operator guide](docs/generic-exports.md) is the current container-choice
boundary.
Maturity remains
development **alpha**. Do not describe the
product as public-ready without [docs/beta-limitations.md](docs/beta-limitations.md)
and [docs/release.md](docs/release.md).

After reading these authorities, consult [Work in progress](WIP.md) as the
non-authoritative reviewed work queue.

## Set up

```bash
uv sync --extra test
uv run ruff check src tests
uv run python scripts/check_project_tracking.py
uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"
```

Python 3.11 or newer is required. The test matrix runs Python 3.11, 3.12, and
3.13 on Ubuntu plus Python 3.12 on macOS. Separate Ubuntu jobs run install
smoke and golden compilation (see
[docs/release.md](docs/release.md)).

## Choose a focused change

Keep each change centered on one behavior or one coherent roadmap step. Preserve unrelated worktree changes. Do not mix broad refactors, new features, and documentation replacement without a clear reason.

For integrity or provenance repairs:

1. write a failing regression test;
2. demonstrate the incorrect current behavior;
3. implement the smallest complete repair;
4. run focused tests;
5. run the full required checks;
6. update affected documentation.

## Required contribution standards

### Evidence and provenance

- Preserve original-file hashes and source identity.
- Keep canonical-stream and span semantics explicit.
- Report parser loss or refusal. Do not silently claim fidelity.
- Test multi-source behavior whenever identities or workspace state change.
- Keep validation facts bound to the artifacts they describe.

### Dataset semantics

- Do not label copied source text as a summary or another transformation that did not occur.
- Do not invent instructions or targets inside a serializer.
- Keep recipe source selection exact. Do not silently widen or narrow it.
- Bind every constructed field to replayable source-text or strict-IR evidence.
- Keep structured prompt and target boundaries when downstream masking depends on them.
- Treat human review as a recipe or policy state, not a universal prerequisite for dataset construction.
- Keep curation and split policy explicit, versioned, deterministic, and bound
  to the finished plan.
- Keep `0.1.0` deterministic and offline unless an approved roadmap step changes that boundary.

### Safety and compatibility

- Fail closed on unsupported formats and failed validation.
- Avoid destructive cleaning defaults.
- Add negative tests for malformed input and stale state.
- Preserve Python 3.11 compatibility; it is an explicit CI matrix cell.
- Do not add a dependency without checking its license, maintenance status, and necessity.

### Documentation

- Use present tense only for implemented, merged, tested behavior.
- Put planned behavior in a clearly labeled section and link the roadmap.
- Update command examples when CLI flags or defaults change.
- State known integrity and provenance limitations directly.
- Do not claim a gate, input format, interface, or bundle guarantee that is not exercised by code and tests.
- Update the active phase packet, program ledger, support registry, WIP,
  current status, and evidence records when tracked truth changes.

## Tests expected by change type

| Change | Minimum evidence |
|---|---|
| Parser | Structural fixture, canonical text, spans, refusal or loss diagnostics |
| Cleaning rule | Positive case, false-positive case, safety-threshold case |
| Chunker | Coverage, short input, identity, span, overlap or boundary behavior |
| Constructor | Declared objective, source evidence, negative semantic case |
| Serializer | Exact schema and loss-bearing field boundaries |
| Validation gate | Passing, failing, malformed, and stale-input cases |
| Bundle or workspace | Tamper, replay, collision, interruption, and recovery cases |
| CLI | Help contract, exit status, artifacts, and actionable error text |

## Pull request checklist

- [ ] The change has a narrow stated purpose.
- [ ] New behavior has regression or acceptance tests.
- [ ] `uv run ruff check src tests` passes.
- [ ] `uv run python scripts/check_project_tracking.py` passes.
- [ ] `uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"` passes.
- [ ] Current and planned behavior remain clearly separated.
- [ ] Relevant CLI, architecture, development, and limitation docs are updated.
- [ ] No unrelated generated files, secrets, credentials, or local configuration are included.
- [ ] The pull request identifies any remaining unverified claim or follow-up work.

## Current project boundary

Version `0.1.0` provides the complete deterministic stage-command runtime
through independent bundle verification, `PipelineService`, transactional
workspace revision schema 3, five objectives, curation, leakage-safe splits,
four row schemas, exact 17-gate validation, expanded declared ingest, YAML,
local MCP, optional Aptus handoff, and the SwiftUI workbench. It remains a
development alpha. Follow the current state and exit gates in the
[independent product roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md),
[program ledger](dev/active/independent-product/program.json), and the current
phase packet when one is active. `split-jsonl-directory`, canonical `json`,
and `constrained-csv` v1 are the supported generic containers. Every new
trainer-specific profile remains planned until its own roadmap gates pass.
This does not erase the existing canonical or optional Aptus profiles.
The separate `deterministic-export-pack-zip-v1` physical container is an
optional post-export transport and does not appear in export discovery.
