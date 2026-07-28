"""Style name mapping between Word paragraph styles and the Veriformis IR.

The mapping is deliberately small: only the style names Word uses for
the canonical semantic elements. Anything else gets treated as a normal
paragraph on ingest.
"""

from __future__ import annotations

# Word paragraph style names -> Veriformis IR block role.
# We accept both Word's localized display names and internal style IDs
# where common aliases exist.

HEADING_STYLES: dict[str, int] = {
    "Title": 1,
    "Heading 1": 1,
    "Heading1": 1,
    "heading 1": 1,
    "Heading 2": 2,
    "Heading2": 2,
    "heading 2": 2,
    "Heading 3": 3,
    "Heading3": 3,
    "heading 3": 3,
    "Heading 4": 4,
    "Heading4": 4,
    "heading 4": 4,
    "Heading 5": 5,
    "Heading5": 5,
    "heading 5": 5,
    "Heading 6": 6,
    "Heading6": 6,
    "heading 6": 6,
}

BLOCKQUOTE_STYLES: set[str] = {
    "Quote",
    "Intense Quote",
    "IntenseQuote",
    "Block Text",
    "BlockText",
    # Common block-quote style names from other tools/templates (LibreOffice
    # uses "Quotations"; many templates use "Quotation"/"Block Quote"/"Extract").
    "Quotation",
    "Quotations",
    "Block Quote",
    "BlockQuote",
    "Block Quotation",
    "BlockQuotation",
    "Extract",
}

CODE_BLOCK_STYLES: set[str] = {
    "Source Code",
    "SourceCode",
    "Code",
    "Code Block",
    "CodeBlock",
    "HTML Preformatted",
}

LIST_PARAGRAPH_STYLES: set[str] = {
    "List Paragraph",
    "ListParagraph",
    "List Bullet",
    "ListBullet",
    "List Number",
    "ListNumber",
}


# IR block -> Word paragraph style name used on output.
# These are the style names the default reference template defines.
OUTPUT_STYLE_HEADING = {
    1: "Heading 1",
    2: "Heading 2",
    3: "Heading 3",
    4: "Heading 4",
    5: "Heading 5",
    6: "Heading 6",
}
OUTPUT_STYLE_PARAGRAPH = "Normal"
OUTPUT_STYLE_QUOTE = "Quote"
OUTPUT_STYLE_CODE_BLOCK = "Source Code"
OUTPUT_STYLE_LIST_BULLET = "List Bullet"
OUTPUT_STYLE_LIST_NUMBER = "List Number"


def heading_level(style_name: str) -> int | None:
    return HEADING_STYLES.get(style_name)


def is_blockquote(style_name: str) -> bool:
    return style_name in BLOCKQUOTE_STYLES


def is_code_block(style_name: str) -> bool:
    return style_name in CODE_BLOCK_STYLES


def is_list_paragraph(style_name: str) -> bool:
    return style_name in LIST_PARAGRAPH_STYLES
