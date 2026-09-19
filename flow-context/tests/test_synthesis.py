import asyncio
import json
from pathlib import Path

import httpx
import pytest

from flow_context.config import LlmConfig
from flow_context.store import load_moments
from flow_context.synthesis import format_prompt, synthesize
import flow_context.synthesis as synthesis_module


MOMENTS = load_moments(Path(__file__).resolve().parents[1] / "data/example_moments.json")
CONFIG = LlmConfig(base_url="https://example.test/v1", model="test-model", api_key="test-key")
UTTERANCE = "Given everything I've thought about Flow Context, what am I still missing?"


def completion(content):
    return {"choices": [{"message": {"content": content}}]}


def run_synthesis(handler, config=CONFIG, diagnostics=None):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await synthesize(UTTERANCE, MOMENTS, client, config, diagnostics=diagnostics)

    return asyncio.run(go())


def test_synthesizes_selected_sources_and_preserves_user_rejection():
    def handler(request):
        assert str(request.url) == "https://example.test/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["stream"] is False
        assert body["response_format"] == {"type": "json_object"}
        prompt = "\n".join(message["content"] for message in body["messages"])
        assert "chat-02" in prompt and "chat-03" in prompt and "voice-07" in prompt
        assert "rejection" in prompt and "user decisions" in prompt
        packet = {
            "context_summary": "The user rejected the AI's standalone reflection app proposal and now wants short dictation expanded in the destination app.",
            "source_ids": ["chat-02", "chat-03", "chat-05", "voice-07"],
        }
        return httpx.Response(200, json=completion(json.dumps(packet)))

    packet = run_synthesis(handler)
    assert packet is not None
    assert "doc-06" not in packet.source_ids
    output = format_prompt(UTTERANCE, packet, MOMENTS)
    assert output.startswith(UTTERANCE + "\n\nHistorical context\n")
    assert "rejected the AI's standalone reflection app proposal" in output
    assert "chat-03 (Sep 17, synthetic)" in output
    assert "My request:" not in output
    assert "Current direction:" not in output


@pytest.mark.parametrize(
    "response",
    [
        completion("not json"),
        completion(""),
        completion(json.dumps({"context_summary": "Summary", "source_ids": ["unknown"]})),
        completion(json.dumps({"context_summary": " ", "source_ids": ["chat-05"]})),
        completion(json.dumps({"context_summary": "x" * 1700, "source_ids": ["chat-05"]})),
    ],
)
def test_bad_model_output_returns_no_packet(response):
    packet = run_synthesis(lambda request: httpx.Response(200, json=response))
    assert packet is None


def test_timeout_returns_no_packet():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    assert run_synthesis(handler) is None


def test_fallback_reason_identifies_invalid_response_without_leaking_content():
    diagnostics = {}

    assert run_synthesis(lambda request: httpx.Response(200, json=completion("not json")), diagnostics=diagnostics) is None
    assert diagnostics == {"reason": "invalid_model_response"}


def test_model_bullet_list_summary_is_normalized_to_text():
    packet = {
        "context_summary": ["The user rejected the separate reflection app.", "Context should appear in the destination app."],
        "source_ids": ["chat-03", "chat-05"],
    }

    result = run_synthesis(lambda request: httpx.Response(200, json=completion(json.dumps(packet))))

    assert result is not None
    assert result.context_summary == "The user rejected the separate reflection app.; Context should appear in the destination app."


def test_comma_separated_source_ids_are_accepted():
    packet = {
        "context_summary": "The user rejected the separate reflection app and wants context in the destination app.",
        "source_ids": "chat-03, chat-05, voice-07",
    }

    result = run_synthesis(lambda request: httpx.Response(200, json=completion(json.dumps(packet))))

    assert result is not None
    assert result.source_ids == ["chat-03", "chat-05", "voice-07"]


def test_total_deadline_returns_no_packet(monkeypatch):
    monkeypatch.setattr(synthesis_module, "REQUEST_TIMEOUT_SECONDS", 0.01)

    async def handler(request):
        await asyncio.sleep(0.05)
        packet = {
            "context_summary": "Use context in another app after rejecting the standalone app.",
            "source_ids": ["chat-03"],
        }
        return httpx.Response(200, json=completion(json.dumps(packet)))

    assert run_synthesis(handler) is None


def test_missing_key_makes_no_request():
    def handler(request):
        raise AssertionError("model request should not be sent")

    assert run_synthesis(handler, LlmConfig(CONFIG.base_url, CONFIG.model, "")) is None
