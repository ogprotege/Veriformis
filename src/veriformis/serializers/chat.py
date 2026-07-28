"""Chat-template rendering. Templates are Jinja2, matching the HF chat_template
convention so output is byte-identical to what a trainer produces."""
from __future__ import annotations

from importlib import resources

from jinja2 import Template

_TEMPLATE_NAMES = ("llama3", "mistral", "qwen", "gemma", "phi")


def _load() -> dict[str, str]:
    out = {}
    for name in _TEMPLATE_NAMES:
        ref = resources.files("veriformis.serializers.templates.chat").joinpath(f"{name}.jinja")
        out[name] = ref.read_text(encoding="utf-8")
    return out


CHAT_TEMPLATES: dict[str, str] = _load()


def render_chat(messages: list[dict[str, str]], *, template: str) -> str:
    if template not in CHAT_TEMPLATES:
        raise ValueError(f"unknown-template: {template!r} (have: {sorted(CHAT_TEMPLATES)})")
    return Template(CHAT_TEMPLATES[template]).render(messages=messages)


def serialize_chat(records: list[dict], *, template: str) -> list[dict]:
    out = []
    for record in records:
        messages = []
        if record.get("system"):
            messages.append({"role": "system", "content": record["system"]})
        messages.append({"role": "user", "content": record["user"]})
        messages.append({"role": "assistant", "content": record["assistant"]})
        out.append({"text": render_chat(messages, template=template)})
    return out
