"""Stock cleaning rules. Line-anchored and conservative by design: a rule may
never delete inline content that merely *looks* structural."""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

from veriformis.errors import RuleError
from veriformis.rules.engine import RegexRule, Rule

CLEAN_MAX_REMOVE_PPM = 300_000


class _RepeatedLineRule:
    """Removes short lines (<=80 chars stripped) appearing >= threshold times —
    the honest v1 approximation of header/footer detection."""

    name = "headers-footers"

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.params = {"threshold": threshold}

    def apply(self, text: str):
        from veriformis.rules.engine import RuleResult

        lines = text.split("\n")
        counts: dict[str, int] = {}
        for line in lines:
            key = line.strip()
            if key and len(key) <= 80:
                counts[key] = counts.get(key, 0) + 1
        out = []
        for line in lines:
            key = line.strip()
            drop = bool(key) and len(key) <= 80 and counts.get(key, 0) >= self.threshold
            if not drop:
                out.append(line)
        cleaned = "\n".join(out)
        return RuleResult(text=cleaned, edits=_diff_edits(text, cleaned))


def custom_regex(pattern: str, replacement: str = "") -> Rule:
    return RegexRule("custom", pattern, replacement, params={"pattern": pattern, "replacement": replacement})


class _LowercaseRule:
    name = "lowercase"
    params: dict = {}

    def apply(self, text: str):
        from veriformis.rules.engine import RuleResult

        lowered = text.lower()
        return RuleResult(text=lowered, edits=_diff_edits(text, lowered))


def _diff_edits(before: str, after: str):
    """Return deterministic, non-overlapping edits that exactly make `after`."""
    from difflib import SequenceMatcher

    from veriformis.rules.engine import Edit

    return [
        Edit(i1, i2, after[j1:j2])
        for tag, i1, i2, j1, j2 in SequenceMatcher(
            a=before, b=after, autojunk=False
        ).get_opcodes()
        if tag != "equal"
    ]


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


def rules_from_clean_config(config: Mapping[str, Any]) -> list[Rule]:
    """Decode the exact executable rule list allowed by clean-stage v1."""
    if not isinstance(config, Mapping) or set(config) != {
        "rules",
        "custom",
        "max_remove_ppm",
    }:
        raise RuleError("clean config keys do not match the v1 schema")
    names = config["rules"]
    custom = config["custom"]
    max_remove_ppm = config["max_remove_ppm"]
    if not isinstance(names, list) or not all(
        isinstance(name, str) and name for name in names
    ):
        raise RuleError("clean config rules must be non-empty strings")
    unknown = [name for name in names if name not in RULES]
    if unknown:
        raise RuleError(f"unknown cleaning rule(s): {', '.join(unknown)}")
    if custom is not None and (not isinstance(custom, str) or not custom):
        raise RuleError("clean config custom pattern must be null or non-empty text")
    if type(max_remove_ppm) is not int or max_remove_ppm != CLEAN_MAX_REMOVE_PPM:
        raise RuleError(
            f"clean config max_remove_ppm must equal {CLEAN_MAX_REMOVE_PPM}"
        )
    selected = [RULES[name]() for name in names]
    if custom is not None:
        custom_rule = custom_regex(custom)
        try:
            re.compile(custom_rule.pattern, custom_rule.flags)
        except re.error as exc:
            raise RuleError(f"invalid custom regular expression: {exc}") from exc
        selected.append(custom_rule)
    if not selected:
        raise RuleError("clean config must select at least one rule")
    return selected


def select_rules(
    rules: str,
    custom: str,
) -> tuple[list[Rule], dict[str, Any]]:
    """Build and decode the canonical v1 config from CLI option strings."""
    if not rules and not custom:
        names = ["page-numbers", "whitespace"]
    else:
        names = [name.strip() for name in rules.split(",") if name.strip()]
    config: dict[str, Any] = {
        "rules": names,
        "custom": custom or None,
        "max_remove_ppm": CLEAN_MAX_REMOVE_PPM,
    }
    return rules_from_clean_config(config), config
