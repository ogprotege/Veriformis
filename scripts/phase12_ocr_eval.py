#!/usr/bin/env python3
"""Build the Phase 12.2 OCR evaluation corpus and measure Tesseract on it.

The corpus is original Veriformis fixture text rendered through PDF standard
Helvetica and pypdfium2. It does not download models, import OCR libraries,
or change taxonomy state. Tesseract, if present on PATH, is invoked as a
subprocess for the local measurement recorded in the packet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import struct
import subprocess
import time
import zlib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "phase12" / "ocr-eval"
PACKET = ROOT / "dev" / "active" / "independent-product" / "phase-12-optional-ocr"
RESULTS_PATH = PACKET / "evaluation-results.json"
MANIFEST_PATH = CORPUS / "manifest.json"

SCALE = 200.0 / 72.0  # 200 dpi
PAGE_W = 612.0
PAGE_H = 220.0
TABLE_H = 280.0

CASES: list[dict[str, Any]] = [
    {
        "id": "clean-en",
        "language": "eng",
        "condition": "clean-print",
        "expected": "Veriformis recovers source text. This page is digitally born.",
        "lines": [(72.0, 140.0, 18, "Veriformis recovers source text. This page is digitally born.")],
        "height": PAGE_H,
        "rotation": 0,
        "degrade": False,
    },
    {
        "id": "fra-accents",
        "language": "fra",
        "condition": "language-french",
        "expected": "Caf\u00e9 \u00e9l\u00e8ve: la page fran\u00e7aise reste locale.",
        "lines": [(72.0, 140.0, 18, "Caf\u00e9 \u00e9l\u00e8ve: la page fran\u00e7aise reste locale.")],
        "height": PAGE_H,
        "rotation": 0,
        "degrade": False,
    },
    {
        "id": "lat-print",
        "language": "lat",
        "condition": "language-latin",
        "expected": "Non est summaria haec pagina.",
        "lines": [(72.0, 140.0, 18, "Non est summaria haec pagina.")],
        "height": PAGE_H,
        "rotation": 0,
        "degrade": False,
    },
    {
        "id": "rotated-en",
        "language": "eng",
        "condition": "rotation-90",
        "expected": "Veriformis recovers source text. This page is digitally born.",
        "lines": [(72.0, 140.0, 18, "Veriformis recovers source text. This page is digitally born.")],
        "height": PAGE_H,
        "rotation": 90,
        "degrade": False,
    },
    {
        "id": "degraded-en",
        "language": "eng",
        "condition": "degraded-noise",
        "expected": "Veriformis recovers source text. This page is digitally born.",
        "lines": [(72.0, 140.0, 18, "Veriformis recovers source text. This page is digitally born.")],
        "height": PAGE_H,
        "rotation": 0,
        "degrade": True,
    },
    {
        "id": "table-en",
        "language": "eng",
        "condition": "table",
        "expected": "Item Count Note alpha 12 keep beta 3 skip",
        "lines": [
            (72.0, 200.0, 16, "Item     Count    Note"),
            (72.0, 170.0, 16, "alpha    12       keep"),
            (72.0, 140.0, 16, "beta     3        skip"),
        ],
        "height": TABLE_H,
        "rotation": 0,
        "degrade": False,
    },
]


def sha256_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _pdf_escape(text: str) -> bytes:
    raw = text.encode("latin-1")
    out = bytearray()
    for byte in raw:
        if byte in {0x28, 0x29, 0x5C}:
            out.extend(b"\\" + bytes([byte]))
        elif byte < 32 or byte > 126:
            out.extend(f"\\{byte:03o}".encode("ascii"))
        else:
            out.append(byte)
    return b"(" + bytes(out) + b")"


def write_text_pdf(lines: list[tuple[float, float, int, str]], *, height: float) -> bytes:
    content_parts = [b"BT /F1 %d Tf %.2f %.2f Td %s Tj ET" % (size, x, y, _pdf_escape(text)) for x, y, size, text in lines]
    stream = b"\n".join(content_parts)
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
            % (PAGE_W, height)
        ),
        b"4 0 obj << /Length %d >> stream\n" % len(stream) + stream + b"\nendstream\nendobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> endobj\n",
    ]
    return _finalize_pdf(objects)


def write_mixed_pdf() -> bytes:
    text_stream = b"BT /F1 18 Tf 72.00 140.00 Td %s Tj ET" % _pdf_escape(
        "Digital text on page one."
    )
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
            % (PAGE_W, PAGE_H)
        ),
        b"4 0 obj << /Length %d >> stream\n" % len(text_stream)
        + text_stream
        + b"\nendstream\nendobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> endobj\n",
        (
            b"6 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
            b"/Resources << >> >> endobj\n" % (PAGE_W, PAGE_H)
        ),
    ]
    return _finalize_pdf(objects)


def write_image_pdf(width: int, height: int, rgb: bytes) -> bytes:
    compressed = zlib.compress(rgb, 9)
    image = (
        b"4 0 obj << /Type /XObject /Subtype /Image /Width %d /Height %d "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode "
        b"/Length %d >> stream\n" % (width, height, len(compressed))
        + compressed
        + b"\nendstream\nendobj\n"
    )
    content = b"q %d 0 0 %d 0 0 cm /Im0 Do Q" % (width, height)
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
            b"/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >> endobj\n"
            % (width, height)
        ),
        image,
        b"5 0 obj << /Length %d >> stream\n" % len(content) + content + b"\nendstream\nendobj\n",
    ]
    return _finalize_pdf(objects)


def _finalize_pdf(objects: list[bytes]) -> bytes:
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    body = bytearray()
    position = len(header)
    for obj in objects:
        offsets.append(position)
        body.extend(obj)
        position += len(obj)
    xref_pos = position
    xref = [b"xref\n0 %d\n" % (len(objects) + 1), b"0000000000 65535 f \n"]
    xref.extend(b"%010d 00000 n \n" % offset for offset in offsets[1:])
    trailer = b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_pos,
    )
    return header + bytes(body) + b"".join(xref) + trailer


def write_png(width: int, height: int, rgb: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b"".join(b"\x00" + rgb[y * width * 3 : (y + 1) * width * 3] for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def bitmap_to_rgb(bitmap) -> tuple[int, int, bytes]:
    width, height, stride, channels = bitmap.width, bitmap.height, bitmap.stride, bitmap.n_channels
    raw = bytes(bitmap.buffer)
    rows = bytearray()
    for y in range(height):
        row = raw[y * stride : y * stride + width * channels]
        for x in range(width):
            base = x * channels
            rows.extend((row[base + 2], row[base + 1], row[base]))
    return width, height, bytes(rows)


def degrade_rgb(rgb: bytes, width: int, height: int) -> bytes:
    out = bytearray(rgb)
    seed = hashlib.sha256(b"veriformis-phase12-degrade-v1").digest()
    needed = width * height
    stream = bytearray()
    counter = 0
    while len(stream) < needed * 2:
        stream.extend(hashlib.sha256(seed + counter.to_bytes(4, "big")).digest())
        counter += 1
    for i in range(needed):
        if stream[i] < 4:  # ~1.6% of pixels
            offset = i * 3
            noise = stream[needed + i]
            out[offset] = noise
            out[offset + 1] = 255 - noise
            out[offset + 2] = noise ^ 0xA5
    return bytes(out)


def render_pdf(payload: bytes, *, rotation: int = 0) -> tuple[int, int, bytes]:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(payload)
    try:
        page = document[0]
        bitmap = page.render(scale=SCALE, rotation=rotation)
        try:
            return bitmap_to_rgb(bitmap)
        finally:
            bitmap.close()
            page.close()
    finally:
        document.close()


def build_corpus() -> dict[str, Any]:
    CORPUS.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    expected: dict[str, Any] = {}

    def store(name: str, payload: bytes) -> None:
        path = CORPUS / name
        path.write_bytes(payload)
        files[name] = sha256_digest(payload)

    for case in CASES:
        text_pdf = write_text_pdf(case["lines"], height=case["height"])
        store(f"{case['id']}.text.pdf", text_pdf)
        width, height, rgb = render_pdf(text_pdf, rotation=case["rotation"])
        if case["degrade"]:
            rgb = degrade_rgb(rgb, width, height)
        store(f"{case['id']}.png", write_png(width, height, rgb))
        store(f"{case['id']}.image.pdf", write_image_pdf(width, height, rgb))
        expected[case["id"]] = {
            "language": case["language"],
            "condition": case["condition"],
            "expected": case["expected"],
            "width": width,
            "height": height,
        }

    mixed = write_mixed_pdf()
    store("mixed-en.text.pdf", mixed)
    expected["mixed-en"] = {
        "language": "eng",
        "condition": "mixed-text-and-empty-page",
        "expected": "Digital text on page one.",
    }

    manifest = {
        "schema": "veriformis.phase12-ocr-eval-corpus/v1",
        "license": "Original Veriformis fixtures. No third-party page scans.",
        "renderer": "pypdfium2",
        "scale": SCALE,
        "files": files,
        "cases": expected,
        "excluded": {
            "handwriting": "Roadmap non-goal; no handwriting sample is retained.",
            "cjk": "PDF standard-14 Helvetica cannot rasterize CJK; language-pack facts are desk-evaluated.",
            "cloud-ocr": "Roadmap non-goal.",
        },
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def normalize_ocr(text: str) -> str:
    collapsed = " ".join(text.replace("\u00a0", " ").split())
    translated = (
        collapsed.replace("\u00e9", "e")
        .replace("\u00e8", "e")
        .replace("\u00ea", "e")
        .replace("\u00e7", "c")
        .replace("\u00c9", "E")
    )
    return translated


def levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, lch in enumerate(left, start=1):
        current = [i]
        for j, rch in enumerate(right, start=1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (lch != rch)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def character_error_rate(expected: str, actual: str) -> float:
    if not expected:
        return 0.0 if not actual else 1.0
    return levenshtein(expected, actual) / len(expected)


def tesseract_version() -> str | None:
    binary = shutil.which("tesseract")
    if binary is None:
        return None
    result = subprocess.run([binary, "--version"], capture_output=True, text=True, check=False)
    line = (result.stderr or result.stdout).splitlines()
    return line[0].strip() if line else binary


def measure_tesseract(manifest: dict[str, Any]) -> dict[str, Any]:
    binary = shutil.which("tesseract")
    if binary is None:
        return {"available": False, "reason": "tesseract not on PATH"}

    measurements: list[dict[str, Any]] = []
    for case in CASES:
        image = CORPUS / f"{case['id']}.png"
        lang = case["language"]
        tessdata = Path("/opt/homebrew/share/tessdata") / f"{lang}.traineddata"
        if not tessdata.is_file() and lang != "eng":
            lang = "eng"
        started = time.perf_counter()
        timed = subprocess.run(
            ["/usr/bin/time", "-l", binary, str(image), "stdout", "-l", lang, "--psm", "6"],
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed = time.perf_counter() - started
        if timed.returncode != 0:
            # time -l may not exist; fall back
            plain = subprocess.run(
                [binary, str(image), "stdout", "-l", lang, "--psm", "6"],
                capture_output=True,
                text=True,
                check=False,
            )
            hyp = plain.stdout
            rss = None
            returncode = plain.returncode
            timed_err = plain.stderr
        else:
            hyp = timed.stdout
            rss = _parse_rss(timed.stderr)
            returncode = 0
            timed_err = timed.stderr
        expected = case["expected"]
        actual = normalize_ocr(hyp)
        expected_normalized = normalize_ocr(expected)
        measurements.append(
            {
                "id": case["id"],
                "condition": case["condition"],
                "language_requested": case["language"],
                "language_used": lang,
                "expected": expected,
                "hypothesis": actual,
                "raw_hypothesis": hyp.strip(),
                "character_error_rate": round(
                    character_error_rate(expected_normalized, actual), 4
                ),
                "seconds": round(elapsed, 4),
                "max_rss_bytes": rss,
                "returncode": returncode,
                "stderr_tail": "\n".join(timed_err.splitlines()[-6:]),
            }
        )
    rotated = CORPUS / "rotated-en.png"
    osd = subprocess.run(
        [binary, str(rotated), "stdout", "--psm", "0", "-l", "osd"],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "available": True,
        "binary": binary,
        "version": tesseract_version(),
        "tessdata_eng_bytes": _traineddata_size("eng"),
        "tessdata_fra_bytes": _traineddata_size("fra"),
        "tessdata_lat_bytes": _traineddata_size("lat"),
        "osd_probe_rotated_en": {
            "returncode": osd.returncode,
            "stdout": osd.stdout.strip(),
            "stderr_tail": "\n".join(osd.stderr.splitlines()[-8:]),
        },
        "measurements": measurements,
    }


def _traineddata_size(lang: str) -> int | None:
    for candidate in (
        Path("/opt/homebrew/share/tessdata") / f"{lang}.traineddata",
        Path("/opt/homebrew/Cellar/tesseract/5.5.3/share/tessdata") / f"{lang}.traineddata",
    ):
        if candidate.is_file():
            return candidate.resolve().stat().st_size
    return None


def _parse_rss(stderr: str) -> int | None:
    for line in stderr.splitlines():
        if "maximum resident set size" in line.lower():
            digits = "".join(ch for ch in line if ch.isdigit())
            return int(digits) if digits else None
    return None


def host_facts() -> dict[str, Any]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "mac_ver": platform.mac_ver()[0],
        "cwd_repo": str(ROOT),
    }


def write_results(manifest: dict[str, Any], tesseract: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "veriformis.phase12-ocr-eval-results/v1",
        "recorded_on": "2026-08-25",
        "host": host_facts(),
        "corpus_manifest_digest": sha256_digest(MANIFEST_PATH.read_bytes()),
        "tesseract": tesseract,
        "network": {
            "evaluation_script_opens_sockets": False,
            "cloud_ocr": "excluded",
        },
        "note": (
            "This measurement is evidence for the operator ADR. It does not "
            "admit ocr-image or add an ocr extra."
        ),
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "measure", "all"))
    args = parser.parse_args(argv)
    if args.command in {"build", "all"}:
        manifest = build_corpus()
        print(f"wrote {len(manifest['files'])} corpus files under {CORPUS}")
    else:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if args.command in {"measure", "all"}:
        tesseract = measure_tesseract(manifest)
        write_results(manifest, tesseract)
        print(f"wrote {RESULTS_PATH}")
        if tesseract.get("available"):
            for item in tesseract["measurements"]:
                print(
                    f"{item['id']}: CER={item['character_error_rate']:.4f} "
                    f"t={item['seconds']:.3f}s rss={item['max_rss_bytes']}"
                )
        else:
            print("tesseract unavailable; desk evaluation only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
