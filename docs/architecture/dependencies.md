# Dependencies

How internal and external dependencies are managed: the fan-in kernel at the
bottom of the graph, the containment of third-party libraries at the edges,
the deferred-import idiom that keeps infrastructure acyclic, and the
versioning governance that pins it all down.

**Last reviewed:** 2026-08-23 (independent-product Phase 7 complete)

**Next review:** Any architecture or dependency change

The dependency architecture of Veriformis is organized as a strict,
downward-pointing directed acyclic graph. It runs from a dependency-light
foundation (`errors`, `contracts`, `identity`) through the canonical model and
pipeline domains (`ir`, `sources`, `evidence`, `parsers`, `rules`, `chunkers`,
`construction`, `datasets`, `bundle`) through `exports.ExportService` to the
`PipelineService` composition root. `exports/` depends on the bundle verifier
but is not a tenth workspace stage. `goals/` and `mapping/` are axial packages
over existing construction and finished-dataset contracts. CLI and MCP are
adapters over the pipeline root; recipes and the optional Aptus handoff are
bounded integration modules.
The SwiftUI workbench is outside the Python graph and shells the CLI.
No lower layer imports a higher one, and every cross-package edge targets
either a layer below or a sibling within the same layer. This shape is not
enforced by tooling — no import-linter configuration exists in the repository
— but is instead maintained by a facade convention in which every subpackage
`__init__.py` re-exports its public API. The composition service intentionally
imports deeper implementations because it is the one place where stage layers
are assembled. The consequence is a graph that remains auditable by source
inspection without making interface adapters own domain policy.

## The kernel: what fan-in actually means here

`errors.py`, `contracts.py`, and `identity.py` have broad fan-in because they
define the shared error taxonomy, persisted registries, canonical JSON,
digests, and durable identities. They sit at the bottom of the graph and do not
import pipeline domains. The genuine exposure is semantic rather than numeric:
a behavioral change to canonicalization can invalidate persisted
content-addressed data. The design's answer is versioned schema and identity
formats plus strict load-time recomputation, not a frequently changing
abstraction layer.

```mermaid
flowchart TD
    CLI["cli.py — thin Typer adapter, 23 commands"]
    MCP["mcp/ — thin local stdio adapter"]
    PIP["pipeline/service.py — composition root"]
    EXP["exports/ — verified derivative-source service"]
    WKS["workspace.py — revision infrastructure"]
    BUN["bundle/ — sealing and verification"]
    DST["datasets/"]
    CST["construction/"]
    CHK["chunkers/"]
    RUL["rules/"]
    PRS["parsers/ — format adapters"]
    IR["ir/ — canonical document model"]
    SRC["sources.py"]
    EVD["evidence.py"]
    DIA["diagnostics.py"]
    IDN["identity.py"]
    CON["contracts.py"]
    ERR["errors.py"]

    CLI --> PIP
    MCP --> PIP
    PIP --> WKS
    PIP --> EXP
    PIP --> BUN
    PIP --> DST
    PIP --> CHK
    PIP --> RUL
    PIP --> PRS
    PIP --> IR
    EXP --> BUN
    WKS -.->|"deferred function-level imports"| CHK
    WKS -.-> CST
    WKS -.-> DST
    WKS -.-> BUN
    DST --> CST
    CST --> CHK
    CST --> RUL
    CHK --> EVD
    CHK --> IR
    CHK --> SRC
    RUL --> IR
    PRS --> IR
    PRS --> SRC
    PRS --> DIA
    BUN --> CHK
    BUN --> RUL
    BUN --> EVD
    BUN --> SRC
    SRC --> CON
    SRC --> DIA
    EVD --> IDN
    IR --> IDN
    DIA --> IDN
    IDN --> ERR
```

## External integration topology: containment as anti-corruption

