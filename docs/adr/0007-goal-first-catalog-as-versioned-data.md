# ADR-0007 — Goal-First Catalog and Presets as Versioned Data

**Status:** Accepted

**Date:** 2026-08-22

**Decider:** Repository owner direction

## Context and evidence

Five deterministic named recipes map one-to-one to the five persisted
objective kinds, but selecting one requires the objective, row-schema,
supervision, and recipe-setting vocabulary. Recipe defaults are literal in the
CLI, MCP server, pipeline service, YAML runner, recipe library, constructors,
and the Swift workbench; `PipelineService.construct` does not build recipes
through the library. No persisted field records the supervised region; it is
derived from the row schema by the taxonomy loss policy. The Phase 6 roadmap
requires plain-language goals, versioned presets that are "not duplicated
CLI/Swift constants", a preview of exactly what receives loss, and identical
recipe identifiers on every surface.

## Decision

1. The goal catalog (Phase 6.1) and recipe presets (Phase 6.4) are packaged
   versioned JSON under `src/veriformis/goals/`, validated by strict models on
   load, canonical byte-for-byte, and emitted unchanged by every discovery
   surface. CLI options, MCP defaults, the service, the YAML runner, the recipe
   library, and the Swift workbench consume these data through discovery and
   shared constants derived from them; they hold no independent literals.
2. Every goal resolves to exactly one existing objective kind and named
   recipe; every representation resolves to exactly one existing row schema
   and its taxonomy loss policy. Supervised instruction and conversation
   representations are representations over the supervised objectives, not a
   sixth objective. The catalog adds no objective, row schema, family, loss
   policy, or learning behavior, and it never describes a summary.
3. The supervised region is derived for preview from the objective field
   roles and the taxonomy loss policy. It is not persisted in `ProductRow` or
   provenance, because under Finished Dataset v1 it is a pure function of the
   row schema. Multi-span supervision (Phase 17) requires a new row contract
   and will define persistence then.
4. `input_family` becomes the seventh taxonomy axis in Phase 6.2 under its
   own ADR, additively within taxonomy v1.
5. The Mac workbench receives a catalog-driven goal picker, a preflight panel,
   and a loss/row preview screen in Phase 6, each a thin bridge over an
   existing CLI command, because Phase 18 depends on them and the Phase 6 exit
   gate is phrased for a non-developer.

## Consequences

- Goal and representation identifiers are never persisted in a recipe, row,
  bundle, or export; only their resolved objective and row schema are.
- Tracking binds `training.implemented_goals` to the catalog, so a goal cannot
  be advertised without an implemented objective and recipe.
- Phase 6.4 must remove duplicated default literals and add a regression that
  fails when any surface reintroduces one.
- Plain-language fields are checked mechanically for machine identifiers and
  summary claims (usability criterion U1).
- Phase 6.7 stores one static `instruction_template` and unique
  `instruction_task` per goal in the same packaged catalog. Those templates
  are the only default instruction literals. An operator instruction is
  admitted only when it names that task and contains no claim vocabulary
  for a transformation the goal does not perform.

## Review triggers

Any objective, row-schema, or loss-policy change; any new representation;
Phase 6.4 preset freeze; Phase 17 multi-span supervision; Phase 18 workbench
completion.
