"""Phase 16.6: split-jsonl-directory is bound only through the protocol."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from veriformis.errors import ExtensionProtocolError
from veriformis.exports.service import ExportService
from veriformis.exports.split_jsonl import SPLIT_JSONL_IMPLEMENTATION
from veriformis.extensions import bound_split_jsonl_exporter


def test_generic_split_jsonl_is_the_catalog_object() -> None:
    service = ExportService()
    bound = bound_split_jsonl_exporter(catalog=service._catalog())
    catalog_item = next(
        item
        for item in service._catalog()
        if item.descriptor.container_profile.container_id == "split-jsonl-directory"
        and item.descriptor.consumer_profile is None
    )
    assert bound is catalog_item
    assert bound is SPLIT_JSONL_IMPLEMENTATION


def test_resolve_generic_split_jsonl_uses_the_protocol() -> None:
    source = inspect.getsource(ExportService._resolve_implementation)
    assert "bound_split_jsonl_exporter" in source
    assert "split-jsonl-directory" in source
    assert "request.consumer_id is None" in source
    assert "for implementation in self._catalog()" in source


def test_other_containers_and_profiles_stay_on_the_private_catalog() -> None:
    source = inspect.getsource(ExportService._resolve_implementation)
    assert source.index("bound_split_jsonl_exporter") < source.index(
        "for implementation in self._catalog()"
    )
    assert "canonical-json" not in source
    assert "constrained-csv" not in source
    assert "parquet" not in source
    catalog = ExportService()._catalog()
    profiled = next(
        item
        for item in catalog
        if item.descriptor.container_profile.container_id == "split-jsonl-directory"
        and item.descriptor.consumer_profile is not None
    )
    generic = bound_split_jsonl_exporter(catalog=catalog)
    assert profiled is not generic
    assert profiled.descriptor.consumer_profile is not None


def test_unknown_split_jsonl_contract_version_names_supported_version() -> None:
    tampered = SimpleNamespace(
        kind="container-exporter",
        origin="builtin",
        contract_version=2,
        discovery=SimpleNamespace(selector="split-jsonl-directory"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match=r"unknown extension contract version: requested 2, supported 1 \(veriformis.extension-protocol/v1\)",
    ):
        bound_split_jsonl_exporter(
            catalog=ExportService()._catalog(),
            declaration=tampered,  # type: ignore[arg-type]
        )


def test_third_party_split_jsonl_origin_is_refused() -> None:
    tampered = SimpleNamespace(
        kind="container-exporter",
        origin="third_party",
        contract_version=1,
        discovery=SimpleNamespace(selector="split-jsonl-directory"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match="split-jsonl-directory selection requires a builtin container-exporter declaration",
    ):
        bound_split_jsonl_exporter(
            catalog=ExportService()._catalog(),
            declaration=tampered,  # type: ignore[arg-type]
        )


def test_missing_generic_split_jsonl_catalog_entry_fails_closed() -> None:
    with pytest.raises(
        ExtensionProtocolError,
        match="split-jsonl-directory is missing from the internal export catalog",
    ):
        bound_split_jsonl_exporter(catalog=())