The system declares exactly ten runtime dependencies in `pyproject.toml`.
Seven are bounded adapters: markdown-it-py and mdit-py-plugins support
Markdown; python-docx and lxml support DOCX and XML validation; pypdfium2
supports digitally-born PDF; PyYAML loads versioned pipeline recipes; and MCP
implements the local stdio surface. Typer is confined to the CLI and jinja2 to
the retained chat renderer. Pydantic is the one deliberate cross-cutting
dependency because it validates versioned persisted contracts. Format-specific
objects are converted into canonical IR at the parser boundary, so the rest of
the nine-stage pipeline is not coupled to a Markdown token, DOCX run, PDF page,
or structured-input parser object.

```mermaid
flowchart LR
    subgraph EXT["Third-party ecosystem — ten runtime dependencies"]
        PYD["pydantic 2.x, capped below v3"]
        TYP["typer"]
        JIN["jinja2"]
        MIT["markdown-it-py + mdit-py-plugins"]
        DOCX["python-docx + lxml"]
        PDF["pypdfium2"]
        YAML["pyyaml"]
        MCPD["mcp"]
    end
    subgraph TREE["veriformis source tree"]
        CLI2["cli.py — sole typer consumer"]
        CHAT["serializers/chat.py — sole jinja2 consumer"]
        PARSE["parsers/ — ingestion boundary"]
        DIAG["diagnostics.py"]
        PDFPARSE["parsers/pdf.py"]
        RECIPE["recipes/"]
        MCPS["mcp/"]
        CONTRACTS["contract-bearing modules"]
    end
    CLI2 --> TYP
    CHAT --> JIN
    PARSE --> MIT
    PARSE --> DOCX
    DIAG --> DOCX
    PDFPARSE --> PDF
    RECIPE --> YAML
    MCPS --> MCPD
    CONTRACTS --> PYD
```

## Pydantic: a deliberate core-domain dependency

The one pervasive external dependency is pydantic, and its placement is the
point. Its occurrences sit on modules that define a
strict, versioned, on-disk contract: workspace revisions
(`src/veriformis/workspace.py:18`), construction models and evidence, all six
dataset modules, and the bundle manifest and attestation layer. The persisted
JSON these models validate is content-addressed and sealed, so schema
validation is not an implementation detail but part of the product's
verification guarantee; choosing a validation framework here is a domain
decision, not framework lock-in in the pejorative sense. The risk profile is
nonetheless real and singular: the declared bound `pydantic>=2.10,<3`
(`pyproject.toml`) means a future pydantic
v3 is the only external upgrade with project-wide blast radius. Two
mitigations are already structural. First, pydantic never leaks into the
pipeline's data currency — the `Chunk`, `TransformRecord`, and IR node types
that flow between stages are plain dataclasses
(`src/veriformis/chunkers/base.py`, `src/veriformis/rules/engine.py`), so the
runtime pipeline is framework-free. Second, the kernel modules are effectively
stdlib-only, so even a catastrophic pydantic migration leaves digests,
identities, and the error taxonomy intact.

## Composition, deferred imports, and cycle posture

