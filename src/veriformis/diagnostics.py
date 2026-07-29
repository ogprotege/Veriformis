"""Versioned, deterministic parser diagnostics.

Diagnostics describe every known normalization, omission, degradation, or
refusal without pretending that every input format has raw byte offsets.
"""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import PurePosixPath
from dataclasses import asdict, dataclass, field
from typing import Any
from typing import Literal

from lxml import etree

from veriformis.errors import ParseError
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    validate_id,
    validate_sha256,
)

Severity = Literal["info", "warning", "error"]
Disposition = Literal["preserved", "normalized", "omitted", "refused"]
LossKind = Literal["none", "presentation", "metadata", "structure", "text", "unknown"]


@dataclass(frozen=True)
class DiagnosticLocation:
    """A truthful format-native location for one parser observation."""

    kind: Literal["source", "text", "ooxml"]
    line_start: int | None = None
    line_end: int | None = None
    column_start: int | None = None
    column_end: int | None = None
    raw_byte_start: int | None = None
    raw_byte_end: int | None = None
    part: str | None = None
    xpath: str | None = None

    def __post_init__(self) -> None:
        _validate_location_shape(self)


def _validate_pair(
    location: DiagnosticLocation,
    start_name: str,
    end_name: str,
    *,
    minimum: int,
) -> bool:
    start = getattr(location, start_name)
    end = getattr(location, end_name)
    if (start is None) != (end is None):
        raise ValueError(
            f"diagnostic location requires both {start_name} and {end_name}"
        )
    if start is None:
        return False
    if type(start) is not int or type(end) is not int:
        raise ValueError(
            f"diagnostic location {start_name}/{end_name} must be integers"
        )
    if start < minimum or end < minimum or end < start:
        raise ValueError(
            f"diagnostic location {start_name}/{end_name} is backward or invalid"
        )
    return True


def _validate_location_shape(location: DiagnosticLocation) -> None:
    """Enforce the exact coordinate shape for each v1 location kind."""
    if location.kind not in {"source", "text", "ooxml"}:
        raise ValueError("diagnostic location kind is invalid")

    has_lines = _validate_pair(
        location,
        "line_start",
        "line_end",
        minimum=1,
    )
    has_columns = _validate_pair(
        location,
        "column_start",
        "column_end",
        minimum=1,
    )
    has_raw_bytes = _validate_pair(
        location,
        "raw_byte_start",
        "raw_byte_end",
        minimum=0,
    )

    if location.kind == "text":
        if not has_lines and not has_raw_bytes:
            raise ValueError(
                "text diagnostic location requires a line or raw-byte range"
            )
        if has_columns and not has_lines:
            raise ValueError("text diagnostic columns require a line range")
        if location.part is not None or location.xpath is not None:
            raise ValueError("text diagnostic location cannot carry OOXML coordinates")
        return

    if location.kind == "ooxml":
        if has_lines or has_columns or has_raw_bytes:
            raise ValueError(
                "OOXML diagnostic location cannot carry text or raw-byte coordinates"
            )
        if (
            not isinstance(location.part, str)
            or not location.part.strip()
            or not isinstance(location.xpath, str)
            or not location.xpath.strip()
        ):
            raise ValueError(
                "OOXML diagnostic location requires nonempty part and xpath"
            )
        return

    if has_lines or has_columns or has_raw_bytes:
        raise ValueError(
            "source diagnostic location cannot carry text or raw-byte coordinates"
        )
    if location.part is not None or location.xpath is not None:
        raise ValueError("source diagnostic location cannot carry OOXML coordinates")


@dataclass(frozen=True)
class ParseDiagnostic:
    diagnostic_id: str
    code: str
    severity: Severity
    disposition: Disposition
    loss_kind: LossKind
    source_id: str
    location: DiagnosticLocation
    message: str
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ParseReport:
    schema_version: str
    source_id: str
    parser_name: str
    parser_version: str
    status: Literal["complete", "degraded", "refused"]
    diagnostics: tuple[ParseDiagnostic, ...]
    report_digest: str


