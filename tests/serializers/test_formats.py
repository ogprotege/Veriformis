from veriformis.chunkers.base import Chunk
from veriformis.serializers.formats import serialize_completion, serialize_instruction


def _chunk(text="body", path=None):
    return Chunk(id="chk-1", source_id="s", block_index=0, span=None,
                 heading_path=path or [], text=text, tokens_est=2)


def test_completion_plain_and_with_heading_path():
    assert serialize_completion([_chunk()])[0] == {"text": "body"}
    out = serialize_completion([_chunk(path=["Intro", "Scope"])], include_heading_path=True)
    assert out[0]["text"] == "Intro > Scope\n\nbody"


def test_instruction_mapping():
    out = serialize_instruction([_chunk(path=["Ch1"])], instruction="Summarize the section.")
    assert out[0] == {"instruction": "Summarize the section.", "input": "Ch1", "output": "body"}
