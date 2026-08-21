# Phase 3 Evidence

**Evidence status:** Complete — Phase 3 exit gates observed

**Predecessor:** [Phase 2 closeout](../phase-02-reliability-artifact-boundary/closeout.md);
[pre-Phase-3 defect closure](../defect-closure-pre-phase-03/closeout.md)

## Source-verified starting facts

| Fact | Evidence | Limitation |
| --- | --- | --- |
| Objective is not a row schema | `TrainingObjective` and `DatasetRecipe.target_row_schema`; ADR 0003 | Docs and CLI still say “format” in places |
| Five deterministic objectives are implemented | `DETERMINISTIC_V1_OBJECTIVE_KINDS`; named recipe library | No preference or generated family |
| Four product row schemas are implemented | `V1_ROW_SCHEMA_KINDS`; finished-dataset contract | `text` is `full_text` only |
| `full_text` requires `text`; others forbid `text` | `DatasetRecipe` validator; `PipelineService.construct` | Error text is local to those call sites |
| Canonical bundle is `minimal-v1` | Bundle constants; support registry | Not a trainer profile |
| Transport is deterministic `.vfbundle.zip` | ADR 0005; bundle transport contract | Not a generic export container |
| Aptus is optional and records a supervised boundary per row | `handoff/aptus_v1.py` `_masking_expectation` | Adapter-local; not a shared registry |
| Legacy CLI mode names are not recipe schemas | Construction contract product-row declarations | Surfaces may still expose the aliases |
| Phase 3 had no packet while `planned` | `program.json` before this change | Packet now required for `in_progress` |

## Required final evidence

- [x] Taxonomy contract with explicit axis, family, loss, and compatibility rules.
- [x] Machine registry bound to existing objective, row, container, and profile IDs.
- [x] Invalid-combination tests that fail before compile.
- [x] Discovery parity across `PipelineService`, CLI, MCP, and workbench help.
- [x] Proof that existing workspaces and sealed bundles still load.
- [x] Tracking, status, support, evidence, and diff checks.

Exact results are appended only after observation.

## Observed opening results — 2026-08-20

| Gate | Result | Grade / limitation |
| --- | --- | --- |
| Project tracking | PASS | Test-verified; Phase 3 packet and WIP table agree |
| Ruff | All checks passed | Recorded local |
| Taxonomy and contract tests | 24 passed | Test-verified |
| Core pytest | 740 passed, 1 deselected | Test-verified; +12 taxonomy tests over the 728 defect-closure baseline |
| `git diff --check` | Clean | Recorded local |

Surface discovery, compile-path wiring, and the public “format” inventory are
not claimed by this observation.

## Observed compile-compatibility results — 2026-08-21

| Gate | Result | Grade / limitation |
| --- | --- | --- |
| Shared compile validator | PASS | Service, CLI, MCP, YAML, named recipes, and workbench compile plan covered |
| Pre-compile refusal | PASS | Invalid objective/row/profile combinations do not open or advance a workspace |
| Aptus profile boundary | PASS | `text` refused at compile selection and descriptor construction; canonical `text` remains supported |
| Persisted construction error code | PASS | Public construction surfaces retain `construction-invalid` |
| Focused Python tests | 55 passed | Taxonomy, service, CLI, recipe/YAML, MCP, model replay, and handoff |
| Full Python suite | 758 passed | One expected durability-warning test warning |
| macOS XCTest | 29 passed | Workbench standalone and Aptus compile plans covered |
| Clean-wheel install smoke | PASS | Installed wheel repeated standalone full-text and continuation golden compiles |
| Golden `full_text` | PASS | Manifest `2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733`; archive `d17217ace8e8929ce4d41f88b3a2bca54b6976ed95b9c7dc42122e97bdfb9980` |
| Golden `continuation` | PASS | Manifest `58df8db589199821d1d51fefbe7d2a777a0e72ea8bb642dada4dfa350f89ef6b`; archive `d898ccb3ade4a5fc2c129c4271e191a7e500b190a728fd8ee18095451b13ec3b` |
| Ruff / diff | PASS | All checks passed; `git diff --check` clean |

Discovery parity, public vocabulary cleanup, migration fixtures, and final
Phase 3 closeout remain open.

## Observed taxonomy-discovery results — 2026-08-21