def validate_parse_report_locations(
    report: ParseReport,
    raw_bytes: bytes,
) -> None:
    """Bind every text coordinate in a report to its captured input bytes.

    Schema loading proves that coordinate pairs are complete and ordered.
    This check adds the source-dependent proof that raw-byte, line, and column
    bounds actually exist in the immutable input consumed by the parser.
    """
    text_lines: list[str] | None = None
    archive: zipfile.ZipFile | None = None
    parsed_parts: dict[str, etree._ElementTree] = {}
    try:
        for diagnostic in report.diagnostics:
            location = diagnostic.location
            _validate_location_shape(location)
            if location.kind == "ooxml":
                if report.parser_name != "docx":
                    raise ParseError(
                        "OOXML diagnostic location requires the DOCX parser"
                    )
                if archive is None:
                    try:
                        archive = zipfile.ZipFile(BytesIO(raw_bytes))
                    except zipfile.BadZipFile as exc:
                        raise ParseError(
                            "OOXML diagnostic location requires a valid ZIP package"
                        ) from exc
                _validate_ooxml_diagnostic(
                    diagnostic,
                    archive,
                    parsed_parts,
                )
                continue
            if location.kind != "text":
                continue

            if location.raw_byte_start is not None:
                assert location.raw_byte_end is not None
                if location.raw_byte_end > len(raw_bytes):
                    raise ParseError(
                        f"diagnostic {diagnostic.diagnostic_id} raw-byte range exceeds "
                        "the captured source"
                    )

            if location.line_start is None:
                continue
            assert location.line_end is not None
            if text_lines is None:
                try:
                    decoded = raw_bytes.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ParseError(
                        "text diagnostic locations require UTF-8 source bytes"
                    ) from exc
                text_lines = decoded.splitlines()
                if not text_lines:
                    text_lines = [""]
                elif decoded.endswith(("\n", "\r")):
                    text_lines.append("")
            if location.line_end > len(text_lines):
                raise ParseError(
                    f"diagnostic {diagnostic.diagnostic_id} line range exceeds "
                    "the captured source"
                )
            if location.column_start is None:
                continue
            assert location.column_end is not None
            start_line = text_lines[location.line_start - 1]
            end_line = text_lines[location.line_end - 1]
            if (
                location.column_start > len(start_line) + 1
                or location.column_end > len(end_line) + 1
            ):
                raise ParseError(
                    f"diagnostic {diagnostic.diagnostic_id} column range exceeds "
                    "the captured source"
                )
    finally:
        if archive is not None:
            archive.close()


def _validate_ooxml_diagnostic(
    diagnostic: ParseDiagnostic,
    archive: zipfile.ZipFile,
    parsed_parts: dict[str, etree._ElementTree],
) -> None:
    location = diagnostic.location
    assert location.part is not None and location.xpath is not None
    part = location.part
    pure = PurePosixPath(part)
    if (
        not part
        or part.startswith("/")
        or "\\" in part
        or any(item in {"", ".", ".."} for item in pure.parts)
        or pure.as_posix() != part
    ):
        raise ParseError("OOXML diagnostic part is not a safe package path")

    names = archive.namelist()
    if location.xpath == "/":
        if (
            not diagnostic.code.endswith("-part-invalid")
            or diagnostic.disposition != "refused"
            or diagnostic.severity != "error"
            or diagnostic.details.get("reason") not in {"unreadable", "invalid-xml"}
        ):
            raise ParseError(
                "root OOXML locator is reserved for an invalid-part refusal"
            )
        reason = diagnostic.details["reason"]
        if names.count(part) == 0:
            if reason != "unreadable":
                raise ParseError("missing OOXML part has the wrong refusal reason")
            return
        if names.count(part) != 1:
            return
        try:
            data = archive.read(part)
        except (KeyError, RuntimeError, OSError):
            if reason != "unreadable":
                raise ParseError("unreadable OOXML part has the wrong refusal reason")
            return
        try:
            etree.fromstring(data)
        except etree.XMLSyntaxError:
            if reason != "invalid-xml":
                raise ParseError("invalid OOXML XML has the wrong refusal reason")
            return
        raise ParseError("invalid-part refusal points to a valid OOXML part")

    if names.count(part) != 1:
        raise ParseError("OOXML diagnostic part does not exist exactly once")
    tree = parsed_parts.get(part)
    if tree is None:
        try:
            root = etree.fromstring(
                archive.read(part),
                parser=etree.XMLParser(
                    resolve_entities=False,
                    no_network=True,
                    recover=False,
                ),
            )
        except (KeyError, etree.XMLSyntaxError, OSError) as exc:
            raise ParseError("OOXML diagnostic part is not parseable XML") from exc
        tree = root.getroottree()
        parsed_parts[part] = tree
    namespaces = {
        prefix: uri
        for prefix, uri in tree.getroot().nsmap.items()
        if prefix is not None
    }
    try:
        matched = tree.xpath(location.xpath, namespaces=namespaces)
    except etree.XPathError as exc:
        raise ParseError("OOXML diagnostic xpath is invalid") from exc
    if not matched:
        raise ParseError("OOXML diagnostic xpath does not resolve to a node")