Cross-layer wiring is concentrated in `pipeline/service.py`, the implemented
surface-neutral composition root. Its methods own stage policy, verified input
loading, deterministic domain calls, and workspace transactions. It now also
injects and owns `exports.ExportService`, whose Phase 4.1 dependency points
to the bundle facade. That service calls the descriptor-anchored finished-
bundle inspector and returns the immutable semantic result. Phase 4.2 adds
strict export models below that service; they depend on the finished-bundle
verification value, contract registry, identity substrate, and taxonomy loss
mapping without adding a workspace dependency. Phase 4.3 adds only
service-local trust-policy validation around that same inspector and those
model aliases. Phase 4.4 adds a read-only service composition from that
immutable bundle view into the existing strict export models. It derives the
source membership baseline from the already reconstructed row set and
provenance and adds no source reread, workspace dependency, destination I/O, or
new layer edge. Phase 4.5 composes the existing dataset `ProductRow`,
`RowProvenance`, and `RowSet` contracts with the existing export plan and
projection models inside the same service. It fresh-reconstructs normalized
semantic evidence in memory and likewise adds no workspace, filesystem,
renderer-registry, or adapter dependency edge. Phase 4.6 adds one exports-
internal filesystem helper below `ExportService`; it depends on the strict
export models and foundation utilities and owns descriptor-anchored exact-byte
publication. It adds no workspace, renderer-registry, `PipelineService`
operation, or adapter dependency edge. `cli.py` and
`mcp/server.py` translate their respective protocols into pipeline methods;
the SwiftUI workbench shells the CLI.
Phase 4.7 composes only existing export models, dataset row/provenance loaders,
identity hashing, and the exports-internal publication helper. Its private
renderer/replayer hooks add no workspace, third-party, discovery-registry,
`PipelineService`, adapter, taxonomy, or support dependency edge. Semantic
replay currently retains complete produced files in memory; the statically
bounded conformance fixture is not a scalable dependency claim.
Phase 4.8 adds a private default-empty implementation catalog inside
`exports/`, typed export methods on `PipelineService`, and thin CLI/MCP/Mac
adapters over one strict request/response protocol. The Mac process bridge
retains stdout and stderr separately so it decodes only canonical stdout. No
adapter adds a registry, renderer, filesystem verifier, taxonomy edge, or
support claim.
Phase 5.1 adds an exports-internal split JSONL planner/renderer and strict
options/data-card models. They reuse the existing dataset rows, identity,
taxonomy loss-policy lookup, portable export paths, and publication service;
no third-party serializer, workspace-stage, adapter filesystem, public plugin,
or trainer dependency edge is added. Additive request v2 is mirrored by the
CLI-backed Mac model while discovery and response remain v1.
Phase 5.2 adds an exports-internal canonical JSON planner/renderer and strict
dataset/provenance object models. It reuses the same canonical writer, row
decoders, loss-policy lookup, paths, and publication service and adds no third-
party, workspace, adapter-filesystem, plugin, or trainer edge. It needs no new
request model because its fixed profile uses request v1 and refuses v2.
Phase 5.3 adds an exports-internal constrained CSV planner/renderer and strict
dataset-card/reload validation. It uses the Python standard-library CSV codec
under a frozen fully quoted dialect and reuses the same row decoders,
loss-policy lookup, paths, provenance model, and publisher. It adds no third-
party, workspace, adapter-filesystem, plugin, trainer, or request-model edge;
the fixed profile uses request v1 and refuses v2.
Phase 5.4, merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`, adds `exports/archive.py` as a
post-export transport
adapter and moves the deterministic stored-ZIP codec into the dependency-light
`_archive_transport.py` shared by `bundle/transport.py` and the export-pack
path. The archive adapter depends on strict export receipt/path/publication
machinery; it adds no renderer, export-catalog entry, third-party ZIP library,
workspace stage, persisted model, MCP edge, Mac edge, consumer profile, or
trainer dependency. `PipelineService` selects bundle or export-pack packaging
through mutually exclusive explicit anchors. Phase 5.5 adds no production
dependency. Its test-only ordinary-file fixture composes the existing strict
row, provenance, split-JSONL, canonical-JSON, constrained-CSV, and discovery
loaders without installing an importer or semantic replayer.

Phase 5.5 merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1`. Phase 5.6 reuses existing strict
`RowSet`, `ExportPlan`, identity/JSON, response serialization, pipeline, CLI,
MCP, and Mac bridge dependencies. It adds response-v2 runtime models but no
persisted model, third-party package, renderer/replayer, filesystem adapter,
workspace edge, catalog selector, taxonomy/support dependency, or new public
operation.

This arrangement needs no dependency injection container because the contracts
passed between stages are stable, low-level data values. `workspace.py` keeps
its module-level domain coupling narrow and uses function-level imports for
semantic replay, so service and workspace orchestration do not create a
module-load cycle.

