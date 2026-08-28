"""Leakage grouping keys for advanced families. Default SFT split is unchanged."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from veriformis.construction import DatasetRecord
from veriformis.datasets.splitting import (
    LeakageGroup,
    RecordAssignment,
    SplitPolicy,
    assign_leakage_partitions,
    build_leakage_groups,
)
from veriformis.errors import SplitError
from veriformis.families.admission import LEAKAGE_GROUPING_KEYS


SOURCE_GROUPING_KEY = "source"
EXTRA_GROUPING_KEYS: tuple[str, ...] = (
    "shared-prompt",
    "conversation",
    "annotator",
    "entity",
)


def keyed_leakage_groups(
    records: Sequence[DatasetRecord],
    raw_digests: Mapping[str, str],
    source_bases: Mapping[str, tuple[str, ...]],
    *,
    grouping_keys: Sequence[str],
    values_by_record: Mapping[str, Mapping[str, str]],
) -> tuple[LeakageGroup, ...]:
    """Union records that share selected grouping-key values.

    ``source`` keeps existing source-identity, raw-digest, and exact-record
    fingerprint bridging. Extra keys use caller-supplied exact strings. This
    function does not read record fields or guess values from free text.
    """
    keys = _checked_grouping_keys(grouping_keys)
    extra_tokens = _extra_tokens_by_record(records, keys, values_by_record)
    return build_leakage_groups(
        records,
        raw_digests,
        source_bases,
        extra_tokens,
    )


def keyed_split_assignments(
    policy: SplitPolicy,
    records: Sequence[DatasetRecord],
    raw_digests: Mapping[str, str],
    source_bases: Mapping[str, tuple[str, ...]],
    ordered_record_ids: Sequence[str],
    *,
    grouping_keys: Sequence[str],
    values_by_record: Mapping[str, Mapping[str, str]],
) -> tuple[tuple[LeakageGroup, ...], tuple[RecordAssignment, ...], int]:
    """Form keyed groups and assign whole groups with the SFT prefix algorithm."""
    groups = keyed_leakage_groups(
        records,
        raw_digests,
        source_bases,
        grouping_keys=grouping_keys,
        values_by_record=values_by_record,
    )
    assignments, requested = assign_leakage_partitions(
        policy,
        groups,
        ordered_record_ids,
    )
    return groups, assignments, requested


def _checked_grouping_keys(grouping_keys: Sequence[str]) -> tuple[str, ...]:
    if isinstance(grouping_keys, str) or not isinstance(grouping_keys, Sequence):
        raise SplitError("grouping_keys must be a sequence of tokens")
    keys = tuple(grouping_keys)
    if keys != tuple(sorted(set(keys))):
        raise SplitError("grouping_keys must be unique and sorted")
    if not keys:
        raise SplitError("grouping_keys must be a non-empty subset")
    unknown = [key for key in keys if key not in LEAKAGE_GROUPING_KEYS]
    if unknown:
        raise SplitError(
            f"unknown leakage grouping key: {unknown[0]!r}; admitted keys are "
            + ", ".join(LEAKAGE_GROUPING_KEYS)
        )
    if SOURCE_GROUPING_KEY not in keys:
        raise SplitError("grouping_keys must include source")
    return keys


def _extra_tokens_by_record(
    records: Sequence[DatasetRecord],
    grouping_keys: tuple[str, ...],
    values_by_record: Mapping[str, Mapping[str, str]],
) -> dict[str, tuple[tuple[str, str], ...]]:
    if not isinstance(values_by_record, Mapping):
        raise SplitError("grouping values must be a mapping of record id to key values")
    extra_keys = tuple(key for key in grouping_keys if key != SOURCE_GROUPING_KEY)
    record_ids = tuple(record.record_id for record in records)
    try:
        provided_ids = tuple(sorted(values_by_record))
    except TypeError as exc:
        raise SplitError("grouping value keys must be record identities") from exc
    if provided_ids != tuple(sorted(record_ids)):
        raise SplitError(
            "grouping values must cover included records exactly once"
        )
    extras: dict[str, tuple[tuple[str, str], ...]] = {}
    for record in records:
        supplied = values_by_record[record.record_id]
        if not isinstance(supplied, Mapping):
            raise SplitError(
                f"grouping values for {record.record_id} must be a mapping"
            )
        try:
            supplied_keys = tuple(sorted(supplied))
        except TypeError as exc:
            raise SplitError(
                f"grouping value names for {record.record_id} must be strings"
            ) from exc
        if supplied_keys != extra_keys:
            raise SplitError(
                "grouping values must supply exactly the selected extra keys "
                f"for {record.record_id}"
            )
        tokens: list[tuple[str, str]] = []
        for key in extra_keys:
            value = supplied[key]
            if type(value) is not str or value == "":
                raise SplitError(
                    f"grouping key {key!r} is missing or empty for {record.record_id}"
                )
            tokens.append((key, value))
        extras[record.record_id] = tuple(sorted(tokens))
    return extras
