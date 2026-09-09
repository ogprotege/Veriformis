"""Newline framing shared by every JSONL reader.

JSON Lines frames records on the single byte ``b"\\n"``. ``str.splitlines()``
also breaks on U+2028, U+2029, U+0085, U+000B, and U+000C, all of which are
legal raw inside a JSON string and which Veriformis's own ``ensure_ascii=False``
writers emit unescaped. Framing on those characters split valid records into
invalid fragments (post-20 defect D-03). Every reader frames through this
module so the rule cannot drift again.
"""

from __future__ import annotations

from collections.abc import Iterator


def frame_jsonl_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield ``(line_number, line)`` for every non-blank ``\\n``-framed line.

    Line numbers are one-based and count every ``\\n``-terminated line so they
    agree with editors and with ``line_count`` evidence. A trailing ``\\r`` is
    removed so CRLF files frame identically to LF files; a ``\\r`` anywhere else
    stays in the line and is refused by the JSON decoder as a control character.
    """
    for line_number, raw_line in enumerate(text.split("\n"), start=1):
        line = raw_line[:-1] if raw_line.endswith("\r") else raw_line
        if not line.strip():
            continue
        yield line_number, line