That narrowness comes with a caveat the static graph hides. `workspace.py`
reaches back up into the domain pipeline through function-level deferred
imports — `chunkers.base`, `construction`, `rules.engine`, and `sources`
inside one loader (`src/veriformis/workspace.py:2339-2348`), `datasets` and
`bundle` at `src/veriformis/workspace.py:2467` and `:2688`, and the full
parse-and-clean replay set at `src/veriformis/workspace.py:3007-3028` and
`:3408-3412`. `bundle/verifier.py` still defers construction replay imports,
but Phase 4.1 intentionally imports `RowSet` and `DatasetValidationReport` at
module load so the public `VerifiedFinishedBundle` type is introspectable.
Those are downward edges and neither target module imports `bundle`, so the
graph remains acyclic. The deferred-import pattern keeps the workspace kernel
cheap and structurally prevents cycles between infrastructure and domain; the
verifier's narrow public-type edge is not required to share that kernel-only
constraint. The
cost is real but bounded: static analysis, including the fan-in figures above,
understates runtime coupling, and an import linter would see none of these
edges.

The graph's only true cycle is intra-package and load-order-dependent:
`ir/__init__.py` imports `nodes` first (`src/veriformis/ir/__init__.py:1`) and
then `serde` (`src/veriformis/ir/__init__.py:9`), while `serde` imports its
own package back (`src/veriformis/ir/serde.py:10`). It works only because the
partially initialized package already carries the `nodes` attribute when
`serde` loads; reordering the facade's imports breaks it. Replacing the
package-level import with a direct `veriformis.ir.nodes` import would remove
the sole cycle outright, and is the cheapest hygiene improvement the graph
offers.

A related governance finding concerns `validate/gates.py`. Dependency
inspection shows it is imported inside the source tree only by its own facade
(`src/veriformis/validate/__init__.py:1`), and its `run_gates`
(`src/veriformis/validate/gates.py:114-122`) implements just five gates — yet
the seal path performs exact 17-gate snapshot validation (see
`docs/architecture.md`). The resolution is supersession, not a correctness
hole: the live seventeen-gate machinery, registered in
`V1_FINISHED_DATASET_GATES` (`src/veriformis/contracts.py:114-132`), lives in
`datasets/validation.py`, whose docstring states that only a report whose
seventeen gates pass can be sealed
(`src/veriformis/datasets/validation.py:6-7`), and it is this machinery that
`PipelineService.validate` invokes.
Similarly, `bundle/writer.write_bundle` (`src/veriformis/bundle/writer.py:150`)
consumes precomputed gate results as a parameter and refuses to seal on any
failure (`src/veriformis/bundle/writer.py:161-167`) but has no production
caller. The legacy pair is superseded yet still re-exported, which actively
misleads readers of the dependency graph; deletion or an explicit legacy
marker would restore the graph's documentary value.

## Versioning and governance posture

Dependency governance follows a reproducibility-first model. The `uv.lock`
file is committed and pins the complete resolved dependency closure, while
`pyproject.toml` declares compatible floors for runtime dependencies and
reserves a hard upper cap for pydantic, whose next major version could affect
persisted-contract validation. Tooling is
pinned more aggressively than libraries — ruff is held at exactly `==0.16.0`
in both the test extras and the tool configuration (`pyproject.toml`) —
reflecting a judgment that lint drift breaks builds more often than library
minors break behavior. Taken as a whole, the dependency strategy is
conservative in the right places: a frozen two-module kernel, format
volatility quarantined at the ingestion boundary, framework gravity confined
to persistence contracts and single-consumer edges, and exactly one
deferred-import idiom traded against static visibility. The principal residual
risks are the pydantic major-version ceiling, the load-order-fragile `ir`
cycle, and the superseded `validate` package — all three visible directly
from the graph, which is itself evidence that the layering discipline is
working.

## Related documentation

- [Architecture overview](README.md)
- [Layers](layers.md) — the layer stack this graph flattens into fan-in terms
- [Data flow](data-flow.md) — the runtime coupling the static graph hides
- [Entry points](entry-points.md) — the composition root described above, in
  invocation terms
- [Architecture hub](../architecture.md)
