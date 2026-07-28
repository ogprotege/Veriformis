import pytest

from veriformis.serializers.chat import CHAT_TEMPLATES, render_chat, serialize_chat

MESSAGES = [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello!"},
]


def test_llama3_golden():
    assert render_chat(MESSAGES, template="llama3") == (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        "You are helpful.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
        "Hi<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\nHello!<|eot_id|>"
    )


def test_qwen_golden():
    assert render_chat(MESSAGES, template="qwen") == (
        "<|im_start|>system\nYou are helpful.<|im_end|>\n"
        "<|im_start|>user\nHi<|im_end|>\n<|im_start|>assistant\nHello!<|im_end|>"
    )


def test_mistral_gemma_phi_golden():
    assert render_chat(MESSAGES, template="mistral") == "<s>[INST] You are helpful.\n\nHi [/INST] Hello!</s>"
    assert render_chat(MESSAGES, template="gemma") == (
        "<bos><start_of_turn>user\nYou are helpful.\n\nHi<end_of_turn>\n<start_of_turn>model\nHello!<end_of_turn>"
    )
    assert render_chat(MESSAGES, template="phi") == (
        "<|system|>\nYou are helpful.<|end|>\n<|user|>\nHi<|end|>\n<|assistant|>\nHello!<|end|>"
    )


def test_unknown_template_fails_closed():
    with pytest.raises(ValueError, match="unknown-template"):
        render_chat(MESSAGES, template="unknown-template")


def test_serialize_chat_pairs():
    out = serialize_chat([{"user": "Hi", "assistant": "Hello!"}], template="qwen")
    assert out == [{"text": "<|im_start|>user\nHi<|im_end|>\n<|im_start|>assistant\nHello!<|im_end|>"}]


def test_builtin_template_set():
    assert set(CHAT_TEMPLATES) == {"llama3", "mistral", "qwen", "gemma", "phi"}
