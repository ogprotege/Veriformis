"""Collection plan: directory expansion, safety, and deterministic identity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from veriformis.collection import (
    CollectionSettings,
    accepted_source_paths,
    build_collection_plan,
)
from veriformis.errors import CollectionError, CollectionLimitError, InvalidSourceLocatorError
from veriformis.pipeline import PipelineService


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_explicit_files_are_accepted_in_logical_order(tmp_path: Path) -> None:
    first = _write(tmp_path / "b.txt", "b")
    second = _write(tmp_path / "a.txt", "a")
    plan = build_collection_plan([first, second], source_root=tmp_path)
    assert plan.accepted_logical_paths() == ("a.txt", "b.txt")
    assert plan.counts.accepted == 2
    assert plan.counts.ignored == 0
    again = build_collection_plan([second, first], source_root=tmp_path)
    assert again.plan_id == plan.plan_id


def test_directory_expansion_skips_hidden_and_unsupported(tmp_path: Path) -> None:
    _write(tmp_path / "keep.txt", "keep")
    _write(tmp_path / "skip.bin", "nope")
    _write(tmp_path / ".secret.txt", "hidden")
    _write(tmp_path / "nested" / "more.md", "# more\n")
    plan = build_collection_plan([tmp_path], source_root=tmp_path)
    assert plan.accepted_logical_paths() == ("keep.txt", "nested/more.md")
    reasons = {member.logical_path: member.reason for member in plan.members}
    assert reasons["skip.bin"] == "unsupported-suffix"
    assert reasons[".secret.txt"] == "hidden"


def test_symlink_is_refused_and_not_followed(tmp_path: Path) -> None:
    target = _write(tmp_path / "real.txt", "real")
    link = tmp_path / "alias.txt"
    link.symlink_to(target)
    plan = build_collection_plan([tmp_path], source_root=tmp_path)
    refused = [member for member in plan.members if member.status == "refused"]
    assert refused == [
        member
        for member in plan.members
        if member.logical_path == "alias.txt" and member.reason == "symlink"
    ]
    assert plan.accepted_logical_paths() == ("real.txt",)


def test_duplicate_bytes_are_counted(tmp_path: Path) -> None:
    _write(tmp_path / "one.txt", "same")
    _write(tmp_path / "two.txt", "same")
    plan = build_collection_plan([tmp_path], source_root=tmp_path)
    assert plan.counts.accepted == 1
    assert plan.counts.duplicate == 1
    duplicate = next(member for member in plan.members if member.status == "duplicate")
    assert duplicate.reason is not None and duplicate.reason.startswith("duplicate-bytes:")


def test_max_files_fails_closed(tmp_path: Path) -> None:
    _write(tmp_path / "a.txt", "a")
    _write(tmp_path / "b.txt", "b")
    with pytest.raises(CollectionLimitError, match="max_files"):
        build_collection_plan(
            [tmp_path],
            source_root=tmp_path,
            settings=CollectionSettings(max_files=1),
        )


def test_unsupported_refuse_policy_fails_the_collection(tmp_path: Path) -> None:
    _write(tmp_path / "ok.txt", "ok")
    _write(tmp_path / "nope.bin", "x")
    with pytest.raises(CollectionError, match="unsupported suffix"):
        build_collection_plan(
            [tmp_path],
            source_root=tmp_path,
            settings=CollectionSettings(unsupported_policy="refuse"),
        )


def test_package_directory_is_not_recursed(tmp_path: Path) -> None:
    _write(tmp_path / "visible.txt", "ok")
    _write(tmp_path / "Helper.app" / "Contents" / "info.txt", "nope")
    plan = build_collection_plan([tmp_path], source_root=tmp_path)
    assert plan.accepted_logical_paths() == ("visible.txt",)
    ignored = next(member for member in plan.members if member.reason == "package-directory")
    assert ignored.logical_path == "Helper.app"


def test_empty_directory_fails_closed(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(CollectionError, match="accepted no sources"):
        build_collection_plan([empty], source_root=tmp_path)


def test_path_outside_root_fails(tmp_path: Path) -> None:
    inside = _write(tmp_path / "root" / "a.txt", "a")
    outside = _write(tmp_path / "other" / "b.txt", "b")
    with pytest.raises(InvalidSourceLocatorError, match="outside source root"):
        build_collection_plan([inside, outside], source_root=tmp_path / "root")


def test_parse_directory_matches_explicit_files(tmp_path: Path) -> None:
    sources = tmp_path / "sources"
    _write(sources / "a.txt", "alpha paragraph.\n")
    _write(sources / "b.md", "# Title\n\nBody.\n")
    service = PipelineService()
    from_dir = tmp_path / "from-dir"
    from_files = tmp_path / "from-files"
    dir_outcome = service.parse([sources], from_dir, source_root=sources)
    file_outcome = service.parse(
        [sources / "a.txt", sources / "b.md"],
        from_files,
        source_root=sources,
    )
    assert dir_outcome.source_count == 2
    assert file_outcome.source_count == 2
    assert dir_outcome.messages[0].text.startswith("collection ")
    plan = service.collect([sources], source_root=sources).plan
    assert plan is not None
    payload = json.loads(plan.transport_text())
    assert payload["schema_id"] == "veriformis.collection-plan/v1"
    resolved = accepted_source_paths(plan, source_root=sources)
    assert [path.name for path in resolved] == ["a.txt", "b.md"]


def test_cli_collect_prints_plan(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from veriformis.cli import app

    _write(tmp_path / "note.txt", "hello\n")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["collect", str(tmp_path / "note.txt"), "--source-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["schema_id"] == "veriformis.collection-plan/v1"
    assert payload["counts"]["accepted"] == 1


def test_byte_limit_is_enforced_before_any_file_is_hashed(tmp_path: Path, monkeypatch) -> None:
    """Post-20 defect D-22: limits are checked from directory sizes, not after hashing."""
    import veriformis.collection.plan as plan_module

    (tmp_path / "a.txt").write_bytes(b"x" * 1000)
    (tmp_path / "b.txt").write_bytes(b"y" * 1000)
    hashed: list[str] = []
    original = plan_module._file_digest

    def counting_digest(path: Path) -> str:
        hashed.append(path.name)
        return original(path)

    monkeypatch.setattr(plan_module, "_file_digest", counting_digest)
    with pytest.raises(CollectionLimitError, match="max_bytes"):
        build_collection_plan(
            [tmp_path],
            source_root=tmp_path,
            settings=CollectionSettings(max_bytes=1500),
        )
    # The first file may be hashed; the second is refused before its digest.
    assert hashed == ["a.txt"]


def test_file_limit_is_enforced_before_hashing_the_extra_file(tmp_path: Path, monkeypatch) -> None:
    import veriformis.collection.plan as plan_module

    (tmp_path / "a.txt").write_bytes(b"x")
    (tmp_path / "b.txt").write_bytes(b"y")
    hashed: list[str] = []
    original = plan_module._file_digest

    def counting_digest(path: Path) -> str:
        hashed.append(path.name)
        return original(path)

    monkeypatch.setattr(plan_module, "_file_digest", counting_digest)
    with pytest.raises(CollectionLimitError, match="max_files"):
        build_collection_plan(
            [tmp_path],
            source_root=tmp_path,
            settings=CollectionSettings(max_files=1),
        )
    assert hashed == ["a.txt"]


def test_duplicate_owner_and_plan_id_do_not_depend_on_argument_order(tmp_path: Path) -> None:
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    (tmp_path / "one" / "same.txt").write_bytes(b"identical bytes")
    (tmp_path / "two" / "same.txt").write_bytes(b"identical bytes")
    forward = build_collection_plan(
        [tmp_path / "one", tmp_path / "two"], source_root=tmp_path
    )
    reverse = build_collection_plan(
        [tmp_path / "two", tmp_path / "one"], source_root=tmp_path
    )
    assert forward.plan_id == reverse.plan_id
    duplicates = [member for member in forward.members if member.status == "duplicate"]
    assert [member.reason for member in duplicates] == ["duplicate-bytes:one/same.txt"]
