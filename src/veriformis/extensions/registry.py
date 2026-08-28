"""Built-in-only wraps of existing parser, mapper, constructor, quality, and export bindings.

Item 16.3 does not change dispatch, constructor lookup, mapping execution, or
the private export catalog. It does not load entry points or scan a workspace.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from veriformis.errors import ExtensionProtocolError
from veriformis.exports._implementation import _ExportImplementation
from veriformis.extensions.protocol import EXTENSION_KINDS


@dataclass(frozen=True, slots=True)
class BuiltinBinding:
    """One trusted built-in wrap. Origin third_party is refused."""

    kind: str
    selector: str
    extra: str | None
    origin: str
    target: object

    def __post_init__(self) -> None:
        if self.origin != "builtin":
            raise ExtensionProtocolError(
                "internal registry admits origin builtin only; "
                f"requested {self.origin}"
            )
        if self.kind not in EXTENSION_KINDS:
            raise ExtensionProtocolError(
                f"unknown extension kind: {self.kind!r}; admitted kinds are "
                + ", ".join(EXTENSION_KINDS)
            )
        if not self.selector or self.selector.strip() != self.selector:
            raise ExtensionProtocolError(
                "extension binding selector must be a non-empty exact token"
            )


@dataclass(frozen=True, slots=True)
class BuiltinExtensionRegistry:
    """Built-in wraps over existing functions. Not a second export catalog."""

    parsers: tuple[BuiltinBinding, ...]
    mapper: BuiltinBinding
    constructors: tuple[BuiltinBinding, ...]
    quality_checks: tuple[BuiltinBinding, ...]
    exporters: tuple[_ExportImplementation, ...]

    def parser(self, selector: str) -> BuiltinBinding:
        for item in self.parsers:
            if item.selector == selector:
                return item
        raise ExtensionProtocolError(f"unknown built-in parser {selector!r}")

    def constructor(self, constructor_id: str, constructor_version: str) -> object:
        selector = f"{constructor_id}/{constructor_version}"
        for item in self.constructors:
            if item.selector == selector:
                return item.target
        raise ExtensionProtocolError(
            "unsupported constructor "
            f"{constructor_id!r} version {constructor_version!r}"
        )


def _unique_bindings(
    bindings: tuple[BuiltinBinding, ...],
    *,
    label: str,
) -> tuple[BuiltinBinding, ...]:
    selectors = tuple(item.selector for item in bindings)
    if len(selectors) != len(set(selectors)):
        raise ExtensionProtocolError(f"{label} selectors must be unique")
    return bindings


def builtin_registry(
    *,
    export_catalog: Sequence[_ExportImplementation],
) -> BuiltinExtensionRegistry:
    """Wrap existing bindings. Callers still use current dispatch and lookup."""
    from veriformis.construction.constructors import _CONSTRUCTORS
    from veriformis.mapping.execute import execute_mapping
    from veriformis.parsers.docx import parse_docx_file
    from veriformis.parsers.html import parse_html_file
    from veriformis.parsers.markdown import parse_md_file
    from veriformis.parsers.pdf import parse_pdf_file
    from veriformis.parsers.structured import (
        parse_csv_file,
        parse_json_file,
        parse_jsonl_file,
    )
    from veriformis.parsers.text import parse_text
    from veriformis.quality.detectors import _DETECTORS
    from veriformis.quality.gates import V1_QUALITY_GATES

    catalog = tuple(export_catalog)
    if any(not isinstance(item, _ExportImplementation) for item in catalog):
        raise ExtensionProtocolError(
            "internal export catalog must use the private implementation type"
        )
    parsers = _unique_bindings(
        (
            BuiltinBinding(
                "source-parser", "text", None, "builtin", parse_text
            ),
            BuiltinBinding(
                "source-parser", "markdown", None, "builtin", parse_md_file
            ),
            BuiltinBinding(
                "source-parser", "docx", None, "builtin", parse_docx_file
            ),
            BuiltinBinding(
                "source-parser", "html", None, "builtin", parse_html_file
            ),
            BuiltinBinding(
                "source-parser", "pdf", None, "builtin", parse_pdf_file
            ),
            BuiltinBinding(
                "source-parser", "csv", None, "builtin", parse_csv_file
            ),
            BuiltinBinding(
                "source-parser", "json", None, "builtin", parse_json_file
            ),
            BuiltinBinding(
                "source-parser", "jsonl", None, "builtin", parse_jsonl_file
            ),
        ),
        label="parser",
    )
    mapper = BuiltinBinding(
        "row-mapper",
        "execute-mapping",
        None,
        "builtin",
        execute_mapping,
    )
    constructors = _unique_bindings(
        tuple(
            BuiltinBinding(
                "deterministic-constructor",
                f"{constructor_id}/{constructor_version}",
                None,
                "builtin",
                target,
            )
            for (constructor_id, constructor_version), target in sorted(
                _CONSTRUCTORS.items()
            )
        ),
        label="constructor",
    )
    quality_checks = _unique_bindings(
        tuple(
            BuiltinBinding(
                "quality-check",
                detector_id,
                None,
                "builtin",
                pattern,
            )
            for _category, detector_id, pattern in _DETECTORS
        )
        + tuple(
            BuiltinBinding(
                "quality-check",
                spec.gate_id,
                None,
                "builtin",
                spec,
            )
            for spec in V1_QUALITY_GATES
        ),
        label="quality-check",
    )
    return BuiltinExtensionRegistry(
        parsers=parsers,
        mapper=mapper,
        constructors=constructors,
        quality_checks=quality_checks,
        exporters=catalog,
    )
