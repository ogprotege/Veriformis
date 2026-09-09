"""File identity guards for a verified source reused within one operation."""
from __future__ import annotations

import copy
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from veriformis._operation import current_operation
from veriformis.errors import ExportVerificationError

_PATHS = ("", "data", "metadata", "manifest.json", "attestation.json", "validation.json",
          "data/train.jsonl", "data/evaluation.jsonl", "metadata/row-provenance.jsonl")


def _facts(root: Path):
    try:
        result = []
        for name in _PATHS:
            path = root / name
            status = path.lstat()
            directory = name in ("", "data", "metadata")
            if (directory and not stat.S_ISDIR(status.st_mode)) or (
                not directory and not stat.S_ISREG(status.st_mode)
            ):
                return None
            result.append((name, status.st_dev, status.st_ino, status.st_mode,
                           status.st_size, status.st_mtime_ns, status.st_ctime_ns,
                           status.st_nlink, tuple(sorted(os.listdir(path))) if directory else ()))
        return tuple(result)
    except OSError:
        return None


@dataclass(frozen=True)
class SourceSnapshot:
    root: Path
    facts: tuple
    source: Any

    def check(self):
        if _facts(self.root) != self.facts:
            raise ExportVerificationError("verified export source changed during operation")


def snapshot_key(bundle, policy, digest):
    return ("export-source", Path(os.path.abspath(os.fspath(bundle))), policy, digest)


def get_snapshot(bundle, policy, digest):
    operation = current_operation()
    return operation.models.get(snapshot_key(bundle, policy, digest)) if operation else None


def capture_source(bundle, policy, digest, inspect):
    operation = current_operation()
    if operation is None:
        return inspect()
    key = snapshot_key(bundle, policy, digest)
    snapshot = operation.models.get(key)
    if snapshot is not None:
        snapshot.check()
        return copy.deepcopy(snapshot.source)
    root = key[1]
    before = _facts(root)
    source = inspect()
    if before is None or _facts(root) != before:
        raise ExportVerificationError("export source changed during verified capture")
    operation.models[key] = SourceSnapshot(root, before, copy.deepcopy(source))
    return source
