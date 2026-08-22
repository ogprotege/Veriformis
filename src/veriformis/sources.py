"""Source registration: every ingested file gets a hash-pinned identity."""

from __future__ import annotations

import errno
import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from veriformis.contracts import CANONICAL_STREAM_CONTRACT_VERSION
from veriformis.diagnostics import ParseReport, make_parse_report
from veriformis.errors import InvalidSourceLocatorError
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    derive_source_id,
    normalize_logical_path,
    sha256_digest,
)


@dataclass(frozen=True)
class SourceRef:
    id: str
    path: str
    sha256: str
    size: int
    parser: str
    extracted_text: str  # in-session only; spans index into this stream
    logical_path: str = ""
    parser_version: str = "1"
    canonical_stream_contract_version: int = CANONICAL_STREAM_CONTRACT_VERSION
    stream_sha256: str = ""
    artifact_id: str = ""


@dataclass(frozen=True)
class ParseResult:
    document: "object"  # veriformis.ir.Document (avoid import cycle at type level)
    source: SourceRef
    diagnostics: ParseReport


@dataclass(frozen=True)
class SourceCapture:
    """One source result from a root-pinned, single-read batch capture."""

    path: Path
    logical_path: str
    raw_bytes: bytes | None
    error: OSError | InvalidSourceLocatorError | None

    def __post_init__(self) -> None:
        if (self.raw_bytes is None) == (self.error is None):
            raise ValueError("source capture must contain bytes or one error")


@dataclass(frozen=True)
class _PinnedSource:
    """An unread regular-file descriptor pinned below the selected root."""

    root_descriptor: int
    source_descriptor: int
    before: os.stat_result

    @property
    def identity(self) -> tuple[int, int]:
        return self.before.st_dev, self.before.st_ino


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _source_root(source_root: Path | None) -> tuple[Path, tuple[int, int]]:
    root = _absolute(source_root or Path.cwd())
    try:
        observed = os.stat(root)
    except OSError as exc:
        raise InvalidSourceLocatorError("source root is not a directory") from exc
    if not stat.S_ISDIR(observed.st_mode):
        raise InvalidSourceLocatorError("source root is not a directory")
    return root, (observed.st_dev, observed.st_ino)


def _relative_to_root(path: Path, root: Path) -> Path:
    absolute = _absolute(path)
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise InvalidSourceLocatorError(
            "source is outside source root; pass --source-root explicitly"
        ) from exc
    if not relative.parts:
        raise InvalidSourceLocatorError("source path names the source root")
    return relative


def safe_logical_locators(
    paths: list[Path],
    *,
    source_root: Path | None,
) -> tuple[str, ...]:
    """Return non-sensitive labels for a batch-level locator failure."""
    root = _absolute(source_root or Path.cwd())
    labels: list[str] = []
    for index, path in enumerate(paths):
        absolute = _absolute(path)
        try:
            relative = absolute.relative_to(root)
        except ValueError:
            relative = None
        candidates = []
        if relative is not None and relative.parts:
            candidates.append(relative)
        if path.name:
            candidates.append(path.name)
        candidates.append(f"source-{index + 1}")
        for candidate in candidates:
            try:
                label = normalize_logical_path(candidate)
            except InvalidSourceLocatorError:
                continue
            labels.append(label)
            break
    return tuple(labels)


def _reject_visible_symlink(logical_path: str, root: Path, relative: Path) -> None:
    cursor = root
    for component in relative.parts:
        cursor /= component
        try:
            observed = os.lstat(cursor)
        except FileNotFoundError:
            return
        if stat.S_ISLNK(observed.st_mode):
            raise InvalidSourceLocatorError(
                f"source symlinks are not allowed: {logical_path!r}"
            )


def _derive_logical_paths(
    paths: list[Path],
    *,
    source_root: Path | None,
    reject_visible_symlinks: bool,
) -> tuple[Path, tuple[int, int], dict[Path, str], dict[Path, Path]]:
    root, root_identity = _source_root(source_root)
    logical: dict[Path, str] = {}
    relatives: dict[Path, Path] = {}
    absolute_seen: dict[Path, str] = {}
    locator_seen: set[str] = set()
    for path in paths:
        absolute = _absolute(path)
        relative = _relative_to_root(path, root)
        locator = normalize_logical_path(relative)
        previous_locator = absolute_seen.get(absolute)
        if previous_locator is not None:
            raise InvalidSourceLocatorError(
                f"source inputs {previous_locator!r} and {locator!r} resolve to "
                "the same file"
            )
        if locator in locator_seen:
            raise InvalidSourceLocatorError(
                f"source inputs resolve to the same logical path {locator!r}"
            )
        if reject_visible_symlinks:
            _reject_visible_symlink(locator, root, relative)
        absolute_seen[absolute] = locator
        locator_seen.add(locator)
        logical[path] = locator
        relatives[path] = relative
    return root, root_identity, logical, relatives