def make_diagnostic(
    *,
    source_id: str,
    parser_name: str,
    parser_version: str,
    code: str,
    severity: Severity,
    disposition: Disposition,
    loss_kind: LossKind,
    location: DiagnosticLocation,
    message: str,
    details: dict | None = None,
) -> ParseDiagnostic:
    payload = {
        "source_id": source_id,
        "parser_name": parser_name,
        "parser_version": parser_version,
        "code": code,
        "severity": severity,
        "disposition": disposition,
        "loss_kind": loss_kind,
        "location": asdict(location),
        "message": message,
        "details": details or {},
    }
    return ParseDiagnostic(
        diagnostic_id=derive_id("diag", payload),
        code=code,
        severity=severity,
        disposition=disposition,
        loss_kind=loss_kind,
        source_id=source_id,
        location=location,
        message=message,
        details=details or {},
    )


def make_parse_report(
    *,
    source_id: str,
    parser_name: str,
    parser_version: str,
    diagnostics: list[ParseDiagnostic] | tuple[ParseDiagnostic, ...] = (),
) -> ParseReport:
    ordered = tuple(sorted(diagnostics, key=lambda item: item.diagnostic_id))
    diagnostic_ids = [item.diagnostic_id for item in ordered]
    if len(diagnostic_ids) != len(set(diagnostic_ids)):
        raise ParseError("parse report contains duplicate diagnostic identities")
    if any(item.severity == "error" for item in ordered):
        status: Literal["complete", "degraded", "refused"] = "refused"
    elif ordered:
        status = "degraded"
    else:
        status = "complete"
    payload = {
        "schema_version": "veriformis.parse-report/v1",
        "source_id": source_id,
        "parser_name": parser_name,
        "parser_version": parser_version,
        "status": status,
        "diagnostics": [asdict(item) for item in ordered],
    }
    return ParseReport(
        report_digest=canonical_digest(payload),
        diagnostics=ordered,
        **{key: value for key, value in payload.items() if key != "diagnostics"},
    )


def parse_report_to_dict(report: ParseReport) -> dict[str, Any]:
    """Serialize and verify an exact v1 parse report."""
    value = json.loads(lossless_json_bytes(asdict(report)).decode("utf-8"))
    if parse_report_from_dict(value) != report:
        raise ParseError("parse report does not round-trip through its v1 schema")
    return value


