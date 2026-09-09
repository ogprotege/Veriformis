"""Private temporary storage for one strict, already rendered export tree."""
from __future__ import annotations

import tempfile
from collections.abc import Mapping, Sequence
from contextlib import suppress


class SpooledTree(Mapping[str, bytes]):
    """Keep the first rendering off the heap while producing the second one."""
    def __init__(self, files: Sequence[tuple[str, bytes]]) -> None:
        self._file = tempfile.TemporaryFile()
        self._entries: dict[str, tuple[int, int]] = {}
        try:
            for path, data in files:
                if path in self._entries:
                    raise ValueError("duplicate path in spooled export tree")
                self._entries[path] = (self._file.tell(), len(data))
                self._file.write(data)
        except BaseException:
            self.close()
            raise

    def __iter__(self):
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)

    def __getitem__(self, path: str) -> bytes:
        offset, size = self._entries[path]
        self._file.seek(offset)
        return self._file.read(size)

    def matches(self, files: Sequence[tuple[str, bytes]]) -> bool:
        if tuple(path for path, _ in files) != tuple(self):
            return False
        for path, data in files:
            offset, size = self._entries[path]
            if len(data) != size:
                return False
            self._file.seek(offset)
            view = memoryview(data)
            for start in range(0, size, 1024 * 1024):
                expected = self._file.read(min(1024 * 1024, size - start))
                if view[start : start + len(expected)] != expected:
                    return False
        return True

    def close(self):
        with suppress(OSError):
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
