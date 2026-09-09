"""Tesseract 5 subprocess provider. No Python OCR wheel; extra `ocr` is empty."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from veriformis.errors import OcrIdentityError
from veriformis.identity import sha256_digest
from veriformis.ocr.identity import (
    ADMITTED_LANGUAGES,
    OcrConfidence,
    build_ocr_page_identity,
)
from veriformis.ocr.recovery import OcrPageRequest, OcrPageResult


def parse_tsv_confidence(tsv_text: str) -> OcrConfidence | None:
    """Return word-level confidence from Tesseract TSV output, or None.

    Tesseract's TSV has a header row and one row per element; ``level`` 5 is
    a word and ``conf`` is its 0-100 confidence (``-1`` for non-word rows).
    Without at least one scored word there is no confidence to report, and
    the policy then requires review rather than accepting blindly
    (post-20 defect D-14).
    """
    lines = tsv_text.splitlines()
    if not lines:
        return None
    header = lines[0].split("\t")
    try:
        level_index = header.index("level")
        conf_index = header.index("conf")
        text_index = header.index("text")
    except ValueError:
        return None
    scores: list[float] = []
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) <= max(level_index, conf_index, text_index):
            continue
        if cells[level_index] != "5":
            continue
        try:
            score = float(cells[conf_index])
        except ValueError:
            continue
        if score < 0.0 or not cells[text_index].strip():
            continue
        scores.append(min(100.0, score))
    if not scores:
        return None
    return OcrConfidence(
        mean=sum(scores) / len(scores),
        minimum=min(scores),
        word_count=len(scores),
    )


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
            outbase = Path(tmp) / "page"
            # One recognition pass writes both the text and the word-level TSV
            # so the confidence describes exactly the emitted text.
            recognized = subprocess.run(
                [
                    binary,
                    str(image),
                    str(outbase),
                    "-l",
                    self.language,
                    "--psm",
                    "6",
                    "txt",
                    "tsv",
                ],
                capture_output=True,
                check=False,
            )
            text_path = outbase.with_suffix(".txt")
            tsv_path = outbase.with_suffix(".tsv")
            if recognized.returncode != 0 or not text_path.is_file():
                raise OcrIdentityError("tesseract recovery failed")
            text = text_path.read_bytes().decode("utf-8", errors="replace").strip()
            confidence = (
                parse_tsv_confidence(
                    tsv_path.read_bytes().decode("utf-8", errors="replace")
                )
                if tsv_path.is_file()
                else None
            )
        identity = build_ocr_page_identity(
            source_sha256=request.source_sha256,
            page_index=request.page_index,
            raster_sha256=sha256_digest(request.raster_png),
            tessdata_language=self.language,
            tessdata_sha256=sha256_digest(trained.read_bytes()),
            engine_version=engine_version,
            confidence=confidence,
        )
        return OcrPageResult(identity=identity, text=text)