def parse_report_from_dict(value: dict[str, Any]) -> ParseReport:
    """Strictly load a v1 report and recompute every durable identity."""
    top_keys = {
        "schema_version",
        "source_id",
        "parser_name",
        "parser_version",
        "status",
        "diagnostics",
        "report_digest",
    }
    diagnostic_keys = {
        "diagnostic_id",
        "code",
        "severity",
        "disposition",
        "loss_kind",
        "source_id",
        "location",
        "message",
        "details",
    }
    location_keys = {
        "kind",
        "line_start",
        "line_end",
        "column_start",
        "column_end",
        "raw_byte_start",
        "raw_byte_end",
        "part",
        "xpath",
    }
    try:
        if not isinstance(value, dict) or set(value) != top_keys:
            raise ParseError("parse report keys do not match the v1 schema")
        if value["schema_version"] != "veriformis.parse-report/v1":
            raise ParseError("unsupported parse report schema")
        validate_id(value["source_id"], kind="src")
        validate_sha256(value["report_digest"])
        if not isinstance(value["parser_name"], str) or not value["parser_name"]:
            raise ParseError("parse report parser name is invalid")
        if not isinstance(value["parser_version"], str) or not value["parser_version"]:
            raise ParseError("parse report parser version is invalid")
        if value["status"] not in {"complete", "degraded", "refused"}:
            raise ParseError("parse report status is invalid")
        if not isinstance(value["diagnostics"], list):
            raise ParseError("parse report diagnostics must be an array")

        diagnostics: list[ParseDiagnostic] = []
        for item in value["diagnostics"]:
            if not isinstance(item, dict) or set(item) != diagnostic_keys:
                raise ParseError("parse diagnostic keys do not match the v1 schema")
            if (
                not isinstance(item["location"], dict)
                or set(item["location"]) != location_keys
            ):
                raise ParseError("diagnostic location keys do not match the v1 schema")
            if item["source_id"] != value["source_id"]:
                raise ParseError("parse diagnostic source does not match its report")
            validate_id(item["diagnostic_id"], kind="diag")
            if item["severity"] not in {"info", "warning", "error"}:
                raise ParseError("parse diagnostic severity is invalid")
            if item["disposition"] not in {
                "preserved",
                "normalized",
                "omitted",
                "refused",
            }:
                raise ParseError("parse diagnostic disposition is invalid")
            if item["loss_kind"] not in {
                "none",
                "presentation",
                "metadata",
                "structure",
                "text",
                "unknown",
            }:
                raise ParseError("parse diagnostic loss kind is invalid")
            if not isinstance(item["code"], str) or not item["code"]:
                raise ParseError("parse diagnostic code is invalid")
            if not isinstance(item["message"], str) or not item["message"]:
                raise ParseError("parse diagnostic message is invalid")
            if not isinstance(item["details"], dict):
                raise ParseError("parse diagnostic details must be an object")
            lossless_json_bytes(item["details"])
            location_value = item["location"]
            if location_value["kind"] not in {"source", "text", "ooxml"}:
                raise ParseError("diagnostic location kind is invalid")
            for field_name in (
                "line_start",
                "line_end",
                "column_start",
                "column_end",
                "raw_byte_start",
                "raw_byte_end",
            ):
                number = location_value[field_name]
                if number is not None and (type(number) is not int or number < 0):
                    raise ParseError(f"diagnostic location {field_name} is invalid")
            for field_name in ("part", "xpath"):
                text = location_value[field_name]
                if text is not None and not isinstance(text, str):
                    raise ParseError(f"diagnostic location {field_name} is invalid")
            location = DiagnosticLocation(**location_value)
            expected = make_diagnostic(
                source_id=value["source_id"],
                parser_name=value["parser_name"],
                parser_version=value["parser_version"],
                code=item["code"],
                severity=item["severity"],
                disposition=item["disposition"],
                loss_kind=item["loss_kind"],
                location=location,
                message=item["message"],
                details=item["details"],
            )
            if expected.diagnostic_id != item["diagnostic_id"]:
                raise ParseError("parse diagnostic identity mismatch")
            diagnostics.append(expected)

        expected_report = make_parse_report(
            source_id=value["source_id"],
            parser_name=value["parser_name"],
            parser_version=value["parser_version"],
            diagnostics=diagnostics,
        )
        if tuple(item.diagnostic_id for item in diagnostics) != tuple(
            item.diagnostic_id for item in expected_report.diagnostics
        ):
            raise ParseError("parse diagnostics are not in canonical order")
        if (
            value["status"] != expected_report.status
            or value["report_digest"] != expected_report.report_digest
        ):
            raise ParseError("parse report status or digest mismatch")
        return expected_report
    except ParseError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ParseError(f"invalid parse report: {exc}") from exc
