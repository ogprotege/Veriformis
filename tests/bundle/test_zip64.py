"""D-16: canonical ZIP64 sizes and offsets survive transport validation."""
from __future__ import annotations

import struct
import zipfile

import pytest

from veriformis._archive_transport import (
    CanonicalArchiveError, require_canonical_archive_structure, write_deterministic_archive,
)


def test_writer_zip64_sizes_and_offsets_are_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 100)
    source = tmp_path / "source"
    source.mkdir()
    (source / "a").write_bytes(b"x" * 256)
    (source / "b").write_bytes(b"y")
    target = tmp_path / "archive.zip"
    write_deterministic_archive(source, target, members=("a", "b"))
    with zipfile.ZipFile(target) as archive:
        assert archive.getinfo("a").extra == struct.pack("<HHQQ", 1, 16, 256, 256)
        assert archive.getinfo("b").extra == struct.pack("<HHQ", 1, 8, archive.getinfo("b").header_offset)
        by_name, names = require_canonical_archive_structure(archive, expected_members=("a", "b"))
        assert names == ("a", "b")
        for name in names:
            assert archive.read(by_name[name]) == (source / name).read_bytes()


@pytest.mark.parametrize("extra", [b"\x01", struct.pack("<HH", 2, 0), struct.pack("<HHQQ", 1, 16, 2, 2), struct.pack("<HH", 1, 0) * 2])
def test_unnecessary_malformed_or_unknown_extra_refuses(tmp_path, extra):
    source = tmp_path / "source"
    source.mkdir()
    (source / "a").write_bytes(b"x")
    target = tmp_path / "archive.zip"
    write_deterministic_archive(source, target, members=("a",))
    with zipfile.ZipFile(target) as archive:
        archive.getinfo("a").extra = extra
        with pytest.raises(CanonicalArchiveError, match="metadata"):
            require_canonical_archive_structure(archive, expected_members=("a",))
