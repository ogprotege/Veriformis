"""Versioned goal catalog v1: plain-language goals over existing objectives.

The catalog is packaged versioned data (``catalog-v1.json``) validated by
strict models. It is a naming and discovery layer only: every goal resolves to
exactly one persisted objective kind and one named recipe library id, and
every representation resolves to exactly one persisted row schema and its
taxonomy loss policy. It adds no objective, row schema, or learning behavior.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from veriformis.contracts import (
    PRODUCT_OBJECTIVE_KINDS,
    PRODUCT_ROW_SCHEMA_KINDS,
    V1_CONSTRUCTION_DIAGNOSTIC_CODES,
)
from veriformis.errors import (
    GoalCatalogError,
    InstructionNotApplicableError,
    InstructionRequiredError,
    InstructionTruthfulnessError,
    TaxonomyError,
)
from veriformis.recipes.library import RECIPE_LIBRARY_IDS
from veriformis.taxonomy import (
    DEFAULT_ROW_SCHEMA,
    IMPLEMENTED_INPUT_FAMILIES,
    IMPLEMENTED_PHYSICAL_CONTAINERS,
    LOSS_POLICY_IDS,
    OBJECTIVE_FAMILY,
    OBJECTIVE_ROW_COMPATIBILITY,
    ROW_LOSS_POLICY,
    ROW_SCHEMA_UI_ALIASES,
    INPUT_FAMILY_PARSERS,
    input_family_for_suffix,
)

GOAL_CATALOG_DATA_NAME = "catalog-v1.json"

# Closed v1 non-claim vocabulary. Every goal states all of them.
NON_CLAIM_CODES: tuple[str, ...] = (
    "no-trainer-compatibility",
    "no-generated-text",
    "no-invented-target",
    "no-fine-tuning-suitability-judgment",
)
REVIEW_POLICY_OPTIONS: tuple[str, ...] = ("none", "required")
_NON_GENERIC_CONTAINERS = frozenset(
    {
        "minimal-v1",
        "deterministic-vfbundle-zip-v1",
        "deterministic-export-pack-zip-v1",
    }
)
GENERIC_EXPORT_CONTAINERS: tuple[str, ...] = tuple(
    container
    for container in IMPLEMENTED_PHYSICAL_CONTAINERS
    if container not in _NON_GENERIC_CONTAINERS
)

_PLAIN_GOAL_FIELDS = (
    "title",
    "plain_language",
    "what_the_model_learns",
    "what_you_provide",
    "required_source_evidence",
    "target_construction",
    "supervision_boundary",
    "instruction_template",
    "instruction_task",
)
_PLAIN_REPRESENTATION_FIELDS = ("title", "plain_language", "supervised_region")
_FORBIDDEN_CLAIM_FRAGMENTS = ("summar", "answer", "translat")
_IDENTIFIER = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_MACHINE_IDENTIFIERS: tuple[str, ...] = tuple(
    sorted(
        token
        for token in {
            *PRODUCT_OBJECTIVE_KINDS,
            *PRODUCT_ROW_SCHEMA_KINDS,
            *LOSS_POLICY_IDS,
            *RECIPE_LIBRARY_IDS,
            *ROW_SCHEMA_UI_ALIASES,
        }
        if any(character in token for character in "_-.")
    )
)

ObjectiveKind = Literal[
    "full_text",
    "continuation",
    "section_reconstruction",
    "before_after_transformation",
    "structured_field",
    "explicit_label",
]
RowSchemaKind = Literal[
    "text",
    "prompt_completion",
    "instruction_output",
    "messages",
    "label-classification",
]
LossPolicyKind = Literal[
    "full-sequence",
    "completion-only",
    "output-only",
    "final-assistant-suffix",
    "label-only",
]


def _require_identifier(field: str, value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(
            f"{field} must match ^[a-z0-9]+(-[a-z0-9]+)*$; observed {value!r}"
        )
    return value


def _require_closed_sequence(
    field: str,
    value: tuple[str, ...],
    allowed: tuple[str, ...],
    *,
    ordered: bool = True,
) -> tuple[str, ...]:
    if not value or len(set(value)) != len(value):
        raise ValueError(f"{field} must be non-empty and unique")
    for item in value:
        if item not in allowed:
            raise ValueError(f"{field} names unknown identifier {item!r}; allowed {list(allowed)!r}")
    if ordered:
        expected = tuple(item for item in allowed if item in value)
        if value != expected:
            raise ValueError(f"{field} must follow taxonomy order {list(expected)!r}")
    return value


def _require_plain_text(field: str, value: str) -> str:
    if not value or value.strip() != value:
        raise ValueError(f"{field} must be non-empty without surrounding whitespace")
    if not value.isprintable():
        raise ValueError(f"{field} must not contain control characters")
    lowered = value.lower()
    for token in _MACHINE_IDENTIFIERS:
        if token in lowered:
            raise ValueError(f"{field} contains machine identifier {token!r}")
    return value


def _require_no_forbidden_claim(field: str, value: str) -> str:
    lowered = value.lower()
    for fragment in _FORBIDDEN_CLAIM_FRAGMENTS:
        if fragment in lowered:
            raise ValueError(
                f"{field} claims a transformation the source does not supply ({fragment!r})"
            )
    return value


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class CurationDefaults(_StrictModel):
    """Documented curation and split defaults a goal executes with.

    Phase 6.4 presets become the single executing source of these values;
    until then the catalog states them and a test proves they equal the
    defaults the service, CLI, MCP, runner, and library currently execute.
    """

    minimum_target_characters: int
    balance_mode: Literal["none", "primary_source_cap"]
    maximum_records_per_primary_source: int | None
    evaluation_ratio_ppm: int
    evaluation_required: bool
    split_seed: str

    @field_validator("minimum_target_characters")
    @classmethod
    def _minimum(cls, value: int) -> int:
        if type(value) is not int or value < 1:
            raise ValueError("minimum_target_characters must be a positive integer")
        return value

    @field_validator("evaluation_ratio_ppm")
    @classmethod
    def _ratio(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 999_999:
            raise ValueError("evaluation_ratio_ppm must be an integer within 1..999999")
        return value

    @field_validator("split_seed")
    @classmethod
    def _seed(cls, value: str) -> str:
        if not value or value.strip() != value or not value.isprintable():
            raise ValueError(
                "split_seed must be non-empty printable text without surrounding whitespace"
            )
        return value

    @model_validator(mode="after")
    def _executable(self) -> "CurationDefaults":
        from veriformis.datasets import CurationPolicy, SplitPolicy
        from veriformis.errors import CurationError

        try:
            CurationPolicy.create(
                minimum_target_characters=self.minimum_target_characters,
                balance_mode=self.balance_mode,
                maximum_records_per_primary_source=self.maximum_records_per_primary_source,
            )
            SplitPolicy.create(
                evaluation_ratio_ppm=self.evaluation_ratio_ppm,
                evaluation_required=self.evaluation_required,
                seed=self.split_seed,
            )
        except (CurationError, ValueError, TypeError) as exc:
            raise ValueError(
                f"curation_defaults are not an executable policy "
                f"(curation and split): {exc}"
            ) from exc
        return self


class GoalRepresentation(_StrictModel):
    """One plain-language representation bound to exactly one row schema."""

    representation_id: str
    title: str
    plain_language: str
    supervised_region: str
    row_schema: RowSchemaKind
    loss_policy: LossPolicyKind
    requires_operator_instruction: bool
    compatible_generic_exports: tuple[str, ...]

    @field_validator("compatible_generic_exports")
    @classmethod
    def _exports(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _require_closed_sequence(
            "compatible_generic_exports", value, GENERIC_EXPORT_CONTAINERS
        )

    @field_validator("representation_id")
    @classmethod
    def _identifier(cls, value: str) -> str:
        return _require_identifier("representation_id", value)

    @field_validator(*_PLAIN_REPRESENTATION_FIELDS)
    @classmethod
    def _plain(cls, value: str, info) -> str:
        return _require_no_forbidden_claim(
            info.field_name, _require_plain_text(info.field_name, value)
        )

    @field_validator("loss_policy")
    @classmethod
    def _loss(cls, value: str, info) -> str:
        row_schema = info.data.get("row_schema")
        if row_schema is not None and ROW_LOSS_POLICY[row_schema] != value:
            raise ValueError(
                f"loss_policy {value!r} does not match taxonomy loss policy "
                f"{ROW_LOSS_POLICY[row_schema]!r} for row_schema {row_schema!r}"
            )
        return value

    @field_validator("requires_operator_instruction")
    @classmethod
    def _instruction(cls, value: bool, info) -> bool:
        row_schema = info.data.get("row_schema")
        if row_schema is not None and value != (row_schema == "instruction_output"):
            raise ValueError(
                "requires_operator_instruction must be true exactly for the "
                "instruction_output row schema"
            )
        return value


class Goal(_StrictModel):
    """One plain-language goal bound to exactly one objective and recipe."""

    goal_id: str
    title: str
    plain_language: str
    what_the_model_learns: str
    what_you_provide: str
    not_this: tuple[str, ...]
    objective: ObjectiveKind
    training_family: str
    recipe_library_id: str
    default_representation: str
    compatible_representations: tuple[str, ...]
    eligible_input_families: tuple[str, ...]
    required_source_evidence: str
    required_evidence_diagnostics: tuple[str, ...]
    target_construction: str
    supervision_boundary: str
    curation_defaults: CurationDefaults
    review_policy_default: Literal["none", "required"]
    review_policy_options: tuple[str, ...]
    non_claims: tuple[str, ...]
    instruction_template: str
    instruction_task: str
    state: Literal["implemented"]

    @model_validator(mode="after")
    def _instruction_template_names_task(self) -> "Goal":
        if self.instruction_task.lower() not in self.instruction_template.lower():
            raise ValueError("instruction_template must contain instruction_task")
        return self

    @field_validator("eligible_input_families")
    @classmethod
    def _families(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _require_closed_sequence(
            "eligible_input_families", value, IMPLEMENTED_INPUT_FAMILIES
        )

    @field_validator("required_evidence_diagnostics")
    @classmethod
    def _diagnostics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _require_closed_sequence(
            "required_evidence_diagnostics",
            value,
            V1_CONSTRUCTION_DIAGNOSTIC_CODES,
            ordered=False,
        )

    @field_validator("review_policy_options")
    @classmethod
    def _review_options(cls, value: tuple[str, ...], info) -> tuple[str, ...]:
        if value != REVIEW_POLICY_OPTIONS:
            raise ValueError(
                f"review_policy_options must be exactly {list(REVIEW_POLICY_OPTIONS)!r}"
            )
        default = info.data.get("review_policy_default")
        if default is not None and default not in value:
            raise ValueError("review_policy_default must be one of review_policy_options")
        return value

    @field_validator("non_claims")
    @classmethod
    def _non_claims(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != NON_CLAIM_CODES:
            raise ValueError(f"non_claims must state exactly {list(NON_CLAIM_CODES)!r}")
        return value

    @field_validator("goal_id")
    @classmethod
    def _identifier(cls, value: str) -> str:
        return _require_identifier("goal_id", value)

    @field_validator(*_PLAIN_GOAL_FIELDS)
    @classmethod
    def _plain(cls, value: str, info) -> str:
        return _require_no_forbidden_claim(
            info.field_name, _require_plain_text(info.field_name, value)
        )

    @field_validator("not_this")
    @classmethod
    def _not_this(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("not_this must name at least one explicit non-claim")
        if len(set(value)) != len(value):
            raise ValueError("not_this must not repeat a non-claim")
        for item in value:
            _require_plain_text("not_this", item)
        return value

    @field_validator("training_family")
    @classmethod
    def _family(cls, value: str, info) -> str:
        objective = info.data.get("objective")
        if objective is not None and OBJECTIVE_FAMILY[objective] != value:
            raise ValueError(
                f"training_family {value!r} does not match taxonomy family "
                f"{OBJECTIVE_FAMILY[objective]!r} for objective {objective!r}"
            )
        return value

    @field_validator("recipe_library_id")
    @classmethod
    def _recipe(cls, value: str, info) -> str:
        objective = info.data.get("objective")
        if value not in RECIPE_LIBRARY_IDS:
            raise ValueError(f"recipe_library_id {value!r} is not a named recipe")
        if objective is not None and value.split(".", 1)[0] != objective:
            raise ValueError(
                f"recipe_library_id {value!r} does not belong to objective {objective!r}"
            )
        return value

    @field_validator("default_representation")
    @classmethod
    def _default(cls, value: str) -> str:
        return _require_identifier("default_representation", value)

    @field_validator("compatible_representations")
    @classmethod
    def _compatible(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(set(value)) != len(value):
            raise ValueError("compatible_representations must be non-empty and unique")
        for item in value:
            _require_identifier("compatible_representations", item)
        return value


class GoalCatalog(_StrictModel):
    """The complete versioned catalog, closed over the taxonomy."""

    schema_id: Literal["veriformis.goal-catalog/v1"]
    contract_id: Literal["veriformis.goal-catalog"]
    contract_version: int
    goals: tuple[Goal, ...]
    representations: tuple[GoalRepresentation, ...]

    @field_validator("contract_version")
    @classmethod
    def _version(cls, value: int) -> int:
        if type(value) is not int or value != 1:
            raise ValueError("contract_version must be exactly the integer 1")
        return value

    @field_validator("representations")
    @classmethod
    def _representations(
        cls, value: tuple[GoalRepresentation, ...]
    ) -> tuple[GoalRepresentation, ...]:
        ids = [rep.representation_id for rep in value]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate representation_id")
        rows = tuple(rep.row_schema for rep in value)
        if rows != PRODUCT_ROW_SCHEMA_KINDS:
            raise ValueError(
                "representations must cover every row schema exactly once in "
                f"taxonomy order {list(PRODUCT_ROW_SCHEMA_KINDS)!r}; observed {list(rows)!r}"
            )
        return value

    @field_validator("goals")
    @classmethod
    def _goals(cls, value: tuple[Goal, ...]) -> tuple[Goal, ...]:
        ids = [goal.goal_id for goal in value]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate goal_id")
        objectives = tuple(goal.objective for goal in value)
        if len(set(objectives)) != len(objectives):
            raise ValueError("each objective may back exactly one goal")
        if objectives != PRODUCT_OBJECTIVE_KINDS:
            raise ValueError(
                "goals must cover every objective exactly once in taxonomy order "
                f"{list(PRODUCT_OBJECTIVE_KINDS)!r}; observed {list(objectives)!r}"
            )
        return value

    def model_post_init(self, __context: Any) -> None:
        by_rep = {rep.representation_id: rep for rep in self.representations}
        for goal in self.goals:
            for rep_id in goal.compatible_representations:
                if rep_id not in by_rep:
                    raise ValueError(
                        f"goal {goal.goal_id!r} names unknown representation {rep_id!r}"
                    )
            rows = tuple(by_rep[rep_id].row_schema for rep_id in goal.compatible_representations)
            expected = OBJECTIVE_ROW_COMPATIBILITY[goal.objective]
            if rows != expected:
                raise ValueError(
                    f"goal {goal.goal_id!r} compatible representations resolve to "
                    f"{list(rows)!r}, but the taxonomy allows exactly {list(expected)!r}"
                )
            if goal.default_representation not in goal.compatible_representations:
                raise ValueError(
                    f"goal {goal.goal_id!r} default representation "
                    f"{goal.default_representation!r} is not compatible"
                )
            default_row = by_rep[goal.default_representation].row_schema
            if default_row != DEFAULT_ROW_SCHEMA[goal.objective]:
                raise ValueError(
                    f"goal {goal.goal_id!r} default representation resolves to "
                    f"{default_row!r}, but the taxonomy default is "
                    f"{DEFAULT_ROW_SCHEMA[goal.objective]!r}"
                )
        tasks = [goal.instruction_task.lower() for goal in self.goals]
        if len(set(tasks)) != len(tasks):
            raise ValueError("instruction_task must be unique per goal")

    def goal(self, goal_id: str) -> Goal:
        for goal in self.goals:
            if goal.goal_id == goal_id:
                return goal
        raise GoalCatalogError(
            f"unknown goal {goal_id!r}; expected one of "
            f"{[goal.goal_id for goal in self.goals]!r}"
        )

    def representation(self, representation_id: str) -> GoalRepresentation:
        for rep in self.representations:
            if rep.representation_id == representation_id:
                return rep
        raise GoalCatalogError(
            f"unknown representation {representation_id!r}; expected one of "
            f"{[rep.representation_id for rep in self.representations]!r}"
        )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _canonical_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def parse_goal_catalog(text: str, *, require_canonical: bool = False) -> GoalCatalog:
    """Validate catalog JSON text strictly, failing closed on any defect."""
    try:
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except ValueError as exc:
        raise GoalCatalogError(f"goal catalog is not valid JSON: {exc}") from exc
    if require_canonical and _canonical_text(payload) != text:
        raise GoalCatalogError("goal catalog bytes are not canonical")
    try:
        return GoalCatalog.model_validate_json(json.dumps(payload))
    except ValidationError as exc:
        detail = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise GoalCatalogError(f"goal catalog is invalid: {detail}") from exc
    except ValueError as exc:
        raise GoalCatalogError(f"goal catalog is invalid: {exc}") from exc


@lru_cache(maxsize=1)
def _packaged() -> tuple[str, GoalCatalog]:
    text = (
        resources.files("veriformis.goals")
        .joinpath(GOAL_CATALOG_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    return text, parse_goal_catalog(text, require_canonical=True)


def goal_catalog() -> GoalCatalog:
    """Return the validated packaged catalog (cached, immutable)."""
    return _packaged()[1]


def goal_catalog_json() -> str:
    """Return the exact canonical catalog text every surface must emit."""
    return _packaged()[0]


def discover_goals() -> dict[str, Any]:
    """Return a fresh, adapter-safe JSON-ready copy of the catalog."""
    return json.loads(goal_catalog_json())


def goal_for_objective(objective: str) -> Goal:
    for goal in goal_catalog().goals:
        if goal.objective == objective:
            return goal
    raise GoalCatalogError(
        f"unknown objective {objective!r}; expected one of "
        f"{list(PRODUCT_OBJECTIVE_KINDS)!r}"
    )


def representation_for_row_schema(row_schema: str) -> GoalRepresentation:
    for rep in goal_catalog().representations:
        if rep.row_schema == row_schema:
            return rep
    raise GoalCatalogError(
        f"unknown row schema {row_schema!r}; expected one of {list(PRODUCT_ROW_SCHEMA_KINDS)!r}"
    )


def resolve_goal(
    goal_id: str, representation_id: str | None = None
) -> tuple[str, str, str, str]:
    """Resolve a goal and optional representation to exact persisted identifiers.

    Returns ``(objective, row_schema, recipe_library_id, loss_policy)``.
    """
    catalog = goal_catalog()
    goal = catalog.goal(goal_id)
    rep_id = goal.default_representation if representation_id is None else representation_id
    rep = catalog.representation(rep_id)
    if rep_id not in goal.compatible_representations:
        raise GoalCatalogError(
            f"goal {goal_id!r} does not allow representation {rep_id!r}; "
            f"expected one of {list(goal.compatible_representations)!r}"
        )
    return goal.objective, rep.row_schema, goal.recipe_library_id, rep.loss_policy


def validate_instruction_text(goal: Goal, text: str) -> str:
    """Admit one instruction only when it names this goal's task and no other."""
    try:
        checked = _require_no_forbidden_claim(
            "instruction", _require_plain_text("instruction", text)
        )
    except ValueError as exc:
        raise InstructionTruthfulnessError(str(exc)) from exc
    if goal.instruction_task.lower() not in checked.lower():
        raise InstructionTruthfulnessError(
            f"instruction does not name the {goal.goal_id} task "
            f"({goal.instruction_task!r})"
        )
    return checked