| Gate | Result | Grade / limitation |
| --- | --- | --- |
| `PipelineService` discovery | PASS | Returns a fresh adapter-safe copy with the exact nine-key implemented registry |
| CLI discovery | PASS | `veriformis taxonomy` emits deterministic sorted JSON only; no `format` key |
| MCP discovery | PASS | `taxonomy` tool delegates to `PipelineService` with exact JSON parity |
| Workbench help | PASS | Strict nine-key decoder, async CLI invocation, cancel-and-replace state, six-axis disclosure, and explicit unavailable state |
| Lock / Ruff | PASS | Lockfile current; Python lint clean |
| Focused discovery parity | 5 passed | Registry, service, deterministic CLI, MCP registration, delegation, and parity |
| Full Python suite | 761 passed | One expected transport durability `RuntimeWarning` |
| Full macOS XCTest | 37 passed | Includes strict decoder, exact CLI argument, ready/unavailable, and stale-request replacement coverage |
| Live CLI payload | PASS | Exact contract metadata and six axes accepted by the workbench decoder |
| Clean-wheel / installed CLI / golden compile | PASS | Standalone full-text and continuation compiles succeeded from the installed wheel |
| Golden `full_text` unchanged | PASS | Manifest `2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733`; archive `d17217ace8e8929ce4d41f88b3a2bca54b6976ed95b9c7dc42122e97bdfb9980` |
| Golden `continuation` unchanged | PASS | Manifest `58df8db589199821d1d51fefbe7d2a777a0e72ea8bb642dada4dfa350f89ef6b`; archive `d898ccb3ade4a5fc2c129c4271e191a7e500b190a728fd8ee18095451b13ec3b` |
| Project tracking | PASS | 21 roadmap phases and governed packet structure agree |
| `git diff --check` | Clean | Recorded local |

The ambiguous public “format” inventory and rewrite, migration fixtures,
backward-compatibility proof, and final Phase 3 closeout remain open.

## Observed public-vocabulary results — 2026-08-21

| Gate | Result | Grade / limitation |
| --- | --- | --- |
| Public docs inventory | PASS | Active product, CLI, install, status, roadmap, tracking, and Mac copy classified; historical records and deliberate warnings retained |
| Axis-specific product copy | PASS | Objective, semantic row, physical container, consumer profile, input type, and row lowering are named separately |
| Workbench stage presentation | PASS | Persisted `format` renders as `Lower rows` in pipeline, failure, cancellation, and history UI |
| Persisted/raw compatibility | PASS | Enum raw value, CLI argv, workspace stages, logs, Codable fields, bundle schemas, legacy keywords, and migrations unchanged |
| Unknown stage compatibility | PASS | Presentation resolver preserves an unknown persisted raw stage string verbatim |
| Lock / Ruff | PASS | Lockfile current; Python lint clean |
| Focused taxonomy/tracking | 13 passed | Contract and governed tracking synchronization |
| Full Python suite | 761 passed | One expected transport durability `RuntimeWarning` |
| Full macOS XCTest | 38 passed | Raw-ID, exact argv, display alias, error, cancellation, history, and unknown-stage coverage |
| Clean-wheel / installed CLI / golden compile | PASS | Standalone full-text and continuation compiles succeeded from the installed wheel |
| Golden `full_text` unchanged | PASS | Manifest `2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733`; archive `d17217ace8e8929ce4d41f88b3a2bca54b6976ed95b9c7dc42122e97bdfb9980` |
| Golden `continuation` unchanged | PASS | Manifest `58df8db589199821d1d51fefbe7d2a777a0e72ea8bb642dada4dfa350f89ef6b`; archive `d898ccb3ade4a5fc2c129c4271e191a7e500b190a728fd8ee18095451b13ec3b` |
| Project tracking / diff | PASS | 21 roadmap phases agree; `git diff --check` clean |

Taxonomy catalog round-trip, existing workspace/bundle backward-compatibility
proof, support/evidence reconciliation, and final Phase 3 closeout remain open.

## Observed taxonomy and persisted-v1 compatibility — 2026-08-21

