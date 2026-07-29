"""Strict, versioned JSON serialization for the canonical document IR."""
from __future__ import annotations

import types
from dataclasses import fields, is_dataclass
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from veriformis.errors import InvalidIRError
from veriformis.identity import validate_id
from veriformis.ir import nodes

IR_SCHEMA_VERSION = "veriformis.ir/v1"

_NODE_TYPES = {
    cls.__name__: cls
    for cls in (
        nodes.Span,
        nodes.Text,
        nodes.Bold,
        nodes.Italic,
        nodes.Strikethrough,
        nodes.Superscript,
        nodes.Subscript,
        nodes.Code,
        nodes.Link,
        nodes.Image,
        nodes.LineBreak,
        nodes.FootnoteRef,
        nodes.EndnoteRef,
        nodes.Math,
        nodes.Citation,
        nodes.Heading,
        nodes.Paragraph,
        nodes.CodeBlock,
        nodes.Blockquote,
        nodes.HorizontalRule,
        nodes.ListItem,
        nodes.ListBlock,
        nodes.Cell,
        nodes.Table,
        nodes.Footnote,
        nodes.Endnote,
        nodes.Document,
    )
}


def _node_to_dict(node: Any) -> dict:
    if type(node).__name__ not in _NODE_TYPES or not is_dataclass(node):
        raise InvalidIRError(f"unsupported IR node type: {type(node).__name__}")
    out: dict[str, Any] = {"type": type(node).__name__}
    for item in fields(node):
        out[item.name] = _value_to_json(getattr(node, item.name))
    return out


def _value_to_json(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _node_to_dict(value)
    if isinstance(value, list):
        return [_value_to_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _value_to_json(item) for key, item in value.items()}
    return value


def document_to_dict(document: nodes.Document) -> dict:
    return {
        "schema_version": IR_SCHEMA_VERSION,
        "document": _node_to_dict(document),
    }


def _node_from_dict(value: dict) -> Any:
    if not isinstance(value, dict) or not isinstance(value.get("type"), str):
        raise InvalidIRError("IR node must be an object with a string type")
    tag = value["type"]
    cls = _NODE_TYPES.get(tag)
    if cls is None:
        raise InvalidIRError(f"unsupported IR node type: {tag!r}")
    expected = {"type", *(item.name for item in fields(cls))}
    if set(value) != expected:
        raise InvalidIRError(f"IR node {tag!r} fields do not match the v1 schema")
    kwargs = {
        key: _value_from_json(item)
        for key, item in value.items()
        if key != "type"
    }
    try:
        node = cls(**kwargs)
    except (TypeError, ValueError) as exc:
        raise InvalidIRError(f"invalid IR node {tag!r}: {exc}") from exc
    hints = get_type_hints(cls, vars(nodes), vars(nodes))
    for name, annotation in hints.items():
        _validate_typed_value(getattr(node, name), annotation, path=f"{tag}.{name}")
    return node


def _value_from_json(value: Any) -> Any:
    if isinstance(value, dict) and "type" in value:
        return _node_from_dict(value)
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise InvalidIRError("IR object keys must be strings")
        return {key: _value_from_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_value_from_json(item) for item in value]
    return value


def _validate_typed_value(value: Any, annotation: Any, *, path: str) -> None:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, types.UnionType):
        for candidate in args:
            try:
                _validate_typed_value(value, candidate, path=path)
            except InvalidIRError:
                continue
            return
        raise InvalidIRError(f"{path} has an invalid union value")
    if origin is Literal:
        if value not in args:
            raise InvalidIRError(f"{path} has an invalid literal value")
        return
    if origin is list:
        if not isinstance(value, list):
            raise InvalidIRError(f"{path} must be an array")
        for index, item in enumerate(value):
            _validate_typed_value(item, args[0], path=f"{path}[{index}]")
        return
    if origin is dict:
        if not isinstance(value, dict):
            raise InvalidIRError(f"{path} must be an object")
        key_type, item_type = args
        for key, item in value.items():
            _validate_typed_value(key, key_type, path=f"{path}.key")
            _validate_typed_value(item, item_type, path=f"{path}[{key!r}]")
        return
    if annotation is type(None):
        if value is not None:
            raise InvalidIRError(f"{path} must be null")
        return
    if annotation is int:
        if type(value) is not int:
            raise InvalidIRError(f"{path} must be an integer")
        return
    if annotation is bool:
        if type(value) is not bool:
            raise InvalidIRError(f"{path} must be a boolean")
        return
    if annotation in (str, float):
        if not isinstance(value, annotation):
            raise InvalidIRError(f"{path} has the wrong scalar type")
        return
    if isinstance(annotation, type) and not isinstance(value, annotation):
        raise InvalidIRError(f"{path} must be {annotation.__name__}")


def _validate_document_structure(document: nodes.Document) -> None:
    try:
        validate_id(document.source_id, kind="src")
    except (TypeError, ValueError) as exc:
        raise InvalidIRError("persisted IR requires a valid source identity") from exc
    for collection_name in ("footnotes", "endnotes"):
        collection = getattr(document, collection_name)
        if any(key != note.id for key, note in collection.items()):
            raise InvalidIRError(f"{collection_name} map key does not match note identity")
    indexes: list[int] = []
    prior_start = -1
    for block in nodes.iter_document_blocks(document):
        if type(block.block_index) is not int or block.block_index < 0:
            raise InvalidIRError("canonical IR block index must be non-negative")
        if block.span is None:
            raise InvalidIRError("canonical IR block lacks a source span")
        if (
            type(block.span.start) is not int
            or type(block.span.end) is not int
            or not 0 <= block.span.start <= block.span.end
        ):
            raise InvalidIRError("canonical IR block span is invalid")
        if block.span.start < prior_start:
            raise InvalidIRError("canonical IR block spans are out of order")
        prior_start = block.span.start
        indexes.append(block.block_index)
    if indexes != sorted(indexes) or len(indexes) != len(set(indexes)):
        raise InvalidIRError("canonical IR block indexes are duplicated or out of order")


def validate_document_against_stream(
    document: nodes.Document,
    canonical_stream: str,
    *,
    exact: bool,
) -> None:
    """Verify block provenance against its immutable canonical text artifact."""
    _validate_document_structure(document)
    blocks = list(nodes.iter_document_blocks(document))
    if any(block.span.end > len(canonical_stream) for block in blocks):
        raise InvalidIRError("canonical IR block span exceeds its source artifact")
    if not exact:
        return
    projection = "\n\n".join(nodes.block_text(block) for block in blocks)
    if projection != canonical_stream:
        raise InvalidIRError("parsed IR projection does not match canonical source text")
    position = 0
    for block_index, block in enumerate(blocks):
        text = nodes.block_text(block)
        if block.block_index != block_index:
            raise InvalidIRError("parsed IR block indexes are not canonical")
        if (block.span.start, block.span.end) != (position, position + len(text)):
            raise InvalidIRError("parsed IR block span does not match canonical text")
        position += len(text) + 2


def document_from_dict(value: dict) -> nodes.Document:
    if not isinstance(value, dict) or set(value) != {"schema_version", "document"}:
        raise InvalidIRError("document IR keys do not match the v1 schema")
    if value["schema_version"] != IR_SCHEMA_VERSION:
        raise InvalidIRError(f"unsupported document IR schema {value['schema_version']!r}")
    document = _node_from_dict(value["document"])
    if not isinstance(document, nodes.Document):
        raise InvalidIRError("document IR root must be a Document")
    _validate_document_structure(document)
    return document