def resolve_operator_instruction(
    *,
    goal: Goal | str | None = None,
    objective: str | None = None,
    representation: GoalRepresentation | str | None = None,
    row_schema: str | None = None,
    instruction: str | None = None,
) -> str | None:
    """Return the catalog template or a truthful operator instruction.

    Omitted instructions resolve to the goal's static template when the
    representation requires one. An empty supplied instruction fails closed.
    A supplied instruction is admitted only when it names this goal's task
    and contains no claim vocabulary for a transformation the goal does not
    perform.
    """
    catalog = goal_catalog()
    if isinstance(goal, Goal):
        resolved_goal = goal
    elif goal is not None:
        resolved_goal = catalog.goal(goal)
    elif objective is not None:
        resolved_goal = goal_for_objective(objective)
    else:
        raise GoalCatalogError("instruction resolution requires a goal or objective")

    if isinstance(representation, GoalRepresentation):
        resolved_rep = representation
    elif representation is not None:
        resolved_rep = catalog.representation(representation)
    elif row_schema is not None:
        resolved_rep = representation_for_row_schema(row_schema)
    else:
        resolved_rep = catalog.representation(resolved_goal.default_representation)

    if resolved_rep.representation_id not in resolved_goal.compatible_representations:
        raise GoalCatalogError(
            f"goal {resolved_goal.goal_id!r} does not allow representation "
            f"{resolved_rep.representation_id!r}"
        )
    if not resolved_rep.requires_operator_instruction:
        if instruction is not None:
            raise InstructionNotApplicableError(
                "instruction is valid only for the instruction-and-output representation"
            )
        return None
    if instruction is None:
        return validate_instruction_text(
            resolved_goal, resolved_goal.instruction_template
        )
    if not instruction or instruction.strip() != instruction:
        raise InstructionRequiredError(
            "instruction is required for the instruction-and-output representation"
        )
    return validate_instruction_text(resolved_goal, instruction)


