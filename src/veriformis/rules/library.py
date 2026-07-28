"""Stock cleaning rules. Line-anchored and conservative by design: a rule may
never delete inline content that merely *looks* structural."""
from __future__ import annotations

import re
from collections.abc import Callable

from veriformis.rules.engine import RegexRule, Rule


class _RepeatedLineRule:
    """Removes short lines (<=80 chars stripped) appearing >= threshold times —
    the honest v1 approximation of header/footer detection."""

    name = "headers-footers"

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.params = {"threshold": threshold}

    def apply(self, text: str):
        from veriformis.rules.engine import Edit, RuleResult

        lines = text.split("\n")
        counts: dict[str, int] = {}
        for line in lines:
            key = line.strip()
            if key and len(key) <= 80:
                counts[key] = counts.get(key, 0) + 1
        edits, out, pos = [], [], 0
        for line in lines:
            key = line.strip()
            drop = bool(key) and len(key) <= 80 and counts.get(key, 0) >= self.threshold
            if drop:
                edits.append(Edit(pos, pos + len(line)))
            else:
                out.append(line)
            pos += len(line) + 1
        return RuleResult(text="\n".join(out), edits=edits)


def custom_regex(pattern: str, replacement: str = "") -> Rule:
    return RegexRule("custom", pattern, replacement, params={"pattern": pattern, "replacement": replacement})


class _LowercaseRule:
    name = "lowercase"
    params: dict = {}

    def apply(self, text: str):
        from veriformis.rules.engine import Edit, RuleResult

        lowered = text.lower()
        return RuleResult(text=lowered, edits=[Edit(0, len(text))] if lowered != text else [])


RULES: dict[str, Callable[[], Rule]] = {
    "page-numbers": lambda: RegexRule(
        "page-numbers",
        r"^[ \t]*(?:\d{1,4}|(?:page|p\.?)\s*\d{1,4}(?:\s*of\s*\d{1,4})?)[ \t]*(?:\n|$)",
        "",
    ),
    "headers-footers": lambda: _RepeatedLineRule(),
    "whitespace": lambda: RegexRule("whitespace", r"[ \t]+", " ", flags=re.MULTILINE),
    "urls": lambda: RegexRule("urls", r"https?://[^\s]+"),
    "emails": lambda: RegexRule("emails", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "special-chars": lambda: RegexRule("special-chars", r"[^\w\s.,!?;:'\"()/-]"),
    "lowercase": lambda: _LowercaseRule(),
}


def default_rules() -> list[Rule]:
    return [RULES["page-numbers"](), RULES["whitespace"]()]
