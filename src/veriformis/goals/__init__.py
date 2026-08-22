"""Goal-first catalog: plain-language goals resolved to existing objectives."""

from veriformis.goals.catalog import (
    GOAL_CATALOG_DATA_NAME,
    Goal,
    GoalCatalog,
    GoalRepresentation,
    discover_goals,
    goal_catalog,
    goal_catalog_json,
    goal_for_objective,
    parse_goal_catalog,
    representation_for_row_schema,
    resolve_goal,
)

__all__ = [
    "GOAL_CATALOG_DATA_NAME",
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
]