| Gate | Result | Grade / limitation |
| --- | --- | --- |
| Taxonomy v1 golden | PASS | Shipped nine-key discovery shape round-trips through canonical JSON; canonical SHA-256 `4a5a7b6fbd00b2b07ac38cd84817bbde87d54af32844e331dc5a65770954aeac` |
| Frozen pre-taxonomy workspace | PASS | Generated 2026-08-21 with source revision `f8dd1bf`; complete layout-v1/revision-v3 parse-to-clean workspace opens with full history/object verification and default cleaning replay is unchanged |
| Frozen pre-taxonomy bundle | PASS | Strict v1 manifest, attestation, validation, payload, and provenance verification reaches `external_digest` at manifest `2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733` |
| Live local workspaces | PASS | Two locally excluded 2026-08-06 workspaces opened with ten verified revisions each; recorded-local only |
| Live local bundles | PASS | Two locally excluded sealed bundles verified; one was externally anchored to retained manifest `5e8b8ce5360b713330488391b97bdfdae1c162defd33a147fcb15bccfa7ee5d8`; recorded-local only |
| Focused taxonomy and compatibility | 15 passed | Includes canonical catalog, frozen workspace, and frozen bundle regressions |
| Full Python suite | 764 passed | One expected transport durability `RuntimeWarning` |
| Exact local release gate | 752 passed, 1 deselected | Optional handoff excluded by the governed core command; lock and Ruff passed |
| Clean-wheel / installed CLI / golden compile | PASS | Standalone full-text and continuation compiles succeeded from the installed wheel |
| Golden `full_text` unchanged | PASS | Manifest `2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733`; archive `d17217ace8e8929ce4d41f88b3a2bca54b6976ed95b9c7dc42122e97bdfb9980` |
| Golden `continuation` unchanged | PASS | Manifest `58df8db589199821d1d51fefbe7d2a777a0e72ea8bb642dada4dfa350f89ef6b`; archive `d898ccb3ade4a5fc2c129c4271e191a7e500b190a728fd8ee18095451b13ec3b` |
| Corpus fixture inventory | PASS | Compatibility snapshots live outside the corpus fixture root; governed aggregate is unchanged |
| Project tracking / diff | PASS | 21 phases and governed packets agree; `git diff --check` clean |

No taxonomy, recipe, workspace, finished-dataset, bundle, or transport schema
was bumped or rewritten. Final cross-surface closeout evidence remains open.

## Observed Phase 3 closeout gates — 2026-08-21

| Gate | Result | Grade / limitation |
| --- | --- | --- |
| Roadmap taxonomy semantics | PASS | Six axes remain separate; every implemented objective/row pair has one family and loss meaning |
| Compile refusal | PASS | Invalid objective, row, and profile selections fail before workspace mutation |
| Physical-container boundary | PASS | Current compile surface exposes no container selector; only the fixed implemented canonical and transport containers are published |
| Taxonomy and persisted-v1 compatibility | PASS | Canonical discovery golden, frozen workspace, and frozen bundle pass without changing an existing persisted workspace/artifact schema or identifier |
| Full Python suite | 764 passed | One expected transport durability `RuntimeWarning` |
| Exact local release gate | PASS | 752 core tests passed, one optional test deselected, one expected warning; lock, Ruff, clean-wheel install, and golden compiles passed |
| Full macOS XCTest | 38 passed | Complete checked-in test target |
| Workbench parity | PASS | CLI/workbench canonical stage and taxonomy expectations agree |
| Project tracking | PASS | Final reconciled tree matches all 21 roadmap phases and the code-bound support registry |
| Structured-file and shell checks | PASS | All 13 tracked JSON files, 2 tracked YAML files, and 10 tracked shell scripts loaded or passed syntax checks |
| Active local Markdown targets | PASS | 485 checked targets; zero broken |
| Checked-in workbench build/launch | PASS | Fresh Debug build launched with the repository CLI |
| Golden `full_text` unchanged | PASS | Manifest `2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733`; archive `d17217ace8e8929ce4d41f88b3a2bca54b6976ed95b9c7dc42122e97bdfb9980` |
| Golden `continuation` unchanged | PASS | Manifest `58df8db589199821d1d51fefbe7d2a777a0e72ea8bb642dada4dfa350f89ef6b`; archive `d898ccb3ade4a5fc2c129c4271e191a7e500b190a728fd8ee18095451b13ec3b` |

The full suite, exact local release gate, complete macOS target, parity,
tracking, structured-file, shell, active-link, diff, and build/launch checks
were repeated after the documentation and tracking reconciliation. This packet
does not fabricate or claim a GitHub CI result; remote checks are evaluated on
the closeout pull request.
