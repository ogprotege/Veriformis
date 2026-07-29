from dataclasses import replace
from copy import deepcopy

import pytest

from veriformis.errors import CleaningPlanError
from veriformis.ir import (
    Blockquote,
    Bold,
    Cell,
    Document,
    Footnote,
    ListBlock,
    ListItem,
    Paragraph,
    Table,
    Text,
    block_text,
)
from veriformis.rules.cleaning import (
    cleaning_plan_from_dict,
    cleaning_plan_to_dict,
    document_digest,
    plan_cleaning,
    replay_cleaning_plan,
)
from veriformis.rules.engine import RegexRule
from veriformis.rules.library import RULES, default_rules
from veriformis.identity import derive_id, sha256_digest
from veriformis.parsers.markdown import parse_md_file


def _paragraphs(*values: str, source_id: str = "src-test") -> Document:
    return Document(
        children=[Paragraph(children=[Text(value)], block_index=i) for i, value in enumerate(values)],
        source_id=source_id,
    )


def test_document_digest_binds_exact_unicode_normalization():
    assert document_digest(_paragraphs("Café")) != document_digest(
        _paragraphs("Cafe\u0301")
    )


def test_cleaning_plan_identity_binds_exact_regex_normalization():
    document = _paragraphs("unchanged text")
    composed = plan_cleaning(
        document,
        [RegexRule("accent", "é", "x", flags=0)],
    )
    decomposed = plan_cleaning(
        document,
        [RegexRule("accent", "e\u0301", "x", flags=0)],
    )

    assert composed.document == decomposed.document
    assert composed.plan.id != decomposed.plan.id
    assert composed.plan.rules[0].params != decomposed.plan.rules[0].params


def test_preview_returns_exact_plan_that_apply_commits():
    doc = _paragraphs("Alpha   beta", "42", "More text")

    preview = plan_cleaning(doc, default_rules())
    serialized = cleaning_plan_to_dict(preview.plan)
    loaded = cleaning_plan_from_dict(serialized)
    replayed = replay_cleaning_plan(doc, loaded)

    assert loaded.id == preview.plan.id
    assert replayed == preview.document
    assert block_text(replayed.children[0]) == "Alpha beta"
    assert [block_text(block) for block in replayed.children] == ["Alpha beta", "More text"]


def test_page_number_scope_matches_preview_and_apply():
    doc = _paragraphs("line", "42", "more")

    preview = plan_cleaning(doc, default_rules())
    applied = replay_cleaning_plan(doc, preview.plan)

    assert preview.document == applied
    assert [block_text(block) for block in applied.children] == ["line", "more"]
    assert any(record.rule == "page-numbers" for record in preview.records)


def test_repeated_headers_are_planned_across_blocks():
    body = "A sufficiently long body paragraph that keeps the removal below the safety limit."
    doc = _paragraphs(
        "CONFIDENTIAL",
        body,
        "CONFIDENTIAL",
        body + " Two.",
        "CONFIDENTIAL",
        body + " Three.",
    )

    preview = plan_cleaning(doc, [RULES["headers-footers"]()])

    assert [block_text(block) for block in preview.document.children] == [
        body,
        body + " Two.",
        body + " Three.",
    ]
    assert len([op for op in preview.plan.operations if op.kind == "remove-block"]) == 3


def test_cleaning_preserves_rich_block_structure():
    rich_list = ListBlock(
        ordered=False,
        items=[
            ListItem(
                children=[
                    Paragraph(
                        children=[Text("Alpha   "), Bold(children=[Text("bold  text")])]
                    )
                ],
                checked=True,
            )
        ],
        block_index=0,
    )
    table = Table(
        headers=[Cell(children=[Text("Head  one")])],
        rows=[[Cell(children=[Text("Cell   value")])]],
        alignments=["center"],
        block_index=1,
    )
    quote = Blockquote(
        children=[Paragraph(children=[Text("Quoted   words")])],
        block_index=2,
    )
    doc = Document(children=[rich_list, table, quote], source_id="src-rich")

    preview = plan_cleaning(doc, [RULES["whitespace"]()])
    cleaned = preview.document

    assert isinstance(cleaned.children[0], ListBlock)
    assert cleaned.children[0].ordered is False
    assert cleaned.children[0].items[0].checked is True
    list_para = cleaned.children[0].items[0].children[0]
    assert isinstance(list_para.children[1], Bold)
    assert block_text(cleaned.children[0]) == "Alpha bold text"
    assert isinstance(cleaned.children[1], Table)
    assert cleaned.children[1].alignments == ["center"]
    assert block_text(cleaned.children[1]) == "Head one\nCell value"
    assert isinstance(cleaned.children[2], Blockquote)
    assert block_text(cleaned.children[2]) == "Quoted words"


def test_transform_byte_count_uses_utf8():
    doc = _paragraphs("ééabcdefgh")

    preview = plan_cleaning(
        doc,
        [RegexRule("remove-acute", "é", "")],
        max_remove_frac=1.0,
    )

    record = preview.records[0]
    assert record.chars_removed == 2
    assert record.bytes_removed == 4


def test_tampered_plan_fails_replay():
    doc = _paragraphs("Alpha   beta")
    preview = plan_cleaning(doc, [RULES["whitespace"]()])
    operation = preview.plan.operations[0]
    tampered = replace(
        preview.plan,
        operations=(replace(operation, replacement="invented"),),
    )

    with pytest.raises(CleaningPlanError):
        replay_cleaning_plan(doc, tampered)


