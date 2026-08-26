"""Pinned OCR engine and page-recovery identities.

Tesseract 5 is named after the operator accepted the 12.2 evaluation.
These models do not import Tesseract. Default parse still refuses
image-only PDFs. Optional recovery is a separate subprocess provider.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import (
    OCR_RECOVERY_IDENTITY_CONTRACT_ID,
    OCR_RECOVERY_IDENTITY_CONTRACT_VERSION,
    OCR_RECOVERY_IDENTITY_SCHEMA_ID,
)
from veriformis.errors import OcrIdentityError
from veriformis.identity import derive_id, validate_sha256


ADMITTED_ENGINE_ID = "tesseract"
ADMITTED_ENGINE_FAMILY = "tesseract-5"
ADMITTED_LANGUAGES: tuple[str, ...] = ("eng", "fra", "lat")
ADMITTED_PSM: tuple[int, ...] = (6,)
PREPROCESS_IDS: tuple[str, ...] = (
    "render-pdf-page/v1",
    "osd-rotate/v1",
)
RECOVERY_PATHS: tuple[str, ...] = ("digital", "ocr", "merged")
LIMITATIONS: tuple[str, ...] = (
    "handwriting-unsupported",
    "cloud-ocr-forbidden",
    "no-network",
    "rotation-requires-explicit-preprocess",
    "ocr-recovery-not-executable",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class OcrEnginePin(_StrictModel):
    admitted_languages: tuple[str, ...]
    admitted_psm: tuple[int, ...]
    contract_id: str
    contract_version: int
    engine_family: Literal["tesseract-5"]
    engine_id: Literal["tesseract"]
    executable: Literal[False]
    extra: Literal["ocr"]
    extra_declared: bool
    license: Literal["Apache-2.0"]
    limitations: tuple[str, ...]
    measured_version: str
    min_version: str
    preprocess_ids: tuple[str, ...]
    schema_id: str

    @field_validator("admitted_languages", "limitations", "preprocess_ids", mode="before")
    @classmethod
    def _tuple_str(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("admitted_psm", mode="before")
    @classmethod
    def _tuple_int(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> OcrEnginePin:
        if self.contract_id != OCR_RECOVERY_IDENTITY_CONTRACT_ID:
            raise OcrIdentityError("OCR engine pin contract_id is invalid")
        if self.contract_version != OCR_RECOVERY_IDENTITY_CONTRACT_VERSION:
            raise OcrIdentityError("OCR engine pin contract_version is invalid")
        if self.schema_id != OCR_RECOVERY_IDENTITY_SCHEMA_ID:
            raise OcrIdentityError("OCR engine pin schema_id is invalid")
        if self.admitted_languages != ADMITTED_LANGUAGES:
            raise OcrIdentityError("OCR admitted languages must match the 12.2 pin")
        if self.admitted_psm != ADMITTED_PSM:
            raise OcrIdentityError("OCR admitted PSM must match the 12.2 pin")
        if self.preprocess_ids != PREPROCESS_IDS:
            raise OcrIdentityError("OCR preprocess identifiers must match the v1 set")
        if self.limitations != LIMITATIONS:
            raise OcrIdentityError("OCR limitations must match the v1 set")
        if self.executable:
            raise OcrIdentityError(
                "OCR recovery is not executable as the default parse path"
            )
        if not self.extra_declared:
            raise OcrIdentityError("ocr extra must be declared as an empty extra")
        return self


class OcrPreprocess(_StrictModel):
    parameters: dict[str, str | int | float | bool]
    transform_id: str

    @model_validator(mode="after")
    def _closed(self) -> OcrPreprocess:
        if self.transform_id not in PREPROCESS_IDS:
            raise OcrIdentityError(
                f"OCR preprocess {self.transform_id!r} is not in the v1 set"
            )
        keys = list(self.parameters)
        if keys != sorted(keys):
            raise OcrIdentityError("OCR preprocess parameters must be sorted")
        return self


class OcrBoundingBox(_StrictModel):
    page_index: int
    unit: Literal["pdf-point", "raster-pixel"]
    x0: float
    x1: float
    y0: float
    y1: float

    @model_validator(mode="after")
    def _closed(self) -> OcrBoundingBox:
        if self.page_index < 1:
            raise OcrIdentityError("OCR bounding box page_index is 1-based")
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise OcrIdentityError("OCR bounding box is backward")
        return self


class OcrConfidence(_StrictModel):
    mean: float
    minimum: float
    word_count: int

    @model_validator(mode="after")
    def _closed(self) -> OcrConfidence:
        for name in ("mean", "minimum"):
            value = getattr(self, name)
            if value < 0.0 or value > 100.0:
                raise OcrIdentityError(f"OCR confidence {name} must be in 0..100")
        if self.minimum > self.mean:
            raise OcrIdentityError("OCR minimum confidence cannot exceed mean")
        if self.word_count < 0:
            raise OcrIdentityError("OCR word_count cannot be negative")
        return self


class OcrPageIdentity(_StrictModel):
    boxes: tuple[OcrBoundingBox, ...]
    confidence: OcrConfidence | None
    engine_id: Literal["tesseract"]
    engine_version: str
    page_index: int
    preprocess: tuple[OcrPreprocess, ...]
    psm: int
    raster_sha256: str
    recovery_path: Literal["ocr"]
    schema_id: str
    source_sha256: str
    tessdata_language: str
    tessdata_sha256: str

    @field_validator("boxes", "preprocess", mode="before")
    @classmethod
    def _tuple_seq(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("raster_sha256", "source_sha256", "tessdata_sha256")
    @classmethod
    def _digest(cls, value: str) -> str:
        try:
            return validate_sha256(value)
        except ValueError as exc:
            raise OcrIdentityError(str(exc)) from exc

    @model_validator(mode="after")
    def _closed(self) -> OcrPageIdentity:
        if self.schema_id != OCR_RECOVERY_IDENTITY_SCHEMA_ID:
            raise OcrIdentityError("OCR page identity schema_id is invalid")
        if self.page_index < 1:
            raise OcrIdentityError("OCR page_index is 1-based")
        if self.tessdata_language not in ADMITTED_LANGUAGES:
            raise OcrIdentityError(
                f"OCR language {self.tessdata_language!r} is not in the 12.2 pin"
            )
        if self.psm not in ADMITTED_PSM:
            raise OcrIdentityError(f"OCR PSM {self.psm} is not in the 12.2 pin")
        if not self.engine_version.strip():
            raise OcrIdentityError("OCR engine_version must be nonempty")
        return self


@lru_cache(maxsize=1)
def admitted_ocr_engine() -> OcrEnginePin:
    """Return the Tesseract 5 pin. Recovery is not executable."""
    return OcrEnginePin(
        admitted_languages=ADMITTED_LANGUAGES,
        admitted_psm=ADMITTED_PSM,
        contract_id=OCR_RECOVERY_IDENTITY_CONTRACT_ID,
        contract_version=OCR_RECOVERY_IDENTITY_CONTRACT_VERSION,
        engine_family="tesseract-5",
        engine_id="tesseract",
        executable=False,
        extra="ocr",
        extra_declared=True,
        license="Apache-2.0",
        limitations=LIMITATIONS,
        measured_version="5.5.3",
        min_version="5.0.0",
        preprocess_ids=PREPROCESS_IDS,
        schema_id=OCR_RECOVERY_IDENTITY_SCHEMA_ID,
    )


def require_ocr_recovery_not_executable() -> None:
    """Fail closed if a caller tries to treat OCR as a parser path."""
    pin = admitted_ocr_engine()
    if pin.executable:
        return
    raise OcrIdentityError(
        "OCR recovery is not executable as the default parse path. "
        "Parse still refuses image-only PDF as ocr-unsupported."
    )


def build_ocr_page_identity(
    *,
    source_sha256: str,
    page_index: int,
    raster_sha256: str,
    tessdata_language: str,
    tessdata_sha256: str,
    engine_version: str,
    psm: int = 6,
    preprocess: tuple[OcrPreprocess, ...] = (),
    boxes: tuple[OcrBoundingBox, ...] = (),
    confidence: OcrConfidence | None = None,
    recovery_path: Literal["ocr"] = "ocr",
) -> OcrPageIdentity:
    """Validate one page-recovery identity. Does not run Tesseract."""
    return OcrPageIdentity(
        boxes=boxes,
        confidence=confidence,
        engine_id="tesseract",
        engine_version=engine_version,
        page_index=page_index,
        preprocess=preprocess,
        psm=psm,
        raster_sha256=raster_sha256,
        recovery_path=recovery_path,
        schema_id=OCR_RECOVERY_IDENTITY_SCHEMA_ID,
        source_sha256=source_sha256,
        tessdata_language=tessdata_language,
        tessdata_sha256=tessdata_sha256,
    )


def ocr_page_identity_id(identity: OcrPageIdentity) -> str:
    """Content-address the page identity without recovered text."""
    return derive_id(
        "ocr-page",
        identity.model_dump(mode="json"),
        version=OCR_RECOVERY_IDENTITY_CONTRACT_VERSION,
    )
