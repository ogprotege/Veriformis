from veriformis.ir import Document, Paragraph, Text
from veriformis.rules.engine import RegexRule, apply_rules, clean_document


def test_apply_rules_logs_edits_and_runs_sequentially():
    text, records, warnings = apply_rules(
        "hello   world",
        [RegexRule("spaces", r"\s+", " "), RegexRule("shout", r"world", "WORLD")],
    )
    assert text == "hello WORLD"
    assert [r.rule for r in records] == ["spaces", "shout"]
    assert records[0].edits == 1
    assert warnings == []


def test_safety_valve_skips_destructive_rule():
    text = "keep this sentence. " * 10
    out, records, warnings = apply_rules(
        text, [RegexRule("nuke", r"\w+", "")], max_remove_frac=0.3
    )
    assert out == text  # rule skipped
    assert warnings and "nuke" in warnings[0]
    assert records[0].warned is True


def test_clean_document_edits_blocks_and_preserves_provenance():
    doc = Document(children=[
        Paragraph(children=[Text("alpha  beta")]),
        Paragraph(children=[Text("gamma")]),
    ])
    cleaned, records, _ = clean_document(doc, [RegexRule("spaces", r"\s+", " ")])
    from veriformis.ir import block_text

    assert block_text(cleaned.children[0]) == "alpha beta"
    assert block_text(cleaned.children[1]) == "gamma"
    assert records[0].block_index == 0
    assert all(r.block_index != 1 for r in records if r.edits > 0)
