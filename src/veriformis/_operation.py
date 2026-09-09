"""Operation-scoped immutable reads and replay memoization.

Nothing survives an outer service call. HEAD is never cached. File identity,
size, mode, and nanosecond times are rechecked on reuse and before publication.
Captured bytes spill to a private temporary file after eight MiB.
"""
from __future__ import annotations

import copy
import os
import tempfile
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any

from veriformis.errors import ArtifactDigestMismatchError, WorkspaceCorruptError
from veriformis.identity import lossless_json_bytes, sha256_digest


@dataclass(frozen=True)
class _Read:
    facts: tuple[int, ...]
    offset: int
    size: int
    digest: str


def _key(path: Path) -> Path:
    # Do not resolve symlinks: replacing the supplied name must be detected.
    return Path(os.path.abspath(path))


def _facts(path: Path) -> tuple[int, ...]:
    values = []
    for status in (path.lstat(), path.stat()):
        values.extend((status.st_dev, status.st_ino, status.st_mode, status.st_size,
                       status.st_mtime_ns, status.st_ctime_ns, status.st_nlink))
    return tuple(values)


class Operation:
    def __init__(self) -> None:
        self.files: dict[Path, _Read] = {}
        self.spool = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)
        self.histories: dict[Path, tuple[str, ...]] = {}
        self.models: dict[Any, Any] = {}
        self.revisions: dict[Path, Any] = {}

    def check(self, path: Path) -> None:
        key = _key(path)
        entry = self.files[key]
        try:
            unchanged = _facts(key) == entry.facts
        except OSError:
            unchanged = False
        if not unchanged:
            raise ArtifactDigestMismatchError(f"immutable file changed during operation: {key}")

    def check_all(self) -> None:
        for path in self.files:
            self.check(path)

    def entry(self, path: Path) -> _Read:
        key = _key(path)
        if key in self.files:
            self.check(key)
            return self.files[key]
        before = _facts(key)
        data = path.read_bytes()
        after = _facts(key)
        if before != after:
            raise ArtifactDigestMismatchError(f"immutable file changed while reading: {key}")
        self.spool.seek(0, 2)
        offset = self.spool.tell()
        self.spool.write(data)
        entry = _Read(after, offset, len(data), sha256_digest(data))
        self.files[key] = entry
        return entry

    def read(self, path: Path) -> bytes:
        entry = self.entry(path)
        self.spool.seek(entry.offset)
        return self.spool.read(entry.size)

    def move(self, old: Path, new: Path) -> None:
        old_key, new_key = _key(old), _key(new)
        entry = self.files.pop(old_key, None)
        if entry is not None:
            facts = _facts(new_key)
            # Rename and chmod may change mode/ctime, not content size, inode,
            # or mtime. Never attach old bytes to a substituted staged object.
            stable = (0, 1, 3, 4, 7, 8, 10, 11)
            if any(facts[index] != entry.facts[index] for index in stable):
                raise ArtifactDigestMismatchError("staged object changed during installation")
            self.files[new_key] = _Read(facts, entry.offset, entry.size, entry.digest)

    def forget_tree(self, root: Path) -> None:
        root = _key(root)
        for path in tuple(self.files):
            if path.is_relative_to(root):
                self.files.pop(path)


_ACTIVE: ContextVar[Operation | None] = ContextVar("veriformis_operation", default=None)


def current_operation() -> Operation | None:
    return _ACTIVE.get()


@contextmanager
def operation_scope():
    if current_operation() is not None:
        yield
        return
    operation = Operation()
    token = _ACTIVE.set(operation)
    try:
        yield
    finally:
        _ACTIVE.reset(token)
        # Cleanup cannot turn a committed publication into a false rollback.
        with suppress(OSError):
            operation.spool.close()


def workspace_operation(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with operation_scope():
            return function(*args, **kwargs)
    return wrapped


def immutable_bytes(path: Path) -> bytes:
    operation = current_operation()
    return path.read_bytes() if operation is None else operation.read(path)


def verify_immutable(path: Path, *, size: int, digest: str) -> None:
    operation = current_operation()
    if operation is None:
        data = path.read_bytes()
        actual_size, actual_digest = len(data), sha256_digest(data)
    else:
        entry = operation.entry(path)
        actual_size, actual_digest = entry.size, entry.digest
    if (actual_size, actual_digest) != (size, digest):
        raise ArtifactDigestMismatchError(f"artifact bytes do not match immutable object: {path}")


def verified_bytes(path: Path, *, size: int, digest: str) -> bytes:
    operation = current_operation()
    if operation is not None:
        verify_immutable(path, size=size, digest=digest)
        return operation.read(path)
    data = path.read_bytes()
    if len(data) != size or sha256_digest(data) != digest:
        raise ArtifactDigestMismatchError(f"artifact bytes do not match immutable object: {path}")
    return data


def memoized_loader(function):
    """Memoize exact inputs and return copies so callers cannot poison a replay."""
    @wraps(function)
    def wrapped(workspace, revision, *args, **kwargs):
        operation = current_operation()
        if operation is None:
            return function(workspace, revision, *args, **kwargs)
        try:
            key = (function, _key(workspace.root), lossless_json_bytes(revision),
                   lossless_json_bytes(args), lossless_json_bytes(kwargs))
        except (TypeError, ValueError) as exc:
            raise WorkspaceCorruptError("invalid loader input during operation") from exc
        if key not in operation.models:
            result = function(workspace, revision, *args, **kwargs)
            operation.models[key] = copy.deepcopy(result)
            return result
        operation.check_all()
        return copy.deepcopy(operation.models[key])
    return wrapped
