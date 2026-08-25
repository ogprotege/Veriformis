"""Digital, OCR, and merged recovery. Digital text is never replaced."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, model_validator

from veriformis.errors import OcrIdentityError
from veriformis.ocr.identity import OcrPageIdentity


PageKind = Literal["digital", "ocr"]
DocumentRecoveryPath = Literal["digital", "ocr", "merged"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class OcrPageRequest(_StrictModel):
    digital_text: str
    page_index: int
    source_sha256: str

    @model_validator(mode="after")
    def _no_digital(self) -> OcrPageRequest:
        if self.digital_text.strip():
            raise OcrIdentityError(
                "OCR must not replace recoverable digital text"
            )
        if self.page_index < 1:
            raise OcrIdentityError("OCR page_index is 1-based")
        return self


class OcrPageResult(_StrictModel):
    identity: OcrPageIdentity
    text: str

    @model_validator(mode="after")
    def _path(self) -> OcrPageResult:
        if self.identity.recovery_path != "ocr":
            raise OcrIdentityError("OCR page result identity must be recovery_path=ocr")
        return self


class PdfPageRecovery(_StrictModel):
    ocr_identity: OcrPageIdentity | None
    page_index: int
    recovery_path: PageKind
    text: str

    @model_validator(mode="after")
    def _closed(self) -> PdfPageRecovery:
        if self.page_index < 1:
            raise OcrIdentityError("PDF page_index is 1-based")
        if self.recovery_path == "digital":
            if not self.text.strip():
                raise OcrIdentityError("digital recovery requires extracted text")
            if self.ocr_identity is not None:
                raise OcrIdentityError("digital recovery cannot carry an OCR identity")
        if self.recovery_path == "ocr" and self.ocr_identity is not None:
            if self.ocr_identity.page_index != self.page_index:
                raise OcrIdentityError("OCR identity page_index does not match the page")
        return self


class PdfDocumentRecovery(_StrictModel):
    pages: tuple[PdfPageRecovery, ...]
    recovery_path: DocumentRecoveryPath

    @model_validator(mode="after")
    def _closed(self) -> PdfDocumentRecovery:
        if not self.pages:
            raise OcrIdentityError("PDF recovery requires at least one page")
        expected = document_recovery_path(tuple(page.recovery_path for page in self.pages))
        if self.recovery_path != expected:
            raise OcrIdentityError("document recovery_path does not match its pages")
        indexes = [page.page_index for page in self.pages]
        if indexes != list(range(1, len(self.pages) + 1)):
            raise OcrIdentityError("PDF recovery pages must be contiguous and 1-based")
        return self


@runtime_checkable
class OcrProvider(Protocol):
    def recover_page(self, request: OcrPageRequest) -> OcrPageResult:
        """Recover one empty-text page. Must not be called with digital text."""


def page_kind(text: str) -> PageKind:
    """Classify one page from its digital text layer."""
    return "digital" if text.strip() else "ocr"


def document_recovery_path(kinds: tuple[PageKind, ...]) -> DocumentRecoveryPath:
    """Document path is digital, ocr, or merged from the page kinds."""
    present = frozenset(kinds)
    if present == frozenset({"digital"}):
        return "digital"
    if present == frozenset({"ocr"}):
        return "ocr"
    if present == frozenset({"digital", "ocr"}):
        return "merged"
    raise OcrIdentityError("recovery path kinds are empty or invalid")


def recover_pages(
    page_texts: tuple[str, ...],
    *,
    source_sha256: str,
    provider: OcrProvider | None = None,
) -> PdfDocumentRecovery:
    """Bind each page to digital or OCR recovery. Never OCR a digital page."""
    if not page_texts:
        raise OcrIdentityError("PDF recovery requires at least one page")
    pages: list[PdfPageRecovery] = []
    for index, text in enumerate(page_texts, start=1):
        kind = page_kind(text)
        if kind == "digital":
            pages.append(
                PdfPageRecovery(
                    ocr_identity=None,
                    page_index=index,
                    recovery_path="digital",
                    text=text,
                )
            )
            continue
        if provider is None:
            pages.append(
                PdfPageRecovery(
                    ocr_identity=None,
                    page_index=index,
                    recovery_path="ocr",
                    text="",
                )
            )
            continue
        request = OcrPageRequest(
            digital_text=text,
            page_index=index,
            source_sha256=source_sha256,
        )
        result = provider.recover_page(request)
        if result.identity.page_index != index:
            raise OcrIdentityError("OCR provider returned a different page_index")
        pages.append(
            PdfPageRecovery(
                ocr_identity=result.identity,
                page_index=index,
                recovery_path="ocr",
                text=result.text,
            )
        )
    kinds = tuple(page.recovery_path for page in pages)
    return PdfDocumentRecovery(
        pages=tuple(pages),
        recovery_path=document_recovery_path(kinds),
    )
