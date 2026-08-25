"""First-class collection ingest: plan membership, then capture."""

from veriformis.collection.plan import (
    COLLECTION_PLAN_SCHEMA_ID,
    COLLECTION_PLAN_SCHEMA_VERSION,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_VISITED,
    CollectionCounts,
    CollectionMember,
    CollectionPlan,
    CollectionSettings,
    accepted_source_paths,
    build_collection_plan,
    default_collection_settings,
)

__all__ = [
    "COLLECTION_PLAN_SCHEMA_ID",
    "COLLECTION_PLAN_SCHEMA_VERSION",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_FILES",
    "DEFAULT_MAX_VISITED",
    "CollectionCounts",
    "CollectionMember",
    "CollectionPlan",
    "CollectionSettings",
    "accepted_source_paths",
    "build_collection_plan",
    "default_collection_settings",
]
