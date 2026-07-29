from copy import deepcopy
import json

import pytest

from veriformis.errors import RuleError
from veriformis.identity import derive_id
from veriformis.ir import Code, CodeBlock, Document, Math, Paragraph, Text
from veriformis.rules.cleaning import plan_cleaning
from veriformis.rules.engine import (
    RegexRule,
    apply_rules,
    clean_document,
    transform_record_from_dict,
    transform_record_to_dict,
)
from veriformis.rules.library import default_rules


SOURCE_ID = derive_id("src", {"test": "rule-engine"})


def test_apply_rules_logs_edits_and_runs_sequentially():
    text, records, warnings = apply_rules(
        "hello   world",
        [RegexRule("spaces", r"\s+", " "), RegexRule("shout", r"world", "WORLD")],
        source_id=SOURCE_ID,
    )
    assert text == "hello WORLD"
    assert [r.rule for r in records] == ["spaces", "shout"]
    assert records[0].edits == 1
    assert all(record.id.startswith("trn-v1-") for record in records)
    assert all(record.source_id == SOURCE_ID for record in records)
    assert records[0].operation_ids[0].startswith("op-v1-")
    assert warnings == []


def test_safety_valve_skips_destructive_rule():
    text = "keep this sentence. " * 10
    out, records, warnings = apply_rules(
        text,
        [RegexRule("nuke", r"\w+", "")],
        source_id=SOURCE_ID,
        max_remove_frac=0.3,
    )
    assert out == text  # rule skipped
    assert warnings and "nuke" in warnings[0]
    assert records[0].warned is True


def test_transform_record_v1_roundtrips_and_recomputes_identity():
    _, records, _ = apply_rules(
        "alpha  beta",
        [RegexRule("spaces", r" +", " ")],
        source_id=SOURCE_ID,
    )
    persisted = json.loads(json.dumps(transform_record_to_dict(records[0])))

    assert transform_record_from_dict(persisted) == records[0]


def test_transform_identity_binds_exact_regex_normalization():
    _, composed, _ = apply_rules(
        "unchanged text",
        [RegexRule("accent", "é", "x", flags=0)],
        source_id=SOURCE_ID,
    )
    _, decomposed, _ = apply_rules(
        "unchanged text",
        [RegexRule("accent", "e\u0301", "x", flags=0)],
        source_id=SOURCE_ID,
    )

    assert composed[0].input_sha256 == decomposed[0].input_sha256
    assert composed[0].output_sha256 == decomposed[0].output_sha256
    assert composed[0].id != decomposed[0].id


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("id", "trn-v1-" + "0" * 64, "identity mismatch"),
        ("source_id", derive_id("src", {"other": True}), "identity mismatch"),
        ("input_sha256", "f" * 64, "identity mismatch"),
        ("edits", -1, "non-negative"),
        ("bytes_removed", True, "non-negative"),
        ("operation_ids", [], "edit count"),
    ],
)
def test_transform_record_v1_rejects_tampering(field, value, message):
    _, records, _ = apply_rules(
        "alpha  beta",
        [RegexRule("spaces", r" +", " ")],
        source_id=SOURCE_ID,
    )
    persisted = deepcopy(transform_record_to_dict(records[0]))
    persisted[field] = value

    with pytest.raises(RuleError, match=message):
        transform_record_from_dict(persisted)


def test_transform_record_v1_rejects_unknown_fields():
    _, records, _ = apply_rules(
        "alpha  beta",
        [RegexRule("spaces", r" +", " ")],
        source_id=SOURCE_ID,
    )
    persisted = transform_record_to_dict(records[0])
    persisted["unexpected"] = True

    with pytest.raises(RuleError, match="keys do not match"):
        transform_record_from_dict(persisted)


def test_clean_document_edits_blocks_and_preserves_provenance():
    doc = Document(
        children=[
            Paragraph(children=[Text("alpha  beta")]),
            Paragraph(children=[Text("gamma")]),
        ],
        source_id=SOURCE_ID,
    )
    cleaned, records, _ = clean_document(doc, [RegexRule("spaces", r"\s+", " ")])
    from veriformis.ir import block_text

    assert block_text(cleaned.children[0]) == "alpha beta"
    assert block_text(cleaned.children[1]) == "gamma"
    assert records[0].block_index == 0
    assert all(r.block_index != 1 for r in records if r.edits > 0)


def test_default_cleaning_never_rewrites_code_or_math_literals():
    code = "def f():\n    x =  1\n\treturn x"
    inline_code = "value  with  spaces"
    math = r"x  +  y"
    doc = Document(
        children=[
            CodeBlock(text=code, language="python", block_index=0),
            Paragraph(
                children=[
                    Text("prose   before "),
                    Code(inline_code),
                    Text(" after   prose"),
                ],
                block_index=1,
            ),
            Math(source=math, display=True, block_index=2),
        ],
        source_id=SOURCE_ID,
    )

    preview = plan_cleaning(doc, default_rules())

    assert preview.document.children[0].text == code
    paragraph = preview.document.children[1]
    assert paragraph.children[1].value == inline_code
    assert preview.document.children[2].source == math
    assert any("structural separator" in warning for warning in preview.warnings)
    assert all(
        operation.path[-1] not in {"text", "source"}
        for operation in preview.plan.operations
    )
