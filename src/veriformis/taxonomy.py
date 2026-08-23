"""Versioned goal, schema, container, profile, and loss-policy taxonomy.

This module is the Phase 3 machine registry. It reuses existing v1 objective,
row, bundle, transport, and Aptus identifiers. It does not change durable
identities or advertise planned families as implemented.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Literal, Mapping, NamedTuple

from veriformis.contracts import (
    DETERMINISTIC_V1_OBJECTIVE_KINDS,
    TAXONOMY_CONTRACT_ID,
    TAXONOMY_CONTRACT_VERSION,
    TAXONOMY_SCHEMA_ID,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.errors import TaxonomyError

CapabilityState = Literal[
    "implemented",
    "planned",
    "candidate",
    "explicitly_unsupported",
]

TAXONOMY_AXES: Final[tuple[str, ...]] = (
    "training_family",
    "objective",
    "semantic_row",
    "physical_container",
    "consumer_profile",
    "loss_policy",
    "input_family",
)

# Seventh axis (Phase 6.2, ADR-0008): the recovery-side input family. Each
# declared v1 suffix belongs to exactly one family, and each family names the
# parser kinds that produce its sources. Families classify recovery only; they
# never state what is learned.
IMPLEMENTED_INPUT_FAMILIES: Final[tuple[str, ...]] = (
    "plain-text",
    "source-code",
    "markdown",
    "word-document",
    "html",
    "pdf-text",
    "delimited-table",
    "json-records",
)
EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES: Final[tuple[str, ...]] = ("ocr-image",)
INPUT_FAMILY_SUFFIXES: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "plain-text": (".txt",),
        "source-code": (
            ".c",
            ".cpp",
            ".go",
            ".java",
            ".js",
            ".py",
            ".rb",
            ".rs",
            ".sh",
            ".ts",
        ),
        "markdown": (".markdown", ".md"),
        "word-document": (".docx",),
        "html": (".htm", ".html"),
        "pdf-text": (".pdf",),
        "delimited-table": (".csv",),
        "json-records": (".json", ".jsonl"),
    }
)
INPUT_FAMILY_PARSERS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "plain-text": ("text",),
        "source-code": ("text",),
        "markdown": ("markdown",),
        "word-document": ("docx",),
        "html": ("html",),
        "pdf-text": ("pdf",),
        "delimited-table": ("csv",),
        "json-records": ("json", "jsonl"),
    }
)

IMPLEMENTED_TRAINING_FAMILIES: Final[tuple[str, ...]] = (
    "source-grounded-language-modeling",
    "source-grounded-supervised-fine-tuning",
)
PLANNED_TRAINING_FAMILIES: Final[tuple[str, ...]] = (
    "preference-and-ranking",
    "explicit-label-classification",
    "tool-call-conversations",
    "stepwise-supervision",
    "pre-tokenized-training",
    "governed-generated-candidates",
)
EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES: Final[tuple[str, ...]] = (
    "multimodal-training",
)

IMPLEMENTED_PHYSICAL_CONTAINERS: Final[tuple[str, ...]] = (
    "minimal-v1",
    "deterministic-vfbundle-zip-v1",
    "deterministic-export-pack-zip-v1",
    "split-jsonl-directory",
    "json",
    "constrained-csv",
)
PLANNED_PHYSICAL_CONTAINERS: Final[tuple[str, ...]] = (
    "parquet",
    "arrow",
    "hugging-face-dataset",
)
UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS: Final[Mapping[str, str]] = MappingProxyType(
    {}
)

CANONICAL_CONSUMER_PROFILE: Final = "veriformis-canonical-v1"
IMPLEMENTED_CONSUMER_PROFILES: Final[tuple[str, ...]] = (
    CANONICAL_CONSUMER_PROFILE,
    "aptus-handoff-v1",
    "trl",
    "mlx-lm",
)
IMPLEMENTED_EXPORT_CONSUMER_PROFILES: Final[tuple[str, ...]] = (
    "trl",
    "mlx-lm",
)
EXPORT_CONSUMER_PROFILE_ITEMS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "trl": "8.3",
        "mlx-lm": "8.4",
    }
)
PLANNED_CONSUMER_PROFILES: Final[tuple[str, ...]] = ()
PLANNED_CONSUMER_PROFILE_ITEMS: Final[Mapping[str, str]] = MappingProxyType({})
UNEXECUTABLE_CONSUMER_PROFILE_ITEMS: Final[Mapping[str, str]] = MappingProxyType({})
CANDIDATE_CONSUMER_PROFILES: Final[tuple[str, ...]] = (
    "axolotl",
    "llama-factory",
    "unsloth",
)

LOSS_POLICY_IDS: Final[tuple[str, ...]] = (
    "full-sequence",
    "completion-only",
    "output-only",
    "final-assistant-suffix",
)

ROW_SCHEMA_UI_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "completion": "prompt_completion",
        "instruction": "instruction_output",
        "chat": "messages",
    }
)

OBJECTIVE_FAMILY: Final[Mapping[str, str]] = MappingProxyType(
    {
        "full_text": "source-grounded-language-modeling",
        "continuation": "source-grounded-supervised-fine-tuning",
        "section_reconstruction": "source-grounded-supervised-fine-tuning",
        "before_after_transformation": "source-grounded-supervised-fine-tuning",
        "structured_field": "source-grounded-supervised-fine-tuning",
    }
)

OBJECTIVE_ROW_COMPATIBILITY: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "full_text": ("text",),
        "continuation": ("prompt_completion", "instruction_output", "messages"),
        "section_reconstruction": (
            "prompt_completion",
            "instruction_output",
            "messages",
        ),
        "before_after_transformation": (
            "prompt_completion",
            "instruction_output",
            "messages",
        ),
        "structured_field": ("prompt_completion", "instruction_output", "messages"),
    }
)

DEFAULT_ROW_SCHEMA: Final[Mapping[str, str]] = MappingProxyType(
    {
        "full_text": "text",
        "continuation": "prompt_completion",
        "section_reconstruction": "prompt_completion",
        "before_after_transformation": "prompt_completion",
        "structured_field": "prompt_completion",
    }
)

ROW_LOSS_POLICY: Final[Mapping[str, str]] = MappingProxyType(
    {
        "text": "full-sequence",
        "prompt_completion": "completion-only",
        "instruction_output": "output-only",
        "messages": "final-assistant-suffix",
    }
)

LOSS_POLICY_BOUNDARIES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "full-sequence": "Entire text sequence is supervised.",
        "completion-only": "Prompt is context; completion receives supervision.",
        "output-only": (
            "Instruction and input are context; output receives supervision."
        ),
        "final-assistant-suffix": (
            "Only the final assistant message receives supervision."
        ),
    }
)

PROFILE_FORBIDDEN_ROW_SCHEMAS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        CANONICAL_CONSUMER_PROFILE: (),
        "aptus-handoff-v1": ("text",),
        "mlx-lm": (),
        "trl": (),
    }
)


class TaxonomyEntry(NamedTuple):
    axis: str
    identifier: str
    state: CapabilityState


def _known_identifiers() -> dict[str, set[str]]:
    return {
        "training_family": set(
            IMPLEMENTED_TRAINING_FAMILIES
            + PLANNED_TRAINING_FAMILIES
            + EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES
        ),
        "objective": set(DETERMINISTIC_V1_OBJECTIVE_KINDS),
        "semantic_row": set(V1_ROW_SCHEMA_KINDS),
        "physical_container": set(
            IMPLEMENTED_PHYSICAL_CONTAINERS + PLANNED_PHYSICAL_CONTAINERS
        ),
        "consumer_profile": set(
            IMPLEMENTED_CONSUMER_PROFILES
            + PLANNED_CONSUMER_PROFILES
            + CANDIDATE_CONSUMER_PROFILES
        ),
        "loss_policy": set(LOSS_POLICY_IDS),
        "input_family": set(
            IMPLEMENTED_INPUT_FAMILIES + EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES
        ),
    }


def require_axis(axis: str) -> str:
    if axis == "format" or axis not in TAXONOMY_AXES:
        raise TaxonomyError(
            f"unknown taxonomy axis {axis!r}; expected one of {list(TAXONOMY_AXES)!r}"
        )
    return axis


def require_identifier(axis: str, identifier: str) -> str:
    require_axis(axis)
    if identifier in ROW_SCHEMA_UI_ALIASES:
        raise TaxonomyError(
            f"{identifier!r} is a UI alias for "
            f"{ROW_SCHEMA_UI_ALIASES[identifier]!r} and MUST NOT be persisted"
        )
    known = _known_identifiers()[axis]
    if identifier not in known:
        raise TaxonomyError(f"unknown {axis.replace('_', ' ')} {identifier!r}")
    return identifier


def input_family_for_suffix(suffix: str) -> str:
    """Return the implemented input family that owns one declared suffix.

    Accepts a bare or dotted suffix in any letter case, mirroring parser
    dispatch, and fails closed for anything no implemented family owns.
    """
    normalized = suffix.lower()
    if not normalized.startswith("."):
        normalized = f".{normalized}"
    for family, suffixes in INPUT_FAMILY_SUFFIXES.items():
        if normalized in suffixes:
            return family
    raise TaxonomyError(f"no implemented input family owns suffix {suffix!r}")


def input_family_for_parser(parser: str) -> tuple[str, ...]:
    """Return every implemented input family produced by one parser kind."""
    families = tuple(
        family
        for family, parsers in INPUT_FAMILY_PARSERS.items()
        if parser in parsers
    )
    if not families:
        raise TaxonomyError(f"no implemented input family is produced by parser {parser!r}")
    return families


def family_for_objective(objective: str) -> str:
    require_identifier("objective", objective)
    return OBJECTIVE_FAMILY[objective]


def compatible_row_schemas(objective: str) -> tuple[str, ...]:
    require_identifier("objective", objective)
    return OBJECTIVE_ROW_COMPATIBILITY[objective]


def default_row_schema(objective: str) -> str:
    require_identifier("objective", objective)
    return DEFAULT_ROW_SCHEMA[objective]


def loss_policy_for_row(row_schema: str) -> str:
    require_identifier("semantic_row", row_schema)
    return ROW_LOSS_POLICY[row_schema]


def loss_boundary(loss_policy: str) -> str:
    require_identifier("loss_policy", loss_policy)
    return LOSS_POLICY_BOUNDARIES[loss_policy]


def assert_objective_row_compatible(objective: str, row_schema: str) -> None:
    require_identifier("objective", objective)
    require_identifier("semantic_row", row_schema)
    allowed = OBJECTIVE_ROW_COMPATIBILITY[objective]
    if row_schema not in allowed:
        if objective == "full_text":
            raise TaxonomyError("full_text recipes require the product 'text' row schema")
        if row_schema == "text":
            raise TaxonomyError(
                f"objective {objective!r} requires a supervised row schema"
            )
        raise TaxonomyError(
            f"objective {objective!r} does not allow row schema {row_schema!r}"
        )


def assert_profile_row_compatible(profile: str, row_schema: str) -> None:
    require_identifier("consumer_profile", profile)
    require_identifier("semantic_row", row_schema)
    if profile not in IMPLEMENTED_CONSUMER_PROFILES:
        raise TaxonomyError(
            f"consumer profile {profile!r} is not implemented and cannot be selected"
        )
    forbidden = PROFILE_FORBIDDEN_ROW_SCHEMAS.get(profile, ())
    if row_schema in forbidden:
        raise TaxonomyError(
            f"consumer profile {profile!r} does not accept row schema {row_schema!r}"
        )


def assert_compile_combination(
    objective: str,
    row_schema: str,
    *,
    profile: str = CANONICAL_CONSUMER_PROFILE,
) -> None:
    """Fail closed before compile when an axis combination is invalid."""
    require_identifier("objective", objective)
    family = family_for_objective(objective)
    if family not in IMPLEMENTED_TRAINING_FAMILIES:
        raise TaxonomyError(
            f"training family {family!r} is not implemented and cannot be compiled"
        )
    assert_objective_row_compatible(objective, row_schema)
    assert_profile_row_compatible(profile, row_schema)
    require_identifier("loss_policy", loss_policy_for_row(row_schema))


def catalog() -> tuple[TaxonomyEntry, ...]:
    """Return every named identifier with its support state, axis by axis."""
    entries: list[TaxonomyEntry] = []
    for identifier in IMPLEMENTED_TRAINING_FAMILIES:
        entries.append(TaxonomyEntry("training_family", identifier, "implemented"))
    for identifier in PLANNED_TRAINING_FAMILIES:
        entries.append(TaxonomyEntry("training_family", identifier, "planned"))
    for identifier in EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES:
        entries.append(
            TaxonomyEntry("training_family", identifier, "explicitly_unsupported")
        )
    for identifier in DETERMINISTIC_V1_OBJECTIVE_KINDS:
        entries.append(TaxonomyEntry("objective", identifier, "implemented"))
    for identifier in V1_ROW_SCHEMA_KINDS:
        entries.append(TaxonomyEntry("semantic_row", identifier, "implemented"))
    for identifier in IMPLEMENTED_PHYSICAL_CONTAINERS:
        entries.append(TaxonomyEntry("physical_container", identifier, "implemented"))
    for identifier in PLANNED_PHYSICAL_CONTAINERS:
        entries.append(TaxonomyEntry("physical_container", identifier, "planned"))
    for identifier in IMPLEMENTED_CONSUMER_PROFILES:
        entries.append(TaxonomyEntry("consumer_profile", identifier, "implemented"))
    for identifier in PLANNED_CONSUMER_PROFILES:
        entries.append(TaxonomyEntry("consumer_profile", identifier, "planned"))
    for identifier in CANDIDATE_CONSUMER_PROFILES:
        entries.append(TaxonomyEntry("consumer_profile", identifier, "candidate"))
    for identifier in LOSS_POLICY_IDS:
        entries.append(TaxonomyEntry("loss_policy", identifier, "implemented"))
    for identifier in IMPLEMENTED_INPUT_FAMILIES:
        entries.append(TaxonomyEntry("input_family", identifier, "implemented"))
    for identifier in EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES:
        entries.append(
            TaxonomyEntry("input_family", identifier, "explicitly_unsupported")
        )
    return tuple(entries)


def implemented_discovery() -> Mapping[str, tuple[str, ...]]:
    """Surface-neutral implemented identifiers, never a collapsed format field."""
    return MappingProxyType(
        {
            "contract_id": (TAXONOMY_CONTRACT_ID,),
            "contract_version": (str(TAXONOMY_CONTRACT_VERSION),),
            "schema_id": (TAXONOMY_SCHEMA_ID,),
            "training_family": IMPLEMENTED_TRAINING_FAMILIES,
            "objective": DETERMINISTIC_V1_OBJECTIVE_KINDS,
            "semantic_row": V1_ROW_SCHEMA_KINDS,
            "physical_container": IMPLEMENTED_PHYSICAL_CONTAINERS,
            "consumer_profile": IMPLEMENTED_CONSUMER_PROFILES,
            "loss_policy": LOSS_POLICY_IDS,
            "input_family": IMPLEMENTED_INPUT_FAMILIES,
        }
    )


__all__ = [
    "CANONICAL_CONSUMER_PROFILE",
    "CANDIDATE_CONSUMER_PROFILES",
    "DEFAULT_ROW_SCHEMA",
    "EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES",
    "EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES",
    "IMPLEMENTED_CONSUMER_PROFILES",
    "IMPLEMENTED_EXPORT_CONSUMER_PROFILES",
    "EXPORT_CONSUMER_PROFILE_ITEMS",
    "IMPLEMENTED_INPUT_FAMILIES",
    "INPUT_FAMILY_PARSERS",
    "INPUT_FAMILY_SUFFIXES",
    "IMPLEMENTED_PHYSICAL_CONTAINERS",
    "IMPLEMENTED_TRAINING_FAMILIES",
    "LOSS_POLICY_BOUNDARIES",
    "LOSS_POLICY_IDS",
    "OBJECTIVE_FAMILY",
    "OBJECTIVE_ROW_COMPATIBILITY",
    "PLANNED_CONSUMER_PROFILE_ITEMS",
    "PLANNED_CONSUMER_PROFILES",
    "UNEXECUTABLE_CONSUMER_PROFILE_ITEMS",
    "UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS",
    "PLANNED_PHYSICAL_CONTAINERS",
    "PLANNED_TRAINING_FAMILIES",
    "PROFILE_FORBIDDEN_ROW_SCHEMAS",
    "ROW_LOSS_POLICY",
    "ROW_SCHEMA_UI_ALIASES",
    "TAXONOMY_AXES",
    "TaxonomyEntry",
    "assert_compile_combination",
    "assert_objective_row_compatible",
    "assert_profile_row_compatible",
    "catalog",
    "compatible_row_schemas",
    "default_row_schema",
    "family_for_objective",
    "input_family_for_parser",
    "input_family_for_suffix",
    "implemented_discovery",
    "loss_boundary",
    "loss_policy_for_row",
    "require_axis",
    "require_identifier",
]
