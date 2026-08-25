"""Tesseract 5 subprocess provider. No Python OCR wheel; extra `ocr` is empty."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from veriformis.errors import OcrIdentityError
from veriformis.identity import sha256_digest
from veriformis.ocr.identity import ADMITTED_LANGUAGES, build_ocr_page_identity
from veriformis.ocr.recovery import OcrPageRequest, OcrPageResult


def tesseract_binary() -> str | None:
    return shutil.which("tesseract")


def tessdata_path(language: str) -> Path | None:
    names = [f"{language}.traineddata"]
    roots = [
        Path("/opt/homebrew/share/tessdata"),
        Path("/usr/share/tesseract-ocr/5/tessdata"),
        Path("/usr/share/tessdata"),
    ]
    prefix = os.environ.get("TESSDATA_PREFIX")
    if prefix:
        roots.insert(0, Path(prefix))
    for root in roots:
        candidate = root / names[0]
        if candidate.is_file():
            return candidate.resolve()
    return None


class TesseractProvider:
    """Recover one empty-text page through a local Tesseract 5 binary."""

    def __init__(self, language: str = "eng") -> None:
        if language not in ADMITTED_LANGUAGES:
            raise OcrIdentityError(
                f"OCR language {language!r} is not in the 12.2 pin"
            )
        self.language = language

    def recover_page(self, request: OcrPageRequest) -> OcrPageResult:
        binary = tesseract_binary()
        if binary is None:
            raise OcrIdentityError("tesseract is not on PATH")
        trained = tessdata_path(self.language)
        if trained is None:
            raise OcrIdentityError(
                f"tessdata for {self.language} is missing"
            )
        if not request.raster_png:
            raise OcrIdentityError("Tesseract recovery requires a page raster")
        version_proc = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        version_line = (version_proc.stderr or version_proc.stdout).splitlines()
        engine_version = version_line[0].replace("tesseract ", "").strip() if version_line else "unknown"
        with tempfile.TemporaryDirectory(prefix="veriformis-ocr-") as tmp:
            image = Path(tmp) / "page.png"
            image.write_bytes(request.raster_png)
            recognized = subprocess.run(
                [binary, str(image), "stdout", "-l", self.language, "--psm", "6"],
                capture_output=True,
                check=False,
            )
            if recognized.returncode != 0:
                raise OcrIdentityError("tesseract recovery failed")
            text = recognized.stdout.decode("utf-8", errors="replace").strip()
        identity = build_ocr_page_identity(
            source_sha256=request.source_sha256,
            page_index=request.page_index,
            raster_sha256=sha256_digest(request.raster_png),
            tessdata_language=self.language,
            tessdata_sha256=sha256_digest(trained.read_bytes()),
            engine_version=engine_version,
        )
        return OcrPageResult(identity=identity, text=text)
