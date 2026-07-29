import hashlib

import pytest

from veriformis.errors import DuplicateIdentityError, InvalidSourceLocatorError
from veriformis.identity import (
    canonical_digest,
    canonical_json_bytes,
    derive_artifact_id,
    derive_id,
    derive_source_id,
    lossless_json_bytes,
    normalize_logical_path,
)
from veriformis.sources import register_source
from veriformis.workspace import ArtifactRef, SourceDescriptor


def test_durable_identity_is_key_order_independent_and_unicode_exact():
    composed = {"name": "café", "nested": {"b": 2, "a": 1}}
    decomposed = {"nested": {"a": 1, "b": 2}, "name": "cafe\u0301"}

    assert canonical_json_bytes(composed) == canonical_json_bytes(decomposed)
    assert canonical_digest(composed) != canonical_digest(decomposed)
    assert lossless_json_bytes(composed) != lossless_json_bytes(decomposed)
    assert derive_id("cfg", composed) != derive_id("cfg", decomposed)


def test_full_domain_separated_ids_are_stable_and_distinct_by_kind():
    payload = {"value": "same"}

    first = derive_id("chk", payload)
    assert first == derive_id("chk", payload)
    assert first != derive_id("trn", payload)
    assert first.startswith("chk-v1-")
    assert len(first.removeprefix("chk-v1-")) == 64


def test_duplicate_content_sources_have_distinct_instance_ids():
    raw_sha = hashlib.sha256(b"identical bytes").hexdigest()

    first = derive_source_id("alpha/notes.txt", raw_sha)
    second = derive_source_id("beta/notes.txt", raw_sha)

    assert first != second
    assert first == derive_source_id("alpha/notes.txt", raw_sha)


@pytest.mark.parametrize(
    "path",
    ["", "/absolute.txt", "../escape.txt", "a/../escape.txt", "a//b.txt", "C:/raw.txt"],
)
def test_logical_source_path_rejects_aliases_and_escape(path):
    with pytest.raises(InvalidSourceLocatorError):
        normalize_logical_path(path)


def test_logical_source_path_rejects_backslash_instead_of_aliasing_posix_path():
    raw_sha = hashlib.sha256(b"same bytes").hexdigest()

    nested = derive_source_id("section/source.txt", raw_sha)
    with pytest.raises(InvalidSourceLocatorError, match="POSIX separators"):
        derive_source_id(r"section\source.txt", raw_sha)

    assert nested == derive_source_id("section/source.txt", raw_sha)


@pytest.mark.parametrize(
    "logical_path", [None, "", "/tmp/source.txt", r"tmp\source.txt"]
)
def test_source_registration_requires_explicit_workspace_relative_locator(
    logical_path,
):
    with pytest.raises(InvalidSourceLocatorError):
        register_source(
            "/tmp/source.txt",
            "text",
            "same bytes",
            logical_path=logical_path,
            raw_bytes=b"same bytes",
        )


def test_registration_does_not_collapse_absolute_and_relative_locators():
    relative = register_source(
        "/tmp/source.txt",
        "text",
        "same bytes",
        logical_path="tmp/source.txt",
        raw_bytes=b"same bytes",
    )

    assert relative.logical_path == "tmp/source.txt"
    with pytest.raises(InvalidSourceLocatorError):
        register_source(
            "/tmp/source.txt",
            "text",
            "same bytes",
            logical_path="/tmp/source.txt",
            raw_bytes=b"same bytes",
        )


def test_registration_never_invents_a_locator_from_the_host_path():
    with pytest.raises(TypeError, match="logical_path"):
        register_source(
            "/tmp/source.txt",
            "text",
            "same bytes",
            raw_bytes=b"same bytes",
        )


def test_artifact_identity_is_source_order_independent():
    digest = hashlib.sha256(b"artifact").hexdigest()
    config_digest = canonical_digest({"size": 100})
    raw_sha = hashlib.sha256(b"raw").hexdigest()
    source_a = derive_source_id("a.txt", raw_sha)
    source_b = derive_source_id("b.txt", raw_sha)

    first = derive_artifact_id(
        kind="chunks",
        content_sha256=digest,
        source_ids=[source_a, source_b],
        producer_id="paragraph",
        producer_version="1",
        config_digest=config_digest,
    )
    second = derive_artifact_id(
        kind="chunks",
        content_sha256=digest,
        source_ids=[source_b, source_a],
        producer_id="paragraph",
        producer_version="1",
        config_digest=config_digest,
    )

    assert first == second


def test_artifact_identity_binds_content_producer_config_and_scope():
    source_sha = hashlib.sha256(b"raw").hexdigest()
    source_id = derive_source_id("doc.txt", source_sha)
    other_source_id = derive_source_id("other.txt", source_sha)
    base = ArtifactRef.from_bytes(
        b"payload",
        kind="document-ir",
        media_type="application/json",
        source_ids=[source_id],
        producer_id="text-parser",
        producer_version="1",
        config={"mode": "strict"},
    )

    variants = {
        ArtifactRef.from_bytes(
            b"changed",
            kind="document-ir",
            media_type="application/json",
            source_ids=[source_id],
            producer_id="text-parser",
            producer_version="1",
            config={"mode": "strict"},
        ).id,
        ArtifactRef.from_bytes(
            b"payload",
            kind="document-ir",
            media_type="application/json",
            source_ids=[source_id],
            producer_id="text-parser",
            producer_version="2",
            config={"mode": "strict"},
        ).id,
        ArtifactRef.from_bytes(
            b"payload",
            kind="document-ir",
            media_type="application/json",
            source_ids=[source_id],
            producer_id="text-parser",
            producer_version="1",
            config={"mode": "lenient"},
        ).id,
        ArtifactRef.from_bytes(
            b"payload",
            kind="document-ir",
            media_type="application/json",
            source_ids=[other_source_id],
            producer_id="text-parser",
            producer_version="1",
            config={"mode": "strict"},
        ).id,
    }

    assert base.id not in variants
    assert len(variants) == 4


def test_artifact_config_identity_preserves_unicode_normalization():
    composed = ArtifactRef.from_bytes(
        b"same payload",
        kind="cleaning-plan",
        media_type="application/json",
        producer_id="veriformis.cleaner",
        producer_version="1",
        config={"pattern": "é"},
    )
    decomposed = ArtifactRef.from_bytes(
        b"same payload",
        kind="cleaning-plan",
        media_type="application/json",
        producer_id="veriformis.cleaner",
        producer_version="1",
        config={"pattern": "e\u0301"},
    )

    assert composed.config_digest != decomposed.config_digest
    assert composed.id != decomposed.id


def test_source_descriptor_rejects_identity_payload_mismatch():
    raw_sha = hashlib.sha256(b"raw").hexdigest()

    with pytest.raises(DuplicateIdentityError):
        SourceDescriptor(
            id=derive_source_id("other.txt", raw_sha),
            logical_path="doc.txt",
            sha256=raw_sha,
            size=3,
            parser_id="text",
            parser_version="1",
        )
