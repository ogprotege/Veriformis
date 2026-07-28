"""JSON-safe serialization for the IR (roundtrip: from_dict(to_dict(doc)) == doc)."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from veriformis.ir import nodes


def _node_to_dict(node: Any) -> dict:
    out: dict[str, Any] = {"type": type(node).__name__}
    for f in fields(node):
        out[f.name] = _value_to_json(getattr(node, f.name))
    return out


def _value_to_json(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _node_to_dict(value)
    if isinstance(value, list):
        return [_value_to_json(v) for v in value]
    if isinstance(value, dict):
        return {k: _value_to_json(v) for k, v in value.items()}
    return value


def document_to_dict(doc: nodes.Document) -> dict:
    return _node_to_dict(doc)


def _node_from_dict(d: dict) -> Any:
    d = dict(d)
    tag = d.pop("type")
    cls = getattr(nodes, tag)
    kwargs = {k: _value_from_json(v) for k, v in d.items()}
    return cls(**kwargs)


def _value_from_json(value: Any) -> Any:
    if isinstance(value, dict) and "type" in value:
        return _node_from_dict(value)
    if isinstance(value, dict):
        return {k: _value_from_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_value_from_json(v) for v in value]
    return value


def document_from_dict(d: dict) -> nodes.Document:
    doc = _node_from_dict(d)
    assert isinstance(doc, nodes.Document)
    return doc