def _directory_open_flags() -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _open_directory_at(
    parent_descriptor: int,
    component: str,
    *,
    logical_path: str | None,
) -> int:
    try:
        return os.open(
            component,
            _directory_open_flags(),
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            if logical_path is None:
                raise InvalidSourceLocatorError(
                    "source root contains a symlink during capture"
                ) from exc
            raise InvalidSourceLocatorError(
                f"source symlinks are not allowed: {logical_path!r}"
            ) from exc
        raise


def _open_resolved_root(
    resolved_root: Path,
    *,
    selected_identity: tuple[int, int],
) -> int:
    """Pin every component of a resolved absolute root without following links."""
    try:
        expected = os.stat(resolved_root, follow_symlinks=False)
    except OSError as exc:
        raise InvalidSourceLocatorError(
            "source root could not be inspected as a directory"
        ) from exc
    if not stat.S_ISDIR(expected.st_mode):
        raise InvalidSourceLocatorError("source root is not a directory")
    if (expected.st_dev, expected.st_ino) != selected_identity:
        raise InvalidSourceLocatorError("source root changed during capture")

    descriptor = os.open("/", _directory_open_flags())
    try:
        for component in resolved_root.parts[1:]:
            next_descriptor = _open_directory_at(
                descriptor,
                component,
                logical_path=None,
            )
            os.close(descriptor)
            descriptor = next_descriptor
        observed = os.fstat(descriptor)
        if (observed.st_dev, observed.st_ino) != selected_identity:
            raise InvalidSourceLocatorError("source root changed during capture")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


_SOURCE_STABILITY_FIELDS = (
    "st_dev",
    "st_ino",
    "st_size",
    "st_mtime_ns",
    "st_ctime_ns",
)


def _open_source_at(
    root_descriptor: int,
    relative: Path,
    logical_path: str,
) -> tuple[int, os.stat_result]:
    directory_descriptor = os.dup(root_descriptor)
    try:
        for component in relative.parts[:-1]:
            next_descriptor = _open_directory_at(
                directory_descriptor,
                component,
                logical_path=logical_path,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        try:
            source_descriptor = os.open(
                relative.parts[-1],
                flags,
                dir_fd=directory_descriptor,
            )
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise InvalidSourceLocatorError(
                    f"source symlinks are not allowed: {logical_path!r}"
                ) from exc
            raise
        try:
            observed = os.fstat(source_descriptor)
            if not stat.S_ISREG(observed.st_mode):
                raise InvalidSourceLocatorError(
                    f"source is not a regular file: {logical_path!r}"
                )
            return source_descriptor, observed
        except BaseException:
            os.close(source_descriptor)
            raise
    finally:
        os.close(directory_descriptor)


def _pin_source_at(
    root_descriptor: int,
    relative: Path,
    logical_path: str,
) -> _PinnedSource:
    source_descriptor, before = _open_source_at(
        root_descriptor,
        relative,
        logical_path,
    )
    return _PinnedSource(
        root_descriptor=root_descriptor,
        source_descriptor=source_descriptor,
        before=before,
    )


def _same_source_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
    return all(
        getattr(left, field) == getattr(right, field)
        for field in _SOURCE_STABILITY_FIELDS
    )


def _capture_at(
    pinned: _PinnedSource,
    relative: Path,
    logical_path: str,
) -> tuple[bytes, tuple[int, int]]:
    """Validate one pinned locator, then read its body exactly once."""
    verification_descriptor, locator_observation = _open_source_at(
        pinned.root_descriptor,
        relative,
        logical_path,
    )
    try:
        if not _same_source_snapshot(pinned.before, locator_observation):
            raise InvalidSourceLocatorError(
                f"source changed during capture: {logical_path!r}"
            )
    finally:
        os.close(verification_descriptor)

    before_read = os.fstat(pinned.source_descriptor)
    if not _same_source_snapshot(pinned.before, before_read):
        raise InvalidSourceLocatorError(
            f"source changed during capture: {logical_path!r}"
        )
    with os.fdopen(pinned.source_descriptor, "rb", closefd=False) as stream:
        raw_bytes = stream.read()
    after_read = os.fstat(pinned.source_descriptor)
    if not _same_source_snapshot(pinned.before, after_read):
        raise InvalidSourceLocatorError(
            f"source changed during capture: {logical_path!r}"
        )
    return raw_bytes, pinned.identity


def capture_source_batch(
    paths: list[Path],
    *,
    source_root: Path | None,
) -> tuple[SourceCapture, ...]:
    """Capture a batch below one pinned root without following child links."""
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise InvalidSourceLocatorError(
            "this platform cannot safely capture source-root-relative files"
        )
    root, root_identity, logical, relatives = _derive_logical_paths(
        paths,
        source_root=source_root,
        reject_visible_symlinks=False,
    )
    try:
        resolved_root = root.resolve()
    except (OSError, RuntimeError) as exc:
        raise InvalidSourceLocatorError(
            "source root could not be resolved as a directory"
        ) from exc
    try:
        root_descriptor = _open_resolved_root(
            resolved_root,
            selected_identity=root_identity,
        )
    except InvalidSourceLocatorError:
        raise
    except OSError as exc:
        raise InvalidSourceLocatorError(
            "source root could not be opened as a directory"
        ) from exc
    pinned_sources: list[tuple[int, Path, str, Path, _PinnedSource]] = []
    try:
        captured: list[SourceCapture | None] = [None] * len(paths)
        identities: dict[tuple[int, int], str] = {}
        for index, path in enumerate(paths):
            try:
                pinned = _pin_source_at(
                    root_descriptor,
                    relatives[path],
                    logical[path],
                )
            except (InvalidSourceLocatorError, OSError) as exc:
                captured[index] = SourceCapture(
                    path=path,
                    logical_path=logical[path],
                    raw_bytes=None,
                    error=exc,
                )
            else:
                pinned_sources.append(
                    (index, path, logical[path], relatives[path], pinned)
                )
                previous_locator = identities.get(pinned.identity)
                if previous_locator is not None:
                    raise InvalidSourceLocatorError(
                        f"source inputs {previous_locator!r} and {logical[path]!r} "
                        "identify the same filesystem file; hard-link and case "
                        "aliases are not allowed"
                    )
                identities[pinned.identity] = logical[path]

        for index, path, logical_path, relative, pinned in pinned_sources:
            try:
                raw_bytes, _ = _capture_at(
                    pinned,
                    relative,
                    logical_path,
                )
            except (InvalidSourceLocatorError, OSError) as exc:
                captured[index] = SourceCapture(
                    path=path,
                    logical_path=logical_path,
                    raw_bytes=None,
                    error=exc,
                )
            else:
                captured[index] = SourceCapture(
                    path=path,
                    logical_path=logical_path,
                    raw_bytes=raw_bytes,
                    error=None,
                )
        if any(item is None for item in captured):
            raise InvalidSourceLocatorError("source capture did not produce a verdict")
        return tuple(item for item in captured if item is not None)
    finally:
        for _, _, _, _, pinned in pinned_sources:
            os.close(pinned.source_descriptor)
        os.close(root_descriptor)


def derive_logical_paths(
    paths: list[Path],
    *,
    source_root: Path | None,
) -> dict[Path, str]:
    """Derive source locators from one explicit root.

    Parse and compile preflight share this boundary so source membership and
    logical identity cannot diverge merely because a caller used a different
    surface. Resolving paths also makes a symlink that escapes the root fail
    closed before any source bytes are accepted.
    """
    _, _, logical, _ = _derive_logical_paths(
        paths,
        source_root=source_root,
        reject_visible_symlinks=True,
    )
    return logical


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_source(
    path: str | Path,
    parser: str,
    extracted_text: str,
    *,
    logical_path: str,
    parser_version: str = "1",
    canonical_stream_contract_version: int = CANONICAL_STREAM_CONTRACT_VERSION,
    raw_bytes: bytes | None = None,
) -> SourceRef:
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    digest = hashlib.sha256(captured).hexdigest()
    locator = normalize_logical_path(logical_path)
    source_id = derive_source_id(locator, digest)
    stream_digest = sha256_digest(extracted_text)
    config_digest = canonical_digest(
        {
            "parser": parser,
            "parser_version": parser_version,
            "canonical_stream_contract_version": canonical_stream_contract_version,
        }
    )
    return SourceRef(
        id=source_id,
        path=str(p),
        sha256=digest,
        size=len(captured),
        parser=parser,
        extracted_text=extracted_text,
        logical_path=locator,
        parser_version=parser_version,
        canonical_stream_contract_version=canonical_stream_contract_version,
        stream_sha256=stream_digest,
        artifact_id=derive_artifact_id(
            kind="canonical-source-text",
            content_sha256=stream_digest,
            source_ids=(source_id,),
            producer_id=f"veriformis.parser.{parser}",
            producer_version=parser_version,
            config_digest=config_digest,
        ),
    )


def empty_parse_report(source: SourceRef) -> ParseReport:
    return make_parse_report(
        source_id=source.id,
        parser_name=source.parser,
        parser_version=source.parser_version,
    )
