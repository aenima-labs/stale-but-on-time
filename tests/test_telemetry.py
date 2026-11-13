import json

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

import providers
import telemetry
from pricing import PriceTable
from providers import ChatRequest, Usage
from telemetry_summary import summarise_condition, trial_records


def span(trace, name, start, end, **attrs):
    return {"trace_id": trace, "span_id": f"{trace}{name}{start}", "parent_span_id": "", "name": name,
            "kind": "internal", "start_unix_nano": int(1.8e18 + start * 1e6),
            "end_unix_nano": int(1.8e18 + end * 1e6), "status": {"code": "unset"},
            "attributes": attrs, "events": []}


def chat(trace, start, end, tin, tout, cached=0, purpose="reply", provider="openai", model="gpt-5.6-luna"):
    return span(trace, f"chat {model}", start, end, **{
        "gen_ai.operation.name": "chat", "gen_ai.provider.name": provider, "gen_ai.request.model": model,
        "gen_ai.usage.input_tokens": tin, "gen_ai.usage.output_tokens": tout,
        "gen_ai.usage.cache_read.input_tokens": cached, "e2.call.purpose": purpose})


def embed(trace, start, end, tokens, purpose="query"):
    return span(trace, "embeddings text-embedding-3-small", start, end, **{
        "gen_ai.operation.name": "embeddings", "gen_ai.provider.name": "openai",
        "gen_ai.request.model": "text-embedding-3-small", "gen_ai.usage.input_tokens": tokens,
        "e2.call.purpose": purpose})


def test_token_accounting_per_trial_and_index_overhead():
    spans = [
        span("a", "trial", 0, 100, **{"circumstances.trial_id": "t1", "e2.path.total_ms": 90.0}),
        embed("a", 0, 5, 2000, purpose="index"),
        chat("a", 10, 40, 1000, 50, purpose="tool_offer"),
        embed("a", 41, 45, 10),
        chat("a", 50, 90, 1200, 40, cached=1000),
        span("b", "trial", 200, 260, **{"circumstances.trial_id": "t2"}),
        chat("b", 200, 250, 800, 30),
    ]
    missing = set()
    trials, overhead = trial_records(spans, PriceTable(), missing)
    by_id = {t["trial_id"]: t for t in trials}
    assert by_id["t1"]["chat_calls"] == 2
    assert by_id["t1"]["input_tokens"] == 2200 and by_id["t1"]["output_tokens"] == 90
    assert by_id["t1"]["cached_input_tokens"] == 1000
    assert by_id["t1"]["embed_tokens"] == 10  # the index embedding is not per trial
    assert overhead["embed_tokens"] == 2000
    luna = (1000 * 0.20 + 50 * 1.20 + 200 * 0.20 + 1000 * 0.02 + 40 * 1.20) / 1e6 + 10 * 0.02 / 1e6
    assert by_id["t1"]["cost_usd"] == pytest.approx(luna)
    assert not missing

    s = summarise_condition(spans, PriceTable())
    assert s["trials"] == 2
    assert s["totals"]["chat_calls"] == 3
    assert s["totals"]["embed_tokens"] == 2010
    assert s["totals"]["cost_usd"] == pytest.approx(luna + 2000 * 0.02 / 1e6 + (800 * 0.20 + 30 * 1.20) / 1e6)
    assert s["latency_ms"]["chat:reply"]["n"] == 2


def test_missing_price_is_reported_not_zero():
    spans = [span("a", "trial", 0, 1), chat("a", 0, 1, 10, 10, provider="openai", model="no-such-model")]
    s = summarise_condition(spans, PriceTable())
    assert s["prices_missing"] == ["openai/no-such-model"]
    assert s["totals"]["cost_usd"] != s["totals"]["cost_usd"]  # NaN


