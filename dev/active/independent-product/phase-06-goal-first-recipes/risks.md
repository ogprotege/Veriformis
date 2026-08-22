# Phase 6 Risk Register

**Status:** Active

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P6-R1 | Controlled for 6.1 | Medium | High | A plain-language goal quietly implies a transformation the source does not supply (summary, answer, translation) | Every goal carries `not_this` and `non_claims`; the catalog forbids `summary` as a goal, alias, or template; item 6.7 enforces instruction truthfulness deterministically |
| P6-R2 | Controlled for 6.4 | Medium | High | Catalog text or presets drift from the objectives and defaults that execute | Catalog and presets are packaged versioned data; the tracking checker binds `implemented_goals` to the recipe library; item 6.4 removes duplicated literals and tests against reintroduction |
| P6-R3 | Controlled for 6.4 (identity); 6.6 matrix pending | Medium | High | Surfaces resolve the same goal to different recipes or rows | Item 6.6 pins `recipe_id` and digests per cell across Python, CLI, MCP, YAML, and the Mac bridge; a Swift test runs the real CLI |
| P6-R4 | Controlled for 6.3 | Medium | High | The preview shows a supervised region that differs from what serialization and export actually supervise | The preview derives the span from the same field-role and loss-policy tables serialization and export use; a test proves the span equals the serialized target for every goal and representation |
| P6-R5 | Controlled for 6.3 | Medium | Medium | Preview or preflight mutates a workspace, calls a renderer, or reads a destination | Both are read-only service operations over captured inputs with unchanged-workspace and no-destination tests, bounded like the Phase 5.6 preview |
| P6-R6 | Controlled for 6.2 | Medium | Medium | Adding `input_family` to taxonomy discovery breaks strict Swift decoding or support parity | The Swift decoder, frozen fixtures, support registry, and tracking checker are updated in the same pull request; the axis is additive and the contract version is unchanged |
| P6-R7 | Controlled for 6.4 | Low | High | Mac goal-first screens expose a capability the shared service does not own | Every Mac action is a bridge call to an existing CLI command; Swift holds no catalog, preset, or default constants |
| P6-R8 | Open | Medium | Medium | Preflight reports a source eligible that the real stages refuse, or vice versa | Item 6.5 proves preflight verdicts against actual parse, construct, and curate outcomes on the same inputs for every goal-by-family cell |
| P6-R9 | Open | Medium | Medium | The usability exit gate is judged against criteria written after the fact | U1–U6 are predeclared in `plan.md` at opening and judged with recorded evidence at closeout |
| P6-R10 | Controlled for 6.1 | Low | Medium | Reconciliation rewrites dated history or claims the item 6.N pull-request result before it exists | Dated progress entries are append-only; each item records local evidence only and cites its merge in the next item's entry |

Risks remain open until the item that controls them records evidence.
