"""PDF page rasters for OCR. Uses pypdfium2 already in core."""

from __future__ import annotations

import struct
import zlib

import pypdfium2 as pdfium

from veriformis.errors import OcrIdentityError


SCALE = 200.0 / 72.0


def _write_png(width: int, height: int, rgb: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b"".join(b"\x00" + rgb[y * width * 3 : (y + 1) * width * 3] for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def render_pdf_page_png(payload: bytes, page_index: int) -> bytes:
    """Rasterize one 1-based PDF page to PNG bytes."""
    if page_index < 1:
        raise OcrIdentityError("PDF page_index is 1-based")
    try:
        document = pdfium.PdfDocument(payload)
    except Exception as exc:
        raise OcrIdentityError(f"PDF page could not be rasterized: {exc}") from exc
    try:
        if page_index > len(document):
            raise OcrIdentityError("PDF page_index exceeds page count")
        page = document[page_index - 1]
        bitmap = page.render(scale=SCALE)
        try:
            width, height, stride, channels = (
                bitmap.width,
                bitmap.height,
                bitmap.stride,
                bitmap.n_channels,
            )
            raw = bytes(bitmap.buffer)
            rows = bytearray()
            for y in range(height):
                row = raw[y * stride : y * stride + width * channels]
                for x in range(width):
                    base = x * channels
                    rows.extend((row[base + 2], row[base + 1], row[base]))
            return _write_png(width, height, bytes(rows))
        finally:
            bitmap.close()
            page.close()
    finally:
        document.close()