def require_goal_input_family(
    goal_id: str,
    *,
    logical_path: str,
    parser_id: str,
) -> str:
    """Return the source family only when the goal may consume it.

    The logical suffix is the family authority and the observed parser must be
    one declared producer of that family. This function is shared by preflight
    and the real construct stage; otherwise synthetic PDF headings could be
    mistaken for source-supplied section or structured-field evidence.
    """
    try:
        family = input_family_for_suffix(Path(logical_path).suffix)
    except TaxonomyError as exc:
        raise GoalCatalogError(exc.message) from exc
    allowed_parsers = INPUT_FAMILY_PARSERS[family]
    if parser_id not in allowed_parsers:
        raise GoalCatalogError(
            f"source {logical_path!r} is classified as input family {family!r}, "
            f"but parser {parser_id!r} is not one of {list(allowed_parsers)!r}"
        )
    goal = goal_catalog().goal(goal_id)
    if family not in goal.eligible_input_families:
        raise GoalCatalogError(
            f"goal {goal_id!r} does not accept input family {family!r} for "
            f"source {logical_path!r}; expected one of "
            f"{list(goal.eligible_input_families)!r}"
        )
    return family


__all__ = [
    "GENERIC_EXPORT_CONTAINERS",
    "GOAL_CATALOG_DATA_NAME",
    "NON_CLAIM_CODES",
    "REVIEW_POLICY_OPTIONS",
    "CurationDefaults",
    "Goal",
    "GoalCatalog",
    "GoalRepresentation",
    "discover_goals",
    "goal_catalog",
    "goal_catalog_json",
    "goal_for_objective",
    "parse_goal_catalog",
    "representation_for_row_schema",
    "resolve_goal",
    "resolve_operator_instruction",
    "require_goal_input_family",
    "validate_instruction_text",
]
