from veriformis.rules.library import RULES, custom_regex, default_rules


def _apply(name, text):
    return RULES[name]().apply(text).text


def test_page_numbers_line_anchored_only():
    # THE canonical regression: tunerepo's regex deleted every standalone number.
    text = "In 1492 Columbus sailed.\n\n37\n\nPage 12 of 98\n\nThe year 1492 matters.\n"
    out = _apply("page-numbers", text)
    assert "1492" in out
    assert "37" not in out
    assert "Page 12 of 98" not in out


def test_page_numbers_conservative_on_inline_and_boundaries():
    # Task-7 review amendment: leading inline numbers survive; paragraph
    # boundaries are never merged by a removal.
    text = "37 people attended the meeting.\n\npara one\n\n42\n\npara two\n"
    out = _apply("page-numbers", text)
    assert out == "37 people attended the meeting.\n\npara one\n\n\npara two\n"


def test_headers_footers_strips_only_short_repeated_lines():
    lines = ["CONFIDENTIAL DRAFT"] + [f"Unique sentence number {i} here." for i in range(6)]
    text = "CONFIDENTIAL DRAFT\n" + "\n".join(lines[1:3]) + "\nCONFIDENTIAL DRAFT\n" + "\n".join(lines[3:]) + "\nCONFIDENTIAL DRAFT"
    out = _apply("headers-footers", text)
    assert "CONFIDENTIAL DRAFT" not in out
    assert "Unique sentence number 4 here." in out


def test_whitespace_urls_emails_lowercase():
    assert _apply("whitespace", "a   b\t\tc") == "a b c"
    assert _apply("whitespace", "a\n\n\nb") == "a\n\n\nb"  # newlines are structural
    assert _apply("urls", "see https://example.com/x now") == "see  now"
    assert _apply("emails", "mail me@example.com please") == "mail  please"
    assert _apply("lowercase", "HeLLo") == "hello"


def test_special_chars_whitelist_conservative():
    out = _apply("special-chars", "price: $5 (ok) — really!")
    assert "$" not in out and "—" not in out
    assert "price" in out and "really!" in out


def test_custom_regex_and_defaults():
    rule = custom_regex(r"\[.*?\]")
    assert rule.apply("keep [drop] this").text == "keep  this"
    assert [r.name for r in default_rules()] == ["page-numbers", "whitespace"]