def test_whitespace_rule_preserves_semantics_across_inline_boundaries():
    doc = Document(
        children=[
            Paragraph(
                children=[Text("Alpha "), Bold(children=[Text("  beta")])],
                block_index=0,
            )
        ],
        source_id="src-inline",
    )

    preview = plan_cleaning(doc, [RULES["whitespace"]()])

    paragraph = preview.document.children[0]
    assert block_text(paragraph) == "Alpha beta"
    assert isinstance(paragraph.children[1], Bold)


def test_page_furniture_rule_never_removes_a_rich_block():
    rich = ListBlock(
        ordered=True,
        items=[ListItem(children=[Paragraph(children=[Text("42")])])],
        block_index=0,
    )
    doc = Document(
        children=[
            rich,
            Paragraph(children=[Text("A long body paragraph remains intact.")], block_index=1),
        ],
        source_id="src-rich-number",
    )

    preview = plan_cleaning(doc, [RULES["page-numbers"]()])

    assert isinstance(preview.document.children[0], ListBlock)
    assert block_text(preview.document.children[0]) == "42"


def test_rule_spec_binds_every_regex_behavior_parameter():
    doc = _paragraphs("unchanged")

    first = plan_cleaning(doc, [RegexRule("rewrite", "a", "b")]).plan
    second = plan_cleaning(doc, [RegexRule("rewrite", "x", "y")]).plan

    assert first.id != second.id


def test_note_bodies_are_cleaned_and_replayed_without_flattening():
    doc = _paragraphs("body")
    doc.footnotes["n"] = Footnote(
        id="n",
        children=[Paragraph(children=[Text("note   text")])],
    )

    preview = plan_cleaning(doc, [RULES["whitespace"]()])
    replayed = replay_cleaning_plan(doc, preview.plan)

    note = replayed.footnotes["n"].children[0]
    assert isinstance(note, Paragraph)
    assert block_text(note) == "note text"


def test_cleaning_plan_deserialization_rejects_unknown_fields():
    plan = plan_cleaning(_paragraphs("Alpha   beta"), [RULES["whitespace"]()]).plan
    serialized = cleaning_plan_to_dict(plan)
    serialized["approval"] = "forged"

    with pytest.raises(CleaningPlanError):
        cleaning_plan_from_dict(serialized)


def test_cleaning_plan_loader_recomputes_operation_identity():
    serialized = cleaning_plan_to_dict(
        plan_cleaning(_paragraphs("Alpha   beta"), [RULES["whitespace"]()]).plan
    )
    serialized["operations"][0]["replacement"] = "forged"

    with pytest.raises(CleaningPlanError, match="operation .* digest mismatch"):
        cleaning_plan_from_dict(serialized)


def test_cleaning_plan_loader_recomputes_plan_identity():
    serialized = cleaning_plan_to_dict(
        plan_cleaning(_paragraphs("Alpha   beta"), [RULES["whitespace"]()]).plan
    )
    serialized["max_remove_ppm"] += 1

    with pytest.raises(CleaningPlanError, match="cleaning plan digest mismatch"):
        cleaning_plan_from_dict(serialized)


def test_durable_note_cleaning_records_canonical_source_location(tmp_path):
    result = parse_md_file(
        tmp_path / "notes.md",
        raw_bytes=b"Body[^n]\n\n[^n]: note   text",
        logical_path="notes.md",
    )
    state_digest = sha256_digest("note-cleaning-state")

    preview = plan_cleaning(
        result.document,
        [RULES["whitespace"]()],
        base_input_sha256=state_digest,
    )

    note_index = result.document.footnotes["n"].children[0].block_index
    operation = next(
        item for item in preview.plan.operations if item.block_index == note_index
    )
    assert operation.source_start is not None
    assert operation.source_end is not None
    assert operation.source_text_sha256 is not None


def _rehash_first_operation(plan_value):
    operation = plan_value["operations"][0]
    operation["id"] = derive_id(
        "op",
        {
            **operation,
            "id": "",
            "replacement_sha256": sha256_digest(operation["replacement"]),
        },
    )
    for run in plan_value["runs"]:
        if run["operation_ids"]:
            run["operation_ids"][0] = operation["id"]
            break
    plan_value["id"] = derive_id("cln", {**plan_value, "id": ""})


def test_self_consistent_unknown_operation_kind_is_rejected():
    value = cleaning_plan_to_dict(
        plan_cleaning(_paragraphs("Alpha   beta"), [RULES["whitespace"]()]).plan
    )
    value["operations"][0]["kind"] = "invented-op"
    _rehash_first_operation(value)

    with pytest.raises(CleaningPlanError, match="kind is invalid"):
        cleaning_plan_from_dict(value)


def test_self_consistent_non_text_operation_path_is_rejected():
    document = _paragraphs("Alpha   beta")
    value = cleaning_plan_to_dict(
        plan_cleaning(document, [RULES["whitespace"]()]).plan
    )
    operation = value["operations"][0]
    operation.update(
        path=["source_id"],
        start=0,
        end=len(document.source_id),
        expected=document.source_id,
        expected_sha256=sha256_digest(document.source_id),
        replacement="src-forged",
    )
    _rehash_first_operation(value)
    forged = cleaning_plan_from_dict(value)

    with pytest.raises(CleaningPlanError, match="non-editable IR field"):
        replay_cleaning_plan(document, forged)


def test_self_consistent_forged_audit_counts_are_rejected():
    document = _paragraphs("Alpha   beta")
    value = deepcopy(
        cleaning_plan_to_dict(
            plan_cleaning(document, [RULES["whitespace"]()]).plan
        )
    )
    value["runs"][0]["chars_removed"] += 1
    value["id"] = derive_id("cln", {**value, "id": ""})
    forged = cleaning_plan_from_dict(value)

    with pytest.raises(CleaningPlanError, match="audit counts"):
        replay_cleaning_plan(document, forged)
