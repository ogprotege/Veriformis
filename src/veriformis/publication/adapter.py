"""Publication adapter contract v1. Pins only; loading is not upload."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from veriformis.contracts import (
    PUBLICATION_ADAPTER_CONTRACT_ID,
    PUBLICATION_ADAPTER_CONTRACT_VERSION,
    PUBLICATION_ADAPTER_SCHEMA_ID,
)
from veriformis.errors import PublicationAdapterError
from veriformis.identity import derive_id, validate_id


DESTINATIONS: tuple[str, ...] = ("hugging-face-hub",)
VISIBILITIES: tuple[str, ...] = ("private", "public")
CREDENTIAL_SOURCES: tuple[str, ...] = ("none",)
PUBLICATION_ADAPTER_LIMITATIONS: tuple[str, ...] = (
    "no-execute",
    "no-hub-upload",
    "no-credentials-in-artifacts",
    "no-retry",
)

Destination = Literal["hugging-face-hub"]
Visibility = Literal["private", "public"]
CredentialSource = Literal["none"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class PublicationAdapter(_StrictModel):
    """One publication pin. Loading a pin is not upload."""

    adapter_id: str
    contract_id: Literal["veriformis.publication-adapter"]
    contract_version: Literal[1]
    credential_source: CredentialSource
    destination: Destination
    dry_run_required: Literal[True]
    execute_allowed: Literal[False]
    generation_allowed: Literal[False]
    local_container_is_not_upload: Literal[True]
    plugin_install_allowed: Literal[False]
    repository: str
    retry_allowed: Literal[False]
    revision: str
    schema_id: Literal["veriformis.publication-adapter/v1"]
    visibility: Visibility

    @model_validator(mode="after")
    def _closed(self) -> PublicationAdapter:
        if self.contract_id != PUBLICATION_ADAPTER_CONTRACT_ID:
            raise PublicationAdapterError("publication adapter contract_id mismatch")
        if self.contract_version != PUBLICATION_ADAPTER_CONTRACT_VERSION:
            raise PublicationAdapterError("publication adapter contract_version mismatch")
        if self.schema_id != PUBLICATION_ADAPTER_SCHEMA_ID:
            raise PublicationAdapterError("publication adapter schema_id mismatch")
        if self.execute_allowed is not False:
            raise PublicationAdapterError(
                "publication-adapter/v1 cannot allow execute; "
                "ADR-0020 Decision A installs no Hub upload"
            )
        if self.retry_allowed is not False:
            raise PublicationAdapterError(
                "publication-adapter/v1 cannot allow retry; "
                "ADR-0020 Decision A installs no network adapter"
            )
        if self.credential_source != "none":
            raise PublicationAdapterError(
                "publication-adapter/v1 credential_source must be none; "
                "credentials never persist in compiler artifacts"
            )
        if self.generation_allowed is not False:
            raise PublicationAdapterError(
                "publication-adapter/v1 cannot allow generation; "
                "ADR-0018 Decision A forbids a compile-path generator"
            )
        if self.plugin_install_allowed is not False:
            raise PublicationAdapterError(
                "publication-adapter/v1 cannot allow plugin install; "
                "ADR-0017 Decision A forbids an untrusted loader"
            )
        if not self.repository.strip() or self.repository.strip() != self.repository:
            raise PublicationAdapterError("repository must be a nonempty path string")
        if not self.revision.strip() or self.revision.strip() != self.revision:
            raise PublicationAdapterError("revision must be a nonempty path string")
        validate_id(self.adapter_id, kind="pub")
        expected = derive_id(
            "pub",
            self.model_dump(mode="json", exclude={"adapter_id"}),
        )
        if self.adapter_id != expected:
            raise PublicationAdapterError("publication adapter identity mismatch")
        return self


def create_publication_adapter(
    *,
    destination: str = "hugging-face-hub",
    repository: str,
    visibility: str = "private",
    revision: str,
    credential_source: str = "none",
    dry_run_required: bool = True,
    execute_allowed: bool = False,
    retry_allowed: bool = False,
    generation_allowed: bool = False,
    plugin_install_allowed: bool = False,
    local_container_is_not_upload: bool = True,
) -> PublicationAdapter:
    """Build one pin with a derived identity. This is not an upload."""
    payload = {
        "contract_id": PUBLICATION_ADAPTER_CONTRACT_ID,
        "contract_version": PUBLICATION_ADAPTER_CONTRACT_VERSION,
        "schema_id": PUBLICATION_ADAPTER_SCHEMA_ID,
        "destination": destination,
        "repository": repository,
        "visibility": visibility,
        "revision": revision,
        "credential_source": credential_source,
        "dry_run_required": dry_run_required,
        "execute_allowed": execute_allowed,
        "retry_allowed": retry_allowed,
        "generation_allowed": generation_allowed,
        "plugin_install_allowed": plugin_install_allowed,
        "local_container_is_not_upload": local_container_is_not_upload,
    }
    return PublicationAdapter(
        adapter_id=derive_id("pub", payload),
        **payload,
    )


def load_publication_adapter(payload: object) -> PublicationAdapter:
    if not isinstance(payload, dict):
        raise PublicationAdapterError("publication adapter must be an object")
    try:
        return PublicationAdapter.model_validate(payload)
    except PublicationAdapterError:
        raise
    except ValidationError as exc:
        message = str(exc)
        if "execute_allowed" in message:
            raise PublicationAdapterError(
                "publication-adapter/v1 cannot allow execute; "
                "ADR-0020 Decision A installs no Hub upload"
            ) from exc
        if "credential_source" in message:
            raise PublicationAdapterError(
                "publication-adapter/v1 credential_source must be none; "
                "credentials never persist in compiler artifacts"
            ) from exc
        if "extra" in message.lower() or "Extra" in message:
            raise PublicationAdapterError("unknown publication adapter field") from exc
        raise PublicationAdapterError("publication adapter is invalid") from exc
    except Exception as exc:
        raise PublicationAdapterError("publication adapter is invalid") from exc
