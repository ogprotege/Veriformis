"""Private executable bindings for verified export container implementations."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from veriformis.datasets import ProductRow, RowProvenance, RowSet
from veriformis.errors import ExportContractError
from veriformis.exports.api import ExportProfileDescriptor
from veriformis.exports.models import ExportFilePlan, ExportPlan


@dataclass(frozen=True, slots=True)
class _RenderedDerivative:
    """One renderer result before service-owned publication."""

    files: tuple[tuple[str, bytes], ...]
    train_rows: tuple[ProductRow, ...]
    evaluation_rows: tuple[ProductRow, ...]
    provenance: tuple[RowProvenance, ...]


@dataclass(frozen=True, slots=True)
class _ReplayedDerivative:
    """One reconstruction of semantics from produced file bytes."""

    semantic_contents: tuple[tuple[str, bytes], ...]
    train_rows: tuple[ProductRow, ...]
    evaluation_rows: tuple[ProductRow, ...]
    provenance: tuple[RowProvenance, ...]


_ContainerOptions = Mapping[str, Any]
_ParsedContainerOptions = object
_FilePlanner = Callable[
    [ExportProfileDescriptor, RowSet],
    Sequence[ExportFilePlan],
]
_OptionsParser = Callable[[_ContainerOptions], _ParsedContainerOptions]
_ConfiguredFilePlanner = Callable[
    [ExportProfileDescriptor, RowSet, _ParsedContainerOptions],
    Sequence[ExportFilePlan],
]
_Renderer = Callable[[ExportPlan, RowSet], _RenderedDerivative]
_SemanticReplayer = Callable[
    [ExportPlan, tuple[tuple[str, bytes], ...]],
    _ReplayedDerivative,
]


@dataclass(frozen=True, slots=True)
class _ExportImplementation:
    """Private executable half of one discoverable profile selector."""

    descriptor: ExportProfileDescriptor
    file_planner: _FilePlanner
    renderer: _Renderer
    semantic_replayer: _SemanticReplayer | None
    options_parser: _OptionsParser | None = None
    configured_file_planner: _ConfiguredFilePlanner | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, ExportProfileDescriptor):
            raise ExportContractError(
                "export implementation descriptor has the wrong runtime type"
            )
        if not callable(self.file_planner) or not callable(self.renderer):
            raise ExportContractError(
                "export implementation planner and renderer must be callable"
            )
        if (self.options_parser is None) != (self.configured_file_planner is None):
            raise ExportContractError(
                "configured export implementation requires both an options parser "
                "and configured file planner"
            )
        if self.options_parser is not None and (
            not callable(self.options_parser)
            or not callable(self.configured_file_planner)
        ):
            raise ExportContractError(
                "export implementation option hooks must be callable"
            )
        semantic = (
            self.descriptor.container_profile.determinism_claim
            == "semantic_content_only"
        )
        if semantic and not callable(self.semantic_replayer):
            raise ExportContractError(
                "semantic export implementation requires a semantic replayer"
            )
        if not semantic and self.semantic_replayer is not None:
            raise ExportContractError(
                "portable exact implementation cannot install a semantic replayer"
            )


__all__: list[str] = []
