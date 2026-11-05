"""MEMRADER_TOP_P lets memory extraction leave top_p out of the request.

Some OpenAI-compatible upstreams reject top_p outright (HTTP 400). On such a
route every extraction failed and went to the fallback model.
"""

import json

import httpx
import openai
import pytest

from oh_memos.api.config import APIConfig
from oh_memos.configs import llm_defaults
from oh_memos.configs.llm import OpenAILLMConfig
from oh_memos.llms.openai import OpenAILLM


MESSAGES = [{"role": "user", "content": "hi"}]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, 0.95), ("", 0.95), ("  ", 0.95), ("none", None), ("NULL", None), ("0.8", 0.8)],
)
def test_memreader_top_p_from_env(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv("MEMRADER_TOP_P", raising=False)
    else:
        monkeypatch.setenv("MEMRADER_TOP_P", raw)
    assert llm_defaults.memreader_top_p() == expected


def test_memreader_config_follows_env(monkeypatch):
    monkeypatch.setenv("MEMRADER_TOP_P", "none")
    assert APIConfig.get_memreader_config()["config"]["top_p"] is None
    monkeypatch.delenv("MEMRADER_TOP_P")
    assert APIConfig.get_memreader_config()["config"]["top_p"] == 0.95


def _llm(top_p, response):
    sent = {}

    def handler(request):
        sent.update(json.loads(request.content))
        return response

    config = OpenAILLMConfig(
        model_name_or_path="m", api_key="k", api_base="http://upstream.test/v1", top_p=top_p
    )
    llm = OpenAILLM(config)
    llm.client = openai.Client(
        api_key="k",
        base_url="http://upstream.test/v1",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return llm, sent


def _completion():
    return httpx.Response(
        200,
        json={
            "id": "c",
            "object": "chat.completion",
            "created": 0,
            "model": "m",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "ok"},
                }
            ],
        },
    )


def _stream():
    chunk = {
        "id": "c",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "m",
        "choices": [{"index": 0, "delta": {"content": "ok"}, "finish_reason": None}],
    }
    body = f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n"
    return httpx.Response(
        200, content=body.encode(), headers={"content-type": "text/event-stream"}
    )


@pytest.mark.parametrize(("top_p", "sent_top_p"), [(None, "omitted"), (0.95, 0.95)])
def test_generate_omits_top_p_only_when_none(top_p, sent_top_p):
    llm, sent = _llm(top_p, _completion())
    assert llm.generate(MESSAGES) == "ok"
    assert sent.get("top_p", "omitted") == sent_top_p


@pytest.mark.parametrize(("top_p", "sent_top_p"), [(None, "omitted"), (0.95, 0.95)])
def test_generate_stream_omits_top_p_only_when_none(top_p, sent_top_p):
    llm, sent = _llm(top_p, _stream())
    assert "".join(llm.generate_stream(MESSAGES)) == "ok"
    assert sent.get("top_p", "omitted") == sent_top_p
