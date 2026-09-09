"""Post-20 defect D-12: HTML block folding is separated and diagnosed.

``itertext()`` glued ``line one<br>line two`` into ``line oneline two`` and
``<li><p>x</p><p>y</p></li>`` into ``xy`` with no diagnostic; tables, lists,
and ``<pre>`` were flattened silently; omitted subtrees and content outside
the selected ``<main>`` were always labelled presentation loss.
"""

from __future__ import annotations

from pathlib import Path

from veriformis.parsers.html import PARSER_VERSION, parse_html_file


def _parse(tmp_path: Path, raw: bytes):
    path = tmp_path / "page.html"
    path.write_bytes(raw)
    return parse_html_file(path, logical_path=path.name)


def _by_code(result) -> dict[str, object]:
    return {item.code: item for item in result.diagnostics.diagnostics}


def test_parser_pin_advanced() -> None:
    assert PARSER_VERSION == "1.2.0"


def test_br_becomes_a_line_break_and_is_diagnosed(tmp_path: Path) -> None:
    result = _parse(tmp_path, b"<html><body><p>line one<br>line two<br/>line three</p></body></html>")
    assert result.source.extracted_text == "line one\nline two\nline three"
    folded = _by_code(result)["html.line-break-normalized"]
    assert folded.details == {"count": 2}
    assert folded.disposition == "normalized"


def test_nested_blocks_inside_a_list_item_do_not_glue_words(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        b"<html><body><ul><li><p>first</p><p>second</p></li><li>third</li></ul></body></html>",
    )
    assert result.source.extracted_text == "first\nsecond\n\nthird"
    codes = _by_code(result)
    assert "html.line-break-normalized" in codes
    assert codes["html.list-flattened"].loss_kind == "structure"
    assert codes["html.list-flattened"].details == {"count": 1}


def test_pre_preserves_internal_whitespace(tmp_path: Path) -> None:
    result = _parse(tmp_path, b"<html><body><pre>\ndef f():\n    return  1\n</pre></body></html>")
    assert result.source.extracted_text == "def f():\n    return  1"


def test_table_flattening_is_diagnosed_as_structure_loss(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        b"<html><body><table><tr><th>h1</th><th>h2</th></tr><tr><td>a</td><td>b</td></tr></table></body></html>",
    )
    assert result.source.extracted_text == "h1\n\nh2\n\na\n\nb"
    flattened = _by_code(result)["html.table-flattened"]
    assert flattened.severity == "warning"
    assert flattened.loss_kind == "structure"
    assert flattened.details == {"count": 1}


def test_omitted_subtree_with_visible_text_is_text_loss(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        b"<html><body><p>Main</p><noscript>Enable scripts to see the chart.</noscript>"
        b"<script>var x = 1;</script></body></html>",
    )
    assert result.source.extracted_text == "Main"
    omitted = _by_code(result)["html.non-content-tags-omitted"]
    assert omitted.loss_kind == "text"
    assert omitted.severity == "warning"
    assert omitted.details["tags_with_visible_text"] == ["noscript"]
    assert "script" in omitted.details["tags"]


def test_script_only_omission_stays_presentation_loss(tmp_path: Path) -> None:
    result = _parse(tmp_path, b"<html><body><style>p{}</style><p>Main</p></body></html>")
    omitted = _by_code(result)["html.non-content-tags-omitted"]
    assert omitted.loss_kind == "presentation"
    assert omitted.details["tags_with_visible_text"] == []


def test_main_selection_that_drops_text_is_text_loss(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        b"<html><body><nav>Site navigation</nav><main><p>Body</p></main><footer>Legal</footer></body></html>",
    )
    assert result.source.extracted_text == "Body"
    selected = _by_code(result)["html.main-content-selected"]
    assert selected.loss_kind == "text"
    assert selected.disposition == "omitted"
    assert selected.details == {"container": "main", "omitted_text": True}


def test_main_selection_without_outside_text_stays_presentation(tmp_path: Path) -> None:
    result = _parse(tmp_path, b"<html><body><main><p>Body</p></main></body></html>")
    selected = _by_code(result)["html.main-content-selected"]
    assert selected.loss_kind == "presentation"
    assert selected.details == {"container": "main", "omitted_text": False}


def test_plain_paragraphs_gain_no_new_diagnostics(tmp_path: Path) -> None:
    result = _parse(tmp_path, b"<html><body><h1>Title</h1><p>One.</p><p>Two.</p></body></html>")
    assert result.source.extracted_text == "Title\n\nOne.\n\nTwo."
    assert result.diagnostics.diagnostics == ()
