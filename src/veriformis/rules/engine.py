"""Deterministic cleaning-rule engine. Every firing is logged; destructive
rules are refused, never silently applied."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from veriformis.ir import Document, block_text, set_block_text


@dataclass
class Edit:
    start: int
    end: int
    replacement: str = ""


@dataclass
class RuleResult:
    text: str
    edits: list[Edit] = field(default_factory=list)


class Rule(Protocol):
    name: str

    def apply(self, text: str) -> RuleResult: ...


@dataclass
class RegexRule:
    name: str
    pattern: str
    replacement: str = ""
    flags: int = re.IGNORECASE | re.MULTILINE
    params: dict = field(default_factory=dict)

    def apply(self, text: str) -> RuleResult:
        rx = re.compile(self.pattern, self.flags)
        edits = [
            Edit(m.start(), m.end(), m.expand(self.replacement))
            for m in rx.finditer(text)
        ]
        return RuleResult(text=rx.sub(self.replacement, text), edits=edits)


@dataclass
class TransformRecord:
    rule: str
    params: dict
    block_index: int
    edits: int
    bytes_removed: int
    warned: bool = False


def apply_rules(
    text: str, rules: list[Rule], *, max_remove_frac: float = 0.3
) -> tuple[str, list[TransformRecord], list[str]]:
    records: list[TransformRecord] = []
    warnings: list[str] = []
    current = text
    for rule in rules:
        before = current
        result = rule.apply(before)
        removed = len(before) - len(result.text)
        warned = len(before) > 0 and removed > max_remove_frac * len(before)
        records.append(
            TransformRecord(
                rule=rule.name,
                params=getattr(rule, "params", {}),
                block_index=-1,
                edits=len(result.edits),
                bytes_removed=removed,
                warned=warned,
            )
        )
        if warned:
            warnings.append(
                f"rule '{rule.name}' skipped: would remove {removed}/{len(before)} chars"
            )
        else:
            current = result.text
    return current, records, warnings


def clean_document(
    doc: Document, rules: list[Rule], *, max_remove_frac: float = 0.3
) -> tuple[Document, list[TransformRecord], list[str]]:
    all_records: list[TransformRecord] = []
    all_warnings: list[str] = []
    new_children = []
    for i, block in enumerate(doc.children):
        original = block_text(block)
        cleaned, records, warnings = apply_rules(original, rules, max_remove_frac=max_remove_frac)
        for r in records:
            # Prefer the block's provenance index; hand-built blocks carry the
            # -1 sentinel, so fall back to document position.
            r.block_index = block.block_index if block.block_index != -1 else i
        all_records.extend(r for r in records if r.edits > 0 or r.warned)
        all_warnings.extend(warnings)
        new_children.append(set_block_text(block, cleaned) if cleaned != original else block)
    return (
        Document(
            children=new_children,
            footnotes=doc.footnotes,
            endnotes=doc.endnotes,
            source_id=doc.source_id,
        ),
        all_records,
        all_warnings,
    )
