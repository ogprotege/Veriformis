"""Private descriptor-anchored publication for verified exact-byte exports.

This module owns runtime filesystem state only.  Portable identities remain in
``veriformis.exports.models`` and never include destination paths, temporary
names, cancellation state, or durability warnings.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import secrets
import stat
import sys
import warnings
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports.models import (
    EXPORT_RECEIPT_PATH,
    ExportDestinationFileBinding,
    ExportPlan,
    ExportReceipt,
    ExportVerification,
)
from veriformis.exports.paths import (
    portable_export_path_key,
    validate_export_relative_path,
)
from veriformis.identity import sha256_digest

_CHUNK_SIZE = 1024 * 1024
_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_FILE_READ_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_EntryFacts = tuple[int, int, int, int, int, int, int]
CancellationCheck = Callable[[], None]


@dataclass(frozen=True, slots=True)
class ExportPublicationOutcome:
    """Runtime result for one visible, receipt-bound derivative directory."""

    destination_root: Path
    receipt: ExportReceipt
    verification: ExportVerification
    durability_warning: str | None


class ExportPartialPublicationError(Exception):
    """A verified derivative became visible before later bookkeeping failed."""

    def __init__(
        self,
        publication: ExportPublicationOutcome,
        cause: BaseException,
    ) -> None:
        self.publication = publication
        self.cause = cause
        super().__init__(str(cause))


@dataclass(slots=True)
class _Destination:
    root: Path
    parent: Path
    parent_descriptor: int
    target_name: str
    parent_identity: tuple[int, int]


@dataclass(slots=True)
class _StagingDirectory:
    destination: _Destination
    name: str
    root: Path
    descriptor: int
    published: bool = False
    owned_directories: dict[str, tuple[int, int]] = field(default_factory=dict)
    owned_files: dict[str, tuple[int, int]] = field(default_factory=dict)


def _entry_facts(status: os.stat_result) -> _EntryFacts:
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
        status.st_nlink,
    )


def _directory_identity(descriptor: int) -> tuple[int, int]:
    try:
        status = os.fstat(descriptor)
    except OSError as exc:
        raise ExportVerificationError(
            f"cannot inspect export directory descriptor: {exc}"
        ) from exc
    if not stat.S_ISDIR(status.st_mode):
        raise ExportVerificationError("export directory descriptor is not a directory")
    return status.st_dev, status.st_ino


def _name_matches_descriptor(
    parent_descriptor: int,
    name: str,
    descriptor: int,
) -> bool:
    try:
        status = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ExportVerificationError(
            f"cannot inspect export directory entry {name!r}: {exc}"
        ) from exc
    return (
        stat.S_ISDIR(status.st_mode)
        and not stat.S_ISLNK(status.st_mode)
        and (status.st_dev, status.st_ino) == _directory_identity(descriptor)
    )


def _path_matches_descriptor(path: Path, descriptor: int) -> bool:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ExportVerificationError(
            f"cannot inspect export directory path {path}: {exc}"
        ) from exc
    return (
        stat.S_ISDIR(status.st_mode)
        and not stat.S_ISLNK(status.st_mode)
        and (status.st_dev, status.st_ino) == _directory_identity(descriptor)
    )


def _check_cancellation(check: CancellationCheck | None) -> None:
    if check is not None:
        check()


def _prepare_destination(
    destination_root: str | os.PathLike[str],
    *,
    source_root: Path,
) -> _Destination:
    try:
        root = Path(os.path.abspath(os.fspath(destination_root)))
    except (TypeError, ValueError) as exc:
        raise ExportContractError(f"invalid export destination root: {exc}") from exc
    if not root.name:
        raise ExportContractError("export destination root must name a directory")
    parent = root.parent
    try:
        before = parent.lstat()
    except OSError as exc:
        raise ExportContractError(
            f"cannot inspect export destination parent {parent}: {exc}"
        ) from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise ExportContractError(
            "export destination parent must be a real directory, not a symlink"
        )
    try:
        parent_descriptor = os.open(parent, _DIRECTORY_FLAGS)
    except OSError as exc:
        raise ExportContractError(
            f"cannot open export destination parent {parent}: {exc}"
        ) from exc
    try:
        after = os.fstat(parent_descriptor)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ExportVerificationError(
                "export destination parent changed while opening"
            )
        try:
            resolved_parent = parent.resolve(strict=True)
            resolved_source = source_root.resolve(strict=True)
        except OSError as exc:
            raise ExportVerificationError(
                f"cannot resolve export/source roots safely: {exc}"
            ) from exc
        try:
            parent_inside_source = (
                os.path.commonpath((resolved_parent, resolved_source))
                == os.fspath(resolved_source)
            )
        except ValueError:
            parent_inside_source = False
        if parent_inside_source:
            raise ExportContractError(
                "export destination cannot be inside the verified source bundle"
            )
        try:
            os.stat(root.name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ExportContractError(
                f"export destination already exists: {root}"
            )
        return _Destination(
            root=root,
            parent=parent,
            parent_descriptor=parent_descriptor,
            target_name=root.name,
            parent_identity=(after.st_dev, after.st_ino),
        )
    except BaseException:
        os.close(parent_descriptor)
        raise


def _require_parent_identity(destination: _Destination) -> None:
    try:
        status = destination.parent.lstat()
    except OSError as exc:
        raise ExportVerificationError(
            f"export destination parent disappeared during publication: {exc}"
        ) from exc
    if (
        stat.S_ISLNK(status.st_mode)
        or not stat.S_ISDIR(status.st_mode)
        or (status.st_dev, status.st_ino) != destination.parent_identity
        or _directory_identity(destination.parent_descriptor)
        != destination.parent_identity
    ):
        raise ExportVerificationError(
            "export destination parent changed during publication"
        )


def _create_staging(destination: _Destination) -> _StagingDirectory:
    _require_parent_identity(destination)
    for _ in range(128):
        name = f".veriformis-export-{secrets.token_hex(12)}"
        try:
            os.mkdir(name, 0o700, dir_fd=destination.parent_descriptor)
        except FileExistsError:
            continue
        break
    else:
        raise ExportVerificationError("cannot allocate a private export staging name")
    root = destination.parent / name
    try:
        created = os.stat(
            name,
            dir_fd=destination.parent_descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        _emit_warning(
            "could not prove ownership of a newly created export staging "
            f"directory; preserved its name: {exc}"
        )
        raise ExportVerificationError(
            f"cannot inspect newly created export staging directory: {exc}"
        ) from exc
    created_identity = (created.st_dev, created.st_ino)
    try:
        descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=destination.parent_descriptor)
    except BaseException as exc:
        try:
            current = os.stat(
                name,
                dir_fd=destination.parent_descriptor,
                follow_symlinks=False,
            )
        except OSError:
            current = None
        if current is not None and (
            stat.S_ISDIR(current.st_mode)
            and not stat.S_ISLNK(current.st_mode)
            and (current.st_dev, current.st_ino) == created_identity
        ):
            try:
                os.rmdir(name, dir_fd=destination.parent_descriptor)
            except OSError:
                pass
        else:
            _emit_warning(
                "could not prove ownership of an export staging name after its "
                f"descriptor failed to open; preserved it: {exc}"
            )
        raise
    proven_owned = False
    try:
        status = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(status.st_mode)
            or (status.st_dev, status.st_ino) != created_identity
            or not _name_matches_descriptor(
                destination.parent_descriptor,
                name,
                descriptor,
            )
        ):
            raise ExportVerificationError(
                "export staging directory changed while opening"
            )
        proven_owned = True
        os.fchmod(descriptor, 0o700)
        return _StagingDirectory(
            destination=destination,
            name=name,
            root=root,
            descriptor=descriptor,
        )
    except BaseException:
        if proven_owned and _name_matches_descriptor(
            destination.parent_descriptor,
            name,
            descriptor,
        ):
            try:
                os.rmdir(name, dir_fd=destination.parent_descriptor)
            except OSError:
                pass
        elif not proven_owned:
            _emit_warning(
                "refused to remove an export staging name whose created identity "
                "was replaced while opening"
            )
        _safe_close(descriptor, label="failed export staging")
        raise


def _emit_warning(message: str) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("always", RuntimeWarning)
            warnings.warn(message, RuntimeWarning, stacklevel=3)
    except Exception:
        # Publication and the caller-visible warning string remain authoritative
        # even when a custom warning hook itself is broken.
        pass


def _safe_close(descriptor: int, *, label: str) -> None:
    try:
        os.close(descriptor)
    except OSError as exc:
        _emit_warning(f"could not close {label} descriptor: {exc}")


def _open_owned_directory(
    staging: _StagingDirectory,
    relative_path: str,
) -> int | None:
    current = os.dup(staging.descriptor)
    prefix = ""
    try:
        for part in relative_path.split("/") if relative_path else ():
            prefix = f"{prefix}/{part}" if prefix else part
            expected = staging.owned_directories.get(prefix)
            if expected is None:
                return None
            status = os.stat(part, dir_fd=current, follow_symlinks=False)
            if (
                not stat.S_ISDIR(status.st_mode)
                or stat.S_ISLNK(status.st_mode)
                or (status.st_dev, status.st_ino) != expected
            ):
                return None
            child = os.open(part, _DIRECTORY_FLAGS, dir_fd=current)
            opened = os.fstat(child)
            if (opened.st_dev, opened.st_ino) != expected:
                _safe_close(child, label="replaced export staging")
                return None
            _safe_close(current, label="export staging traversal")
            current = child
        result = current
        current = -1
        return result
    except OSError:
        return None
    finally:
        if current >= 0:
            _safe_close(current, label="export staging traversal")


def _cleanup_staging(staging: _StagingDirectory) -> None:
    try:
        if staging.published:
            return
        if not _name_matches_descriptor(
            staging.destination.parent_descriptor,
            staging.name,
            staging.descriptor,
        ):
            _emit_warning(
                "refused to clean a replaced or moved export staging directory"
            )
            return
        for relative_path, expected in sorted(
            staging.owned_files.items(),
            key=lambda item: (item[0].count("/"), item[0]),
            reverse=True,
        ):
            parent, name = (
                relative_path.rsplit("/", 1)
                if "/" in relative_path
                else ("", relative_path)
            )
            parent_descriptor = _open_owned_directory(staging, parent)
            if parent_descriptor is None:
                _emit_warning(
                    f"refused to clean replaced export file {relative_path!r}"
                )
                continue
            try:
                status = os.stat(
                    name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if (
                    not stat.S_ISREG(status.st_mode)
                    or (status.st_dev, status.st_ino) != expected
                ):
                    _emit_warning(
                        f"refused to clean replaced export file {relative_path!r}"
                    )
                    continue
                os.unlink(name, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass
            finally:
                _safe_close(parent_descriptor, label="export cleanup parent")

        for relative_path, expected in sorted(
            staging.owned_directories.items(),
            key=lambda item: (item[0].count("/"), item[0]),
            reverse=True,
        ):
            parent, name = (
                relative_path.rsplit("/", 1)
                if "/" in relative_path
                else ("", relative_path)
            )
            parent_descriptor = _open_owned_directory(staging, parent)
            if parent_descriptor is None:
                _emit_warning(
                    f"refused to clean replaced export directory {relative_path!r}"
                )
                continue
            try:
                status = os.stat(
                    name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if (
                    not stat.S_ISDIR(status.st_mode)
                    or stat.S_ISLNK(status.st_mode)
                    or (status.st_dev, status.st_ino) != expected
                ):
                    _emit_warning(
                        f"refused to clean replaced export directory "
                        f"{relative_path!r}"
                    )
                    continue
                os.rmdir(name, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass
            except OSError as exc:
                _emit_warning(
                    f"could not remove owned export directory {relative_path!r}: {exc}"
                )
            finally:
                _safe_close(parent_descriptor, label="export cleanup parent")

        if not _name_matches_descriptor(
            staging.destination.parent_descriptor,
            staging.name,
            staging.descriptor,
        ):
            _emit_warning("refused to remove a replaced export staging directory")
            return
        try:
            os.rmdir(staging.name, dir_fd=staging.destination.parent_descriptor)
        except FileNotFoundError:
            pass
        except OSError as exc:
            _emit_warning(f"could not remove export staging directory: {exc}")
    except BaseException as exc:
        _emit_warning(f"could not safely clean export staging directory: {exc}")
    finally:
        _safe_close(staging.descriptor, label="export staging")


def _parent_directories(paths: Sequence[str]) -> tuple[str, ...]:
    values: set[str] = set()
    for path in paths:
        parts = path.split("/")
        for index in range(1, len(parts)):
            values.add("/".join(parts[:index]))
    return tuple(sorted(values, key=lambda item: (item.count("/"), item)))


def _create_parent_directories(
    staging: _StagingDirectory,
    paths: Sequence[str],
    *,
    cancellation_check: CancellationCheck | None,
) -> dict[str, int]:
    descriptors = {"": os.dup(staging.descriptor)}
    try:
        for directory in _parent_directories(paths):
            _check_cancellation(cancellation_check)
            parent, name = (
                directory.rsplit("/", 1) if "/" in directory else ("", directory)
            )
            os.mkdir(name, 0o700, dir_fd=descriptors[parent])
            created = os.stat(
                name,
                dir_fd=descriptors[parent],
                follow_symlinks=False,
            )
            if not stat.S_ISDIR(created.st_mode) or stat.S_ISLNK(created.st_mode):
                raise ExportVerificationError(
                    f"created export parent {directory!r} is not a directory"
                )
            staging.owned_directories[directory] = (
                created.st_dev,
                created.st_ino,
            )
            descriptor = os.open(
                name,
                _DIRECTORY_FLAGS,
                dir_fd=descriptors[parent],
            )
            status = os.fstat(descriptor)
            if (
                not stat.S_ISDIR(status.st_mode)
                or (status.st_dev, status.st_ino)
                != staging.owned_directories[directory]
            ):
                os.close(descriptor)
                raise ExportVerificationError(
                    f"export parent {directory!r} is not a directory"
                )
            descriptors[directory] = descriptor
        return descriptors
    except BaseException:
        for descriptor in descriptors.values():
            _safe_close(descriptor, label="export parent")
        raise


def _write_file(
    staging: _StagingDirectory,
    directory_descriptor: int,
    relative_path: str,
    name: str,
    data: bytes,
    *,
    cancellation_check: CancellationCheck | None,
) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = os.open(name, flags, 0o600, dir_fd=directory_descriptor)
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise ExportVerificationError(
                f"created export file {relative_path!r} is not regular"
            )
        staging.owned_files[relative_path] = (status.st_dev, status.st_ino)
        view = memoryview(data)
        while view:
            _check_cancellation(cancellation_check)
            written = os.write(descriptor, view[:_CHUNK_SIZE])
            if written <= 0:
                raise OSError("short write while publishing export")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sync_directories(
    descriptors: dict[str, int],
    *,
    cancellation_check: CancellationCheck | None,
) -> None:
    for path in sorted(
        descriptors,
        key=lambda value: (value.count("/") + 1 if value else 0, value),
        reverse=True,
    ):
        _check_cancellation(cancellation_check)
        os.fsync(descriptors[path])


def _register_path(paths: dict[str, str], relative_path: str) -> None:
    try:
        validate_export_relative_path(relative_path)
    except ValueError as exc:
        raise ExportVerificationError(
            f"unsafe path in export tree: {relative_path!r}: {exc}"
        ) from exc
    key = portable_export_path_key(relative_path)
    previous = paths.get(key)
    if previous is not None and previous != relative_path:
        raise ExportVerificationError(
            f"export tree paths collide by case or Unicode: "
            f"{previous!r} and {relative_path!r}"
        )
    paths[key] = relative_path


def _collect_tree(
    root_descriptor: int,
    *,
    cancellation_check: CancellationCheck | None = None,
) -> tuple[dict[str, _EntryFacts], dict[str, _EntryFacts]]:
    files: dict[str, _EntryFacts] = {}
    directories: dict[str, _EntryFacts] = {}
    portable_paths: dict[str, str] = {}
    file_inodes: dict[tuple[int, int], str] = {}

    def visit(directory_descriptor: int, prefix: str) -> None:
        _check_cancellation(cancellation_check)
        try:
            names = sorted(os.listdir(directory_descriptor))
        except OSError as exc:
            raise ExportVerificationError(
                f"cannot enumerate export directory {prefix or '.'}: {exc}"
            ) from exc
        for name in names:
            _check_cancellation(cancellation_check)
            relative_path = f"{prefix}/{name}" if prefix else name
            _register_path(portable_paths, relative_path)
            try:
                status = os.stat(
                    name,
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            except OSError as exc:
                raise ExportVerificationError(
                    f"cannot inspect export entry {relative_path!r}: {exc}"
                ) from exc
            if stat.S_ISLNK(status.st_mode):
                raise ExportVerificationError(
                    f"export tree cannot contain symlink {relative_path!r}"
                )
            if stat.S_ISDIR(status.st_mode):
                directories[relative_path] = _entry_facts(status)
                try:
                    child = os.open(
                        name,
                        _DIRECTORY_FLAGS,
                        dir_fd=directory_descriptor,
                    )
                except OSError as exc:
                    raise ExportVerificationError(
                        f"cannot open export directory {relative_path!r}: {exc}"
                    ) from exc
                try:
                    if _directory_identity(child) != (status.st_dev, status.st_ino):
                        raise ExportVerificationError(
                            f"export directory {relative_path!r} changed while opening"
                        )
                    visit(child, relative_path)
                finally:
                    _safe_close(child, label="verified export directory")
                continue
            if not stat.S_ISREG(status.st_mode):
                raise ExportVerificationError(
                    f"export tree contains special file {relative_path!r}"
                )
            if status.st_nlink != 1:
                raise ExportVerificationError(
                    f"export tree cannot contain hard-linked file {relative_path!r}"
                )
            inode = (status.st_dev, status.st_ino)
            previous = file_inodes.get(inode)
            if previous is not None:
                raise ExportVerificationError(
                    f"export files share one inode: {previous!r} and {relative_path!r}"
                )
            file_inodes[inode] = relative_path
            files[relative_path] = _entry_facts(status)

    visit(root_descriptor, "")
    return files, directories


def _open_regular_file(
    root_descriptor: int,
    relative_path: str,
    *,
    expected_facts: _EntryFacts,
) -> int:
    try:
        current = os.dup(root_descriptor)
    except OSError as exc:
        raise ExportVerificationError(
            f"cannot duplicate export root descriptor: {exc}"
        ) from exc
    try:
        for part in relative_path.split("/")[:-1]:
            child = os.open(part, _DIRECTORY_FLAGS, dir_fd=current)
            _safe_close(current, label="export file traversal")
            current = child
        descriptor = os.open(
            relative_path.rsplit("/", 1)[-1],
            _FILE_READ_FLAGS,
            dir_fd=current,
        )
    except OSError as exc:
        raise ExportVerificationError(
            f"cannot safely open export file {relative_path!r}: {exc}"
        ) from exc
    finally:
        _safe_close(current, label="export file parent")
    try:
        status = os.fstat(descriptor)
    except OSError as exc:
        _safe_close(descriptor, label="failed export file")
        raise ExportVerificationError(
            f"cannot inspect opened export file {relative_path!r}: {exc}"
        ) from exc
    if (
        not stat.S_ISREG(status.st_mode)
        or status.st_nlink != 1
        or _entry_facts(status) != expected_facts
    ):
        _safe_close(descriptor, label="rejected export file")
        raise ExportVerificationError(
            f"export file changed between enumeration and open: {relative_path!r}"
        )
    return descriptor


def _read_and_hash(
    root_descriptor: int,
    relative_path: str,
    *,
    expected_facts: _EntryFacts,
    cancellation_check: CancellationCheck | None,
    retain_bytes: bool = False,
    retain_limit: int | None = None,
) -> tuple[str, int, bytes | None]:
    descriptor = _open_regular_file(
        root_descriptor,
        relative_path,
        expected_facts=expected_facts,
    )
    digest = hashlib.sha256()
    size = 0
    chunks: list[bytes] | None = [] if retain_bytes else None
    try:
        try:
            before = os.fstat(descriptor)
        except OSError as exc:
            raise ExportVerificationError(
                f"cannot inspect export file {relative_path!r}: {exc}"
            ) from exc
        while True:
            _check_cancellation(cancellation_check)
            try:
                chunk = os.read(descriptor, _CHUNK_SIZE)
            except OSError as exc:
                raise ExportVerificationError(
                    f"cannot read export file {relative_path!r}: {exc}"
                ) from exc
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
            if chunks is not None:
                if retain_limit is not None and size > retain_limit:
                    raise ExportVerificationError(
                        "export receipt exceeds its independently expected size"
                    )
                chunks.append(chunk)
        try:
            after = os.fstat(descriptor)
        except OSError as exc:
            raise ExportVerificationError(
                f"cannot re-inspect export file {relative_path!r}: {exc}"
            ) from exc
    finally:
        _safe_close(descriptor, label="verified export file")
    if _entry_facts(before) != _entry_facts(after):
        raise ExportVerificationError(
            f"export file changed during verification: {relative_path!r}"
        )
    return digest.hexdigest(), size, b"".join(chunks) if chunks is not None else None


def _expected_directories(paths: Sequence[str]) -> set[str]:
    return set(_parent_directories(paths))


def _verify_staged_export(
    root_descriptor: int,
    *,
    expected_plan: ExportPlan,
    cancellation_check: CancellationCheck | None,
) -> tuple[ExportReceipt, ExportVerification, tuple[dict[str, _EntryFacts], dict[str, _EntryFacts]]]:
    """Independently verify one staged exact-byte export through its root fd."""
    checked_plan = ExportPlan.from_json_bytes(expected_plan.canonical_bytes())
    if checked_plan.container_profile.determinism_claim != "portable_exact_bytes":
        raise ExportContractError(
            "Phase 4.6 publication supports portable_exact_bytes plans only"
        )
    files, directories = _collect_tree(
        root_descriptor,
        cancellation_check=cancellation_check,
    )
    expected_files = {item.path for item in checked_plan.file_plans} | {
        EXPORT_RECEIPT_PATH
    }
    expected_directories = _expected_directories(tuple(expected_files))
    if set(files) != expected_files:
        raise ExportVerificationError(
            "export file set is not closed; "
            f"missing={sorted(expected_files - set(files))!r}, "
            f"extra={sorted(set(files) - expected_files)!r}"
        )
    if set(directories) != expected_directories:
        raise ExportVerificationError(
            "export directory set is not closed; "
            f"missing={sorted(expected_directories - set(directories))!r}, "
            f"extra={sorted(set(directories) - expected_directories)!r}"
        )

    bindings: list[ExportDestinationFileBinding] = []
    for file_plan in checked_plan.file_plans:
        digest, size, _ = _read_and_hash(
            root_descriptor,
            file_plan.path,
            expected_facts=files[file_plan.path],
            cancellation_check=cancellation_check,
        )
        bindings.append(
            ExportDestinationFileBinding.create(
                file_plan_id=file_plan.file_plan_id,
                path=file_plan.path,
                role=file_plan.role,
                media_type=file_plan.media_type,
                membership_scope=file_plan.membership_scope,
                record_count=file_plan.record_count,
                semantic_content_sha256=None,
                sha256=digest,
                byte_size=size,
            )
        )
    recomputed_receipt = ExportReceipt.create(
        export_plan=checked_plan,
        files=bindings,
    )
    expected_receipt_bytes = recomputed_receipt.canonical_bytes()
    receipt_size = files[EXPORT_RECEIPT_PATH][3]
    if receipt_size != len(expected_receipt_bytes):
        raise ExportVerificationError(
            "export receipt byte size differs from independent reconstruction"
        )
    _, _, receipt_bytes = _read_and_hash(
        root_descriptor,
        EXPORT_RECEIPT_PATH,
        expected_facts=files[EXPORT_RECEIPT_PATH],
        cancellation_check=cancellation_check,
        retain_bytes=True,
        retain_limit=len(expected_receipt_bytes),
    )
    assert receipt_bytes is not None
    receipt = ExportReceipt.from_json_bytes(receipt_bytes)
    if (
        receipt.export_plan != checked_plan
        or receipt.export_plan.canonical_bytes() != checked_plan.canonical_bytes()
    ):
        raise ExportVerificationError(
            "export receipt embeds a plan other than the independently supplied plan"
        )
    if (
        receipt != recomputed_receipt
        or receipt.canonical_bytes() != recomputed_receipt.canonical_bytes()
    ):
        raise ExportVerificationError(
            "export receipt differs from independently observed destination bytes"
        )
    verification = ExportVerification.create(receipt=receipt)
    final_files, final_directories = _collect_tree(
        root_descriptor,
        cancellation_check=cancellation_check,
    )
    if final_files != files or final_directories != directories:
        raise ExportVerificationError("export tree changed during verification")
    return receipt, verification, (final_files, final_directories)


def _verify_export_directory(
    destination_root: str | os.PathLike[str],
    *,
    expected_plan: ExportPlan,
    cancellation_check: CancellationCheck | None = None,
) -> tuple[ExportReceipt, ExportVerification]:
    """Independently inspect one already visible derivative directory."""
    if cancellation_check is not None and not callable(cancellation_check):
        raise ExportContractError("cancellation_check must be callable")
    try:
        root = Path(os.path.abspath(os.fspath(destination_root)))
        before = root.lstat()
    except (OSError, TypeError, ValueError) as exc:
        raise ExportVerificationError(
            f"cannot inspect export directory root: {exc}"
        ) from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise ExportVerificationError(
            "export directory root must be a real directory, not a symlink"
        )
    try:
        descriptor = os.open(root, _DIRECTORY_FLAGS)
    except OSError as exc:
        raise ExportVerificationError(
            f"cannot open export directory root {root}: {exc}"
        ) from exc
    try:
        try:
            after = os.fstat(descriptor)
        except OSError as exc:
            raise ExportVerificationError(
                f"cannot inspect opened export directory root: {exc}"
            ) from exc
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ExportVerificationError("export directory root changed while opening")
        receipt, verification, _ = _verify_staged_export(
            descriptor,
            expected_plan=expected_plan,
            cancellation_check=cancellation_check,
        )
        if not _path_matches_descriptor(root, descriptor):
            raise ExportVerificationError(
                "export directory root changed during verification"
            )
        return receipt, verification
    finally:
        _safe_close(descriptor, label="verified export root")


def _rename_no_replace(
    staging: _StagingDirectory,
    *,
    expected_tree: tuple[dict[str, _EntryFacts], dict[str, _EntryFacts]],
    cancellation_check: CancellationCheck | None,
) -> None:
    destination = staging.destination
    # This is the final caller-controlled checkpoint.  Every identity and tree
    # fact is rechecked after it, with no further callback before the syscall.
    _check_cancellation(cancellation_check)
    _require_parent_identity(destination)
    if not _name_matches_descriptor(
        destination.parent_descriptor,
        staging.name,
        staging.descriptor,
    ):
        raise ExportVerificationError(
            "export staging directory changed before publication"
        )
    if _collect_tree(
        staging.descriptor,
        cancellation_check=None,
    ) != expected_tree:
        raise ExportVerificationError(
            "export tree changed immediately before publication"
        )
    if sys.platform == "darwin":
        libc = ctypes.CDLL(None, use_errno=True)
        renameatx = libc.renameatx_np
        renameatx.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameatx.restype = ctypes.c_int
        result = renameatx(
            destination.parent_descriptor,
            os.fsencode(staging.name),
            destination.parent_descriptor,
            os.fsencode(destination.target_name),
            0x00000004,
        )
    elif sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise OSError(
                errno.ENOTSUP,
                "atomic no-replace export rename is unavailable",
                os.fspath(destination.root),
            )
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            destination.parent_descriptor,
            os.fsencode(staging.name),
            destination.parent_descriptor,
            os.fsencode(destination.target_name),
            1,
        )
    elif sys.platform == "win32":
        move_file = ctypes.windll.kernel32.MoveFileExW
        move_file.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        move_file.restype = ctypes.c_int
        result = move_file(os.fspath(staging.root), os.fspath(destination.root), 0)
        if result == 0:
            win_error = ctypes.get_last_error()
            if win_error in (80, 183):
                raise FileExistsError(
                    errno.EEXIST,
                    "export destination already exists",
                    os.fspath(destination.root),
                )
            raise OSError(
                win_error,
                "atomic export rename failed",
                os.fspath(destination.root),
            )
        result = 0
    else:
        raise OSError(
            errno.ENOTSUP,
            "atomic no-replace export rename is unavailable",
            os.fspath(destination.root),
        )

    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in (errno.EEXIST, errno.ENOTEMPTY):
            raise FileExistsError(
                error_number,
                "export destination already exists",
                os.fspath(destination.root),
            )
        raise OSError(
            error_number,
            os.strerror(error_number),
            os.fspath(destination.root),
        )
    staging.published = True
    if not _name_matches_descriptor(
        destination.parent_descriptor,
        destination.target_name,
        staging.descriptor,
    ):
        raise ExportVerificationError(
            "published export destination changed immediately after promotion"
        )


def _publish_exact_export(
    destination_root: str | os.PathLike[str],
    *,
    source_root: Path,
    plan: ExportPlan,
    files: Sequence[tuple[str, bytes]],
    cancellation_check: CancellationCheck | None,
) -> ExportPublicationOutcome:
    """Write, verify, and atomically publish one exact-byte export tree."""
    if cancellation_check is not None and not callable(cancellation_check):
        raise ExportContractError("cancellation_check must be callable")
    checked_plan = ExportPlan.from_json_bytes(plan.canonical_bytes())
    if checked_plan.container_profile.determinism_claim != "portable_exact_bytes":
        raise ExportContractError(
            "Phase 4.6 publication supports portable_exact_bytes plans only"
        )
    supplied = tuple(files)
    copied: dict[str, bytes] = {}
    for entry in supplied:
        _check_cancellation(cancellation_check)
        if type(entry) is not tuple or len(entry) != 2:
            raise ExportVerificationError(
                "renderer output entries must be exact (path, bytes) tuples"
            )
        path, data = entry
        if type(path) is not str or type(data) is not bytes:
            raise ExportVerificationError(
                "renderer output entries must contain an exact string and bytes"
            )
        try:
            validate_export_relative_path(path)
        except ValueError as exc:
            raise ExportVerificationError(
                f"renderer produced unsafe export path {path!r}: {exc}"
            ) from exc
        if path in copied:
            raise ExportVerificationError(
                f"renderer produced duplicate export path {path!r}"
            )
        copied[path] = data
    expected_paths = {item.path for item in checked_plan.file_plans}
    if set(copied) != expected_paths:
        raise ExportVerificationError(
            "renderer output does not match the complete planned file set; "
            f"missing={sorted(expected_paths - set(copied))!r}, "
            f"extra={sorted(set(copied) - expected_paths)!r}"
        )

    bindings: list[ExportDestinationFileBinding] = []
    for file_plan in checked_plan.file_plans:
        _check_cancellation(cancellation_check)
        data = copied[file_plan.path]
        digest = sha256_digest(data)
        size = len(data)
        if digest != file_plan.expected_sha256 or size != file_plan.expected_byte_size:
            raise ExportVerificationError(
                f"renderer bytes differ from the exact plan for {file_plan.path!r}"
            )
        bindings.append(
            ExportDestinationFileBinding.create(
                file_plan_id=file_plan.file_plan_id,
                path=file_plan.path,
                role=file_plan.role,
                media_type=file_plan.media_type,
                membership_scope=file_plan.membership_scope,
                record_count=file_plan.record_count,
                semantic_content_sha256=None,
                sha256=digest,
                byte_size=size,
            )
        )
    receipt = ExportReceipt.create(export_plan=checked_plan, files=bindings)
    receipt_bytes = receipt.canonical_bytes()
    destination = _prepare_destination(
        destination_root,
        source_root=source_root,
    )
    staging: _StagingDirectory | None = None
    publication_failure: BaseException | None = None
    try:
        _check_cancellation(cancellation_check)
        staging = _create_staging(destination)
        _check_cancellation(cancellation_check)
        all_paths = (*tuple(copied), EXPORT_RECEIPT_PATH)
        descriptors = _create_parent_directories(
            staging,
            all_paths,
            cancellation_check=cancellation_check,
        )
        try:
            for file_plan in checked_plan.file_plans:
                _check_cancellation(cancellation_check)
                parent, name = (
                    file_plan.path.rsplit("/", 1)
                    if "/" in file_plan.path
                    else ("", file_plan.path)
                )
                _write_file(
                    staging,
                    descriptors[parent],
                    file_plan.path,
                    name,
                    copied[file_plan.path],
                    cancellation_check=cancellation_check,
                )
            _check_cancellation(cancellation_check)
            _write_file(
                staging,
                staging.descriptor,
                EXPORT_RECEIPT_PATH,
                EXPORT_RECEIPT_PATH,
                receipt_bytes,
                cancellation_check=cancellation_check,
            )
            _sync_directories(
                descriptors,
                cancellation_check=cancellation_check,
            )
        finally:
            for descriptor in descriptors.values():
                _safe_close(descriptor, label="export parent")

        _check_cancellation(cancellation_check)
        independently_observed = _verify_staged_export(
            staging.descriptor,
            expected_plan=checked_plan,
            cancellation_check=cancellation_check,
        )
        observed_receipt, observed_verification, verified_tree = independently_observed
        if (
            observed_receipt != receipt
            or observed_receipt.canonical_bytes() != receipt_bytes
            or observed_verification
            != ExportVerification.create(receipt=observed_receipt)
        ):
            raise ExportVerificationError(
                "independent staged verification returned different export evidence"
            )
        _check_cancellation(cancellation_check)
        final_tree = _collect_tree(
            staging.descriptor,
            cancellation_check=cancellation_check,
        )
        if final_tree != verified_tree:
            raise ExportVerificationError(
                "export tree changed after staged verification"
            )
        _require_parent_identity(destination)
        publication = ExportPublicationOutcome(
            destination_root=destination.root,
            receipt=observed_receipt,
            verification=observed_verification,
            durability_warning=None,
        )
        _rename_no_replace(
            staging,
            expected_tree=verified_tree,
            cancellation_check=cancellation_check,
        )
        if (
            not _name_matches_descriptor(
                destination.parent_descriptor,
                destination.target_name,
                staging.descriptor,
            )
            or not _path_matches_descriptor(destination.root, staging.descriptor)
        ):
            raise ExportVerificationError(
                "published export destination changed after promotion"
            )
    except BaseException as exc:
        if staging is not None and not staging.published:
            # A successful syscall followed by asynchronous interruption is still
            # publication.  Recover that fact before deciding whether cleanup is safe.
            if _name_matches_descriptor(
                destination.parent_descriptor,
                destination.target_name,
                staging.descriptor,
            ):
                staging.published = True
        publication_failure = exc
    finally:
        if staging is not None:
            _cleanup_staging(staging)
    if publication_failure is not None:
        _safe_close(
            destination.parent_descriptor,
            label="export destination parent",
        )
        if staging is not None and staging.published:
            raise ExportPartialPublicationError(
                publication,
                publication_failure,
            ) from publication_failure
        raise publication_failure.with_traceback(publication_failure.__traceback__)

    try:
        durability_warning: str | None = None
        try:
            os.fsync(destination.parent_descriptor)
        except OSError as exc:
            durability_warning = (
                f"export {destination.root} is visible, but its parent directory "
                f"could not be synced: {exc}"
            )
            _emit_warning(durability_warning)
        result = replace(publication, durability_warning=durability_warning)
    except BaseException as exc:
        raise ExportPartialPublicationError(publication, exc) from exc
    finally:
        _safe_close(
            destination.parent_descriptor,
            label="export destination parent",
        )
    return result
