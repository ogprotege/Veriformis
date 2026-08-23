"""Phase 6.7: catalog defaults and deterministic instruction truthfulness."""

from __future__ import annotations

import pytest

from veriformis.errors import GoalInstructionError
from veriformis.goals import goal_catalog, resolve_goal_instruction


EXPECTED_DEFAULTS = {
    "continuation": "Continue the passage with its exact source remainder.",
    "section_reconstruction": (
        "Produce the exact source section body for this heading."
    ),
    "before_after_transformation": (
        "Apply the recorded cleaning change to this exact source text."
    ),
    "structured_field": (
        "Produce the exact structural attribute recorded by this source."
    ),
}


def test_catalog_owns_the_only_default_instruction_for_each_supervised_goal() -> None:
    by_objective = {goal.objective: goal for goal in goal_catalog().goals}

    assert by_objective["full_text"].default_instruction is None
    assert by_objective["full_text"].instruction_task_claim is None
    for objective, expected in EXPECTED_DEFAULTS.items():
        goal = by_objective[objective]
        assert goal.default_instruction == expected
        assert goal.instruction_task_claim is not None


@pytest.mark.parametrize(("objective", "expected"), EXPECTED_DEFAULTS.items())
def test_omitted_instruction_resolves_to_the_catalog_default(
    objective: str, expected: str
) -> None:
    resolved = resolve_goal_instruction(
        objective=objective,
        row_schema="instruction_output",
        instruction=None,
    )

    assert resolved.instruction_text == expected
    assert resolved.source == "catalog-default"


@pytest.mark.parametrize(
    ("objective", "instruction"),
    [
        ("continuation", "Continue with the exact source remainder."),
        (
            "section_reconstruction",
            "Produce the section body recorded beneath this heading.",
        ),
        (
            "before_after_transformation",
            "Apply the recorded cleaning change to this source text.",
        ),
        (
            "structured_field",
            "Produce the structural attribute recorded by this source.",
        ),
    ],
)
def test_operator_instruction_is_preserved_only_when_it_names_the_goal_task(
    objective: str, instruction: str
) -> None:
    resolved = resolve_goal_instruction(
        objective=objective,
        row_schema="instruction_output",
        instruction=instruction,
    )

    assert resolved.instruction_text == instruction
    assert resolved.source == "operator"


@pytest.mark.parametrize("objective", EXPECTED_DEFAULTS)
@pytest.mark.parametrize(
    "instruction",
    [
        "Summarize the source.",
        "Continue the passage and produce a summarization.",
        "Translate the source.",
        "Continue the passage with a translated ending.",
        "Answer a question about the source.",
        "Explain the source.",
        "Continue the passage with an explained ending.",
        "Paraphrase the source.",
        "Continue the passage with a paraphrased ending.",
        "Rewrite the source.",
        "Continue the passage with a rewritten ending.",
        "Invent a new ending.",
        "Continue the passage with an invented ending.",
        "Continue creatively.",
        "Continue the passage creatively.",
        "Discontinue the passage and do something else.",
        "Do not continue the passage.",
        "Produce the exact source-derived target.",
    ],
)
def test_operator_instruction_refuses_absent_or_unnamed_transformations(
    objective: str, instruction: str
) -> None:
    with pytest.raises(GoalInstructionError) as excinfo:
        resolve_goal_instruction(
            objective=objective,
            row_schema="instruction_output",
            instruction=instruction,
        )

    assert excinfo.value.reason_codes
    assert set(excinfo.value.reason_codes) <= {
        "instruction-empty",
        "goal-task-not-named",
        "absent-transformation-claimed",
    }


@pytest.mark.parametrize(
    ("objective", "other_task"),
    [
        ("continuation", "Produce the section body for this heading."),
        ("section_reconstruction", "Continue with the source remainder."),
        ("before_after_transformation", "Produce the structural attribute."),
        ("structured_field", "Apply the recorded cleaning change."),
    ],
)
def test_operator_instruction_refuses_another_goal_task(
    objective: str, other_task: str
) -> None:
    with pytest.raises(GoalInstructionError) as excinfo:
        resolve_goal_instruction(
            objective=objective,
            row_schema="instruction_output",
            instruction=other_task,
        )

    assert "absent-transformation-claimed" in excinfo.value.reason_codes


@pytest.mark.parametrize(
    ("objective", "instruction"),
    [
        ("continuation", "Continue the passage but shorten the source."),
        ("continuation", "Continue the passage and reorder the source."),
        (
            "section_reconstruction",
            "Produce the section body as an outline.",
        ),
        (
            "before_after_transformation",
            "Apply the recorded change as general editing.",
        ),
        (
            "before_after_transformation",
            "Apply the recorded change as style transfer.",
        ),
        (
            "structured_field",
            "Produce the structural attribute by inferring it.",
        ),
        (
            "structured_field",
            "Produce the structural attribute by guessing it.",
        ),
        (
            "structured_field",
            "Produce the structural attribute by computing it.",
        ),
    ],
)
def test_operator_instruction_refuses_catalog_non_claim_transformations(
    objective: str, instruction: str
) -> None:
    with pytest.raises(GoalInstructionError) as excinfo:
        resolve_goal_instruction(
            objective=objective,
            row_schema="instruction_output",
            instruction=instruction,
        )
    assert "absent-transformation-claimed" in excinfo.value.reason_codes


@pytest.mark.parametrize("instruction", ["", "   ", "Continue the passage.\n"])
def test_operator_instruction_refuses_empty_surrounding_or_control_text(
    instruction: str,
) -> None:
    with pytest.raises(GoalInstructionError):
        resolve_goal_instruction(
            objective="continuation",
            row_schema="instruction_output",
            instruction=instruction,
        )


def test_instruction_is_not_applicable_outside_instruction_output() -> None:
    absent = resolve_goal_instruction(
        objective="continuation",
        row_schema="prompt_completion",
        instruction=None,
    )
    assert absent.instruction_text is None
    assert absent.source == "not-applicable"

    with pytest.raises(GoalInstructionError) as excinfo:
        resolve_goal_instruction(
            objective="continuation",
            row_schema="prompt_completion",
            instruction="Continue the passage.",
        )
    assert excinfo.value.reason_codes == ("instruction-not-applicable",)


def test_instruction_resolution_refuses_unknown_or_goal_incompatible_row_schema() -> None:
    with pytest.raises(GoalInstructionError) as unknown:
        resolve_goal_instruction(
            objective="continuation",
            row_schema="made_up_row",
            instruction=None,
        )
    assert unknown.value.reason_codes == ("instruction-not-applicable",)

    with pytest.raises(GoalInstructionError) as incompatible:
        resolve_goal_instruction(
            objective="full_text",
            row_schema="instruction_output",
            instruction=None,
        )
    assert incompatible.value.reason_codes == ("instruction-not-applicable",)


@pytest.mark.parametrize("instruction", [7, True, ["Continue the passage."]])
def test_instruction_resolution_refuses_non_string_operator_values(instruction) -> None:
    with pytest.raises(GoalInstructionError) as excinfo:
        resolve_goal_instruction(
            objective="continuation",
            row_schema="instruction_output",
            instruction=instruction,
        )
    assert excinfo.value.reason_codes == ("instruction-not-plain",)
