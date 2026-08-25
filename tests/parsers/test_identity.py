"""Pinned parser identities and recovery-quality vocabulary."""

from __future__ import annotations

from veriformis.diagnostics import make_parse_report
from veriformis.identity import derive_source_id, sha256_digest
from veriformis.parsers.identity import (
    PARSER_KIND_VERSIONS,
    RECOVERY_QUALITY_STATUSES,
    parser_identities,
)


def test_parser_identities_cover_every_implemented_kind() -> None:
    identities = parser_identities()
    assert set(identities) == set(PARSER_KIND_VERSIONS)
    for kind, pin in identities.items():
        assert pin["parser"] == kind
        assert pin["parser_version"] == PARSER_KIND_VERSIONS[kind]
        assert pin["recovery_quality_status"] == list(RECOVERY_QUALITY_STATUSES)


def test_parse_report_status_is_the_recovery_quality_fact() -> None:
    complete = make_parse_report(
        source_id=derive_source_id("note.txt", sha256_digest(b"x")),
        parser_name="text",
        parser_version=PARSER_KIND_VERSIONS["text"],
    )
    assert complete.status == "complete"
    assert complete.parser_version == PARSER_KIND_VERSIONS["text"]