def test_traced_chat_records_semconv_attributes_without_content(tmp_path):
    exporter_path = tmp_path / "spans.jsonl"
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(telemetry.JsonLinesSpanExporter(exporter_path)))
    tracer = provider.get_tracer("t")

    class Fake(providers.ChatClient):
        provider = "openai"
        model = "gpt-5.6-luna"
        server_address = "api.openai.com"

        def chat(self, request):
            return providers.ChatResult("{\"reply\": \"secret words\"}", [], Usage(120, 7, 100, 0),
                                        finish_reason="stop", response_model="gpt-5.6-luna-2026-07-30")

        @property
        def temperature_supported(self):
            return False

    req = ChatRequest("SYSTEM PROMPT", [{"role": "user", "content": "hello"}], None, 0.7, 5, 220, False)
    providers.traced_chat(tracer, Fake(), req, "reply")
    provider.shutdown()
    (s,) = telemetry.read_spans(exporter_path)
    a = s["attributes"]
    assert s["name"] == "chat gpt-5.6-luna" and s["kind"] == "client"
    assert a["gen_ai.operation.name"] == "chat" and a["gen_ai.provider.name"] == "openai"
    assert a["gen_ai.usage.input_tokens"] == 120 and a["gen_ai.usage.output_tokens"] == 7
    assert a["gen_ai.usage.cache_read.input_tokens"] == 100
    assert a["gen_ai.response.finish_reasons"] == ["stop"]
    assert "gen_ai.request.temperature" not in a  # the model rejects temperature, so none was sent
    text = exporter_path.read_text()
    for leaked in ("SYSTEM PROMPT", "hello", "secret words"):
        assert leaked not in text


def _fake_http(response):
    calls = []

    def fake(url, body, headers, retries=0):
        calls.append((url, body, headers))
        return response, 1
    return fake, calls


def test_openai_responses_parsing(monkeypatch):
    fake, calls = _fake_http({
        "id": "resp_1", "model": "gpt-5.6-luna", "status": "completed",
        "output": [{"type": "reasoning"},
                   {"type": "function_call", "name": "memory_search", "arguments": "{\"query\": \"Ansel\"}"}],
        "usage": {"input_tokens": 500, "output_tokens": 12, "input_tokens_details": {"cached_tokens": 0},
                  "output_tokens_details": {"reasoning_tokens": 0}},
    })
    monkeypatch.setattr(providers, "_http", fake)
    client = providers.OpenAIChat("gpt-5.6-luna", "sk-test")
    tool = {"type": "function", "function": {"name": "memory_search", "description": "d", "parameters": {}}}
    r = client.chat(ChatRequest("sys", [{"role": "user", "content": "u"}], tool, 0.7, 1, 220, False))
    assert r.tool_calls == [("memory_search", {"query": "Ansel"})]
    assert r.finish_reason == "tool_calls" and r.usage.input_tokens == 500
    url, body, headers = calls[0]
    assert url.endswith("/responses") and "temperature" not in body and "seed" not in body
    assert body["reasoning"] == {"effort": "none"} and body["tools"][0]["name"] == "memory_search"


def test_anthropic_input_tokens_include_cache(monkeypatch):
    fake, _ = _fake_http({
        "id": "msg_1", "model": "claude-sonnet-5", "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "{\"reply\": \"hi\", \"abstained\": false}"}],
        "usage": {"input_tokens": 50, "cache_read_input_tokens": 400, "cache_creation_input_tokens": 0,
                  "output_tokens": 9},
    })
    monkeypatch.setattr(providers, "_http", fake)
    r = providers.AnthropicChat("claude-sonnet-5", "k").chat(
        ChatRequest("sys", [{"role": "user", "content": "u"}], None, 0.7, 1, 220, False))
    assert r.usage.input_tokens == 450 and r.usage.cached_input_tokens == 400
    assert json.loads(r.extra["e2.response.usage_raw"])["input_tokens"] == 50


def test_missing_key_names_the_variable(monkeypatch):
    for v in ("OPENAI_API_KEY", "KODAMA_MODELS__OPENAI_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(providers.MissingKey) as e:
        providers.resolve_key("openai")
    assert "OPENAI_API_KEY" in str(e.value)


def test_key_from_kodama_secrets(tmp_path, monkeypatch):
    for v in ("OPENAI_API_KEY", "KODAMA_MODELS__OPENAI_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    f = tmp_path / "secrets.yaml"
    f.write_text("models:\n  openai_api_key: \"sk-from-file\"\n")
    assert providers.resolve_key("openai", f) == "sk-from-file"
