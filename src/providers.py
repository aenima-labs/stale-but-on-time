"""Model providers for the reference agent, behind one interface.

``ollama`` is the provider of every stored run. ``openai``, ``vertex`` (Gemini
on Vertex AI, through its OpenAI-compatible endpoint) and ``anthropic`` are the
hosted providers Kodama's hosted instances can use (``config/base.yaml`` and
``config/gcp.yaml`` in the Kodama repository: OpenAI for chat and embeddings
on the hosted donor and listener apps).

Every call is traced: one ``chat <model>`` or ``embeddings <model>`` span with
the OpenTelemetry GenAI attributes (provider, model, token counts, finish
reason) and the provider's own timings where it returns them.

Keys are read from the environment (``OPENAI_API_KEY`` or Kodama's
``KODAMA_MODELS__OPENAI_API_KEY``; the same for Anthropic) or, when a path is
given, from Kodama's ``config/secrets.yaml``. Vertex uses Application Default
Credentials, as Kodama does. A key is never printed, logged or put on a span.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from retrieval import EMBED_MODEL, OLLAMA_URL

PROVIDERS = ("ollama", "openai", "vertex", "anthropic")
EMBED_PROVIDERS = ("ollama", "openai")
DEFAULT_MODELS = {
    "ollama": "gemma4:e4b",
    "openai": "gpt-5.6-luna",  # Kodama's hosted default (config/gcp.yaml)
    "vertex": "gemini-3.8-flash",
    "anthropic": "claude-sonnet-5",
}
DEFAULT_EMBED_MODELS = {"ollama": EMBED_MODEL, "openai": "text-embedding-3-small"}
# gen_ai.provider.name values (OpenTelemetry GenAI well-known values where one exists).
SEMCONV_PROVIDER = {
    "ollama": "ollama",
    "openai": "openai",
    "vertex": "gcp.vertex_ai",
    "anthropic": "anthropic",
}
# OpenAI models that reject a temperature field (Kodama: provider/options.go).
OPENAI_FIXED_TEMPERATURE = {"gpt-5.6-luna"}
# Anthropic models that reject a temperature field (HTTP 400 "`temperature` is deprecated").
ANTHROPIC_FIXED_TEMPERATURE = {"claude-sonnet-5"}
KEY_VARIABLES = {
    "openai": ("OPENAI_API_KEY", "KODAMA_MODELS__OPENAI_API_KEY"),
    "anthropic": ("ANTHROPIC_API_KEY", "KODAMA_MODELS__ANTHROPIC_API_KEY"),
}
SECRETS_FIELD = {"openai": "openai_api_key", "anthropic": "anthropic_api_key"}
HOSTED_RETRIES = 2  # as Kodama's llm_retries: retried on 429 and 5xx
HTTP_TIMEOUT_S = 300


class MissingKey(SystemExit):
    pass


class ProviderError(RuntimeError):
    pass


def resolve_key(provider: str, kodama_secrets: Path | None = None) -> str:
    for name in KEY_VARIABLES[provider]:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    if kodama_secrets is not None and kodama_secrets.is_file():
        import yaml

        models = (yaml.safe_load(kodama_secrets.read_text()) or {}).get("models") or {}
        value = str(models.get(SECRETS_FIELD[provider]) or "").strip()
        if value:
            return value
    names = " or ".join(KEY_VARIABLES[provider])
    raise MissingKey(
        f"No API key for {provider}. Set {names} in the environment, or pass "
        f"--kodama-secrets <kodama>/config/secrets.yaml (models.{SECRETS_FIELD[provider]})."
    )


@dataclass
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None


@dataclass
class ChatResult:
    content: str
    tool_calls: list[tuple[str, dict]]  # (name, arguments)
    usage: Usage
    finish_reason: str = ""
    response_model: str = ""
    response_id: str = ""
    extra: dict = field(default_factory=dict)  # provider timings, span attributes
    attempts: int = 1


@dataclass
class ChatRequest:
    system: str
    messages: list[dict]  # [{"role": "user"|"assistant", "content": str}], ends with user
    tool: dict | None  # an Ollama/OpenAI-style function tool, or None for JSON mode
    temperature: float
    seed: int
    max_tokens: int
    think: bool


# ---------------------------------------------------------------- HTTP -----


def _http(url: str, body: dict, headers: dict[str, str], retries: int = 0) -> tuple[dict, int]:
    data = json.dumps(body).encode()
    attempt = 0
    while True:
        attempt += 1
        request = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json", **headers}
        )
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
                return json.loads(response.read()), attempt
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:400].decode("utf-8", "replace")
            if attempt <= retries and (exc.code == 429 or exc.code >= 500):
                time.sleep(2 ** (attempt - 1))
                continue
            raise ProviderError(f"HTTP {exc.code} from {url.split('?')[0]}: {detail}") from None


# --------------------------------------------------------------- chat -----


class ChatClient:
    provider = ""
    model = ""
    server_address = ""

    def chat(self, request: ChatRequest) -> ChatResult:  # pragma: no cover
        raise NotImplementedError

    @property
    def seed_supported(self) -> bool:
        return True

    @property
    def temperature_supported(self) -> bool:
        return True


class OllamaChat(ChatClient):
    provider = "ollama"

    def __init__(self, model: str) -> None:
        self.model = model
        self.server_address = OLLAMA_URL

    def chat(self, request: ChatRequest) -> ChatResult:
        # Exactly the request body of the stored runs (src/subject.py before telemetry).
        body: dict = {
            "model": self.model,
            "stream": False,
            "think": request.think,
            "keep_alive": "30m",
            "options": {
                "temperature": request.temperature,
                "seed": request.seed,
                "num_predict": request.max_tokens,
                "num_ctx": 4096,
            },
            "messages": [{"role": "system", "content": request.system}, *request.messages],
        }
        if request.tool:
            body["tools"] = [request.tool]
        else:
            body["format"] = "json"
        raw, attempts = _http(f"{OLLAMA_URL}/api/chat", body, {})
        message = raw.get("message", {})
        calls = []
        for call in message.get("tool_calls") or []:
            function = call.get("function", {})
            calls.append((function.get("name", ""), function.get("arguments") or {}))
        ns = 1e-6
        extra = {
            f"ollama.{k}_ms": raw[k] * ns
            for k in ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration")
            if isinstance(raw.get(k), int | float)
        }
        return ChatResult(
            content=message.get("content") or "",
            tool_calls=calls,
            usage=Usage(raw.get("prompt_eval_count"), raw.get("eval_count")),
            finish_reason=str(raw.get("done_reason") or ""),
            response_model=str(raw.get("model") or ""),
            extra=extra,
            attempts=attempts,
        )


class OpenAIChat(ChatClient):
    """OpenAI Responses API, as Kodama's hosted LLM slot uses it."""

    provider = "openai"

    def __init__(self, model: str, key: str) -> None:
        self.model = model
        self._key = key
        self.base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.server_address = self.base.split("/")[2]

    @property
    def seed_supported(self) -> bool:
        return False  # the Responses API takes no seed

    @property
    def temperature_supported(self) -> bool:
        return self.model not in OPENAI_FIXED_TEMPERATURE

    def chat(self, request: ChatRequest) -> ChatResult:
        body: dict = {
            "model": self.model,
            # The system prompt is the first input message, as in the Ollama request;
            # JSON mode also requires the word "json" in the input messages.
            "input": [{"role": "system", "content": request.system}, *request.messages],
            "max_output_tokens": request.max_tokens,
            "reasoning": {"effort": "low" if request.think else "none"},
            "store": False,
        }
        if self.temperature_supported:
            body["temperature"] = request.temperature
        if request.tool:
            fn = request.tool["function"]
            body["tools"] = [{"type": "function", "name": fn["name"],
                              "description": fn["description"], "parameters": fn["parameters"]}]
        else:
            body["text"] = {"format": {"type": "json_object"}}
        raw, attempts = _http(
            f"{self.base}/responses", body, {"Authorization": f"Bearer {self._key}"},
            retries=HOSTED_RETRIES,
        )
        text, calls = [], []
        for item in raw.get("output") or []:
            if item.get("type") == "function_call":
                try:
                    args = json.loads(item.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                calls.append((item.get("name", ""), args))
            elif item.get("type") == "message":
                text += [c.get("text", "") for c in item.get("content") or []
                         if c.get("type") == "output_text"]
        usage = raw.get("usage") or {}
        status = raw.get("status", "")
        reason = (raw.get("incomplete_details") or {}).get("reason", "")
        finish = "tool_calls" if calls else ("length" if reason == "max_output_tokens" else
                                             "stop" if status == "completed" else status or reason)
        return ChatResult(
            content="".join(text),
            tool_calls=calls,
            usage=Usage(
                usage.get("input_tokens"),
                usage.get("output_tokens"),
                (usage.get("input_tokens_details") or {}).get("cached_tokens"),
                (usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
            ),
            finish_reason=finish,
            response_model=str(raw.get("model") or ""),
            response_id=str(raw.get("id") or ""),
            extra={"e2.response.usage_raw": json.dumps(usage, sort_keys=True)},
            attempts=attempts,
        )


class _VertexToken:
    """An ADC access token from gcloud, refreshed every 30 minutes."""

    def __init__(self) -> None:
        self._token, self._at = "", 0.0

    def get(self) -> str:
        if not self._token or time.time() - self._at > 1800:
            done = subprocess.run(
                ["gcloud", "auth", "application-default", "print-access-token"],
                capture_output=True, text=True, check=False,
            )
            if done.returncode != 0 or not done.stdout.strip():
                raise MissingKey(
                    "Vertex needs Application Default Credentials: run "
                    "`gcloud auth application-default login` (as for Kodama's Gemini slot)."
                )
            self._token, self._at = done.stdout.strip(), time.time()
        return self._token


class VertexChat(ChatClient):
    """Gemini on Vertex AI through the OpenAI-compatible chat completions endpoint."""

    provider = "vertex"

    def __init__(self, model: str, project: str, location: str = "global") -> None:
        self.model = model
        host = "aiplatform.googleapis.com" if location == "global" else f"{location}-aiplatform.googleapis.com"
        self.base = os.environ.get(
            "VERTEX_OPENAI_BASE_URL",
            f"https://{host}/v1/projects/{project}/locations/{location}/endpoints/openapi",
        ).rstrip("/")
        self.server_address = host
        self._token = _VertexToken()

    def chat(self, request: ChatRequest) -> ChatResult:
        body: dict = {
            "model": self.model if self.model.startswith("google/") else f"google/{self.model}",
            "messages": [{"role": "system", "content": request.system}, *request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "seed": request.seed,
            # Gemini 3 cannot switch reasoning off; "minimal" is the smallest setting.
            "reasoning_effort": "low" if request.think else "minimal",
        }
        if request.tool:
            body["tools"] = [request.tool]
        else:
            body["response_format"] = {"type": "json_object"}
        raw, attempts = _http(
            f"{self.base}/chat/completions", body,
            {"Authorization": f"Bearer {self._token.get()}"}, retries=HOSTED_RETRIES,
        )
        return _parse_chat_completion(raw, attempts)


def _parse_chat_completion(raw: dict, attempts: int) -> ChatResult:
    choice = (raw.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        try:
            args = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        calls.append((function.get("name", ""), args))
    usage = raw.get("usage") or {}
    return ChatResult(
        content=message.get("content") or "",
        tool_calls=calls,
        usage=Usage(
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
            (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
        ),
        finish_reason=str(choice.get("finish_reason") or ""),
        response_model=str(raw.get("model") or ""),
        response_id=str(raw.get("id") or ""),
        extra={"e2.response.usage_raw": json.dumps(usage, sort_keys=True)},
        attempts=attempts,
    )


class AnthropicChat(ChatClient):
    provider = "anthropic"

    def __init__(self, model: str, key: str) -> None:
        self.model = model
        self._key = key
        self.base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
        self.server_address = self.base.split("/")[2]

    @property
    def seed_supported(self) -> bool:
        return False

    @property
    def temperature_supported(self) -> bool:
        return self.model not in ANTHROPIC_FIXED_TEMPERATURE

    def chat(self, request: ChatRequest) -> ChatResult:
        # No JSON mode: the reply format is asked for in the prompt, as for every provider.
        body: dict = {
            "model": self.model,
            "system": request.system,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
        }
        if self.temperature_supported:
            body["temperature"] = request.temperature
        if request.tool:
            fn = request.tool["function"]
            body["tools"] = [{"name": fn["name"], "description": fn["description"],
                              "input_schema": fn["parameters"]}]
        raw, attempts = _http(
            f"{self.base}/v1/messages", body,
            {"x-api-key": self._key, "anthropic-version": "2023-06-01"},
            retries=HOSTED_RETRIES,
        )
        text, calls = [], []
        for block in raw.get("content") or []:
            if block.get("type") == "text":
                text.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                calls.append((block.get("name", ""), block.get("input") or {}))
        usage = raw.get("usage") or {}
        cached = usage.get("cache_read_input_tokens") or 0
        written = usage.get("cache_creation_input_tokens") or 0
        uncached = usage.get("input_tokens")
        return ChatResult(
            content="".join(text),
            tool_calls=calls,
            # Anthropic counts cache reads and writes apart from input_tokens; the
            # GenAI convention's input_tokens includes them, so they are added here.
            usage=Usage(
                None if uncached is None else uncached + cached + written,
                usage.get("output_tokens"),
                cached,
            ),
            extra={"e2.response.usage_raw": json.dumps(usage, sort_keys=True)},
            finish_reason=str(raw.get("stop_reason") or ""),
            response_model=str(raw.get("model") or ""),
            response_id=str(raw.get("id") or ""),
            attempts=attempts,
        )


# ---------------------------------------------------------- embeddings -----


class EmbedClient:
    provider = ""
    model = ""
    last_extra: dict = {}  # provider timings of the last call, put on its span

    def embed(self, inputs: list[str]) -> tuple[np.ndarray, Usage, int]:  # pragma: no cover
        raise NotImplementedError


class OllamaEmbed(EmbedClient):
    provider = "ollama"

    def __init__(self, model: str = EMBED_MODEL) -> None:
        self.model = model

    def embed(self, inputs: list[str]) -> tuple[np.ndarray, Usage, int]:
        raw, attempts = _http(f"{OLLAMA_URL}/api/embed", {"model": self.model, "input": inputs}, {})
        self.last_extra = {
            f"ollama.{k}_ms": raw[k] * 1e-6
            for k in ("total_duration", "load_duration")
            if isinstance(raw.get(k), int | float)
        }
        return np.asarray(raw["embeddings"], dtype=np.float32), Usage(raw.get("prompt_eval_count")), attempts


class OpenAIEmbed(EmbedClient):
    provider = "openai"

    def __init__(self, model: str, key: str) -> None:
        self.model = model
        self._key = key
        self.base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    def embed(self, inputs: list[str]) -> tuple[np.ndarray, Usage, int]:
        raw, attempts = _http(
            f"{self.base}/embeddings", {"model": self.model, "input": inputs},
            {"Authorization": f"Bearer {self._key}"}, retries=HOSTED_RETRIES,
        )
        rows = sorted(raw["data"], key=lambda d: d["index"])
        usage = raw.get("usage") or {}
        return np.asarray([r["embedding"] for r in rows], dtype=np.float32), Usage(usage.get("prompt_tokens")), attempts


# ------------------------------------------------------------- factory -----


def chat_client(provider: str, model: str | None, *, kodama_secrets: Path | None = None,
                vertex_project: str | None = None) -> ChatClient:
    model = model or DEFAULT_MODELS[provider]
    if provider == "ollama":
        return OllamaChat(model)
    if provider == "openai":
        return OpenAIChat(model, resolve_key("openai", kodama_secrets))
    if provider == "anthropic":
        return AnthropicChat(model, resolve_key("anthropic", kodama_secrets))
    if provider == "vertex":
        project = vertex_project or os.environ.get("VERTEX_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise MissingKey("Vertex needs a project: set VERTEX_PROJECT or pass --vertex-project.")
        return VertexChat(model, project)
    raise ValueError(provider)


def embed_client(provider: str, model: str | None = None, *, kodama_secrets: Path | None = None) -> EmbedClient:
    model = model or DEFAULT_EMBED_MODELS[provider]
    if provider == "ollama":
        return OllamaEmbed(model)
    if provider == "openai":
        return OpenAIEmbed(model, resolve_key("openai", kodama_secrets))
    raise ValueError(provider)


# -------------------------------------------------------------- tracing -----


def _set_usage(span: trace.Span, usage: Usage) -> None:
    for name, value in (
        ("gen_ai.usage.input_tokens", usage.input_tokens),
        ("gen_ai.usage.output_tokens", usage.output_tokens),
        ("gen_ai.usage.cache_read.input_tokens", usage.cached_input_tokens),
        ("gen_ai.usage.reasoning.output_tokens", usage.reasoning_tokens),
    ):
        if value is not None:
            span.set_attribute(name, int(value))


def traced_chat(tracer: trace.Tracer, client: ChatClient, request: ChatRequest, purpose: str) -> ChatResult:
    with tracer.start_as_current_span(f"chat {client.model}", kind=SpanKind.CLIENT,
                                      record_exception=True) as span:
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.provider.name", SEMCONV_PROVIDER[client.provider])
        span.set_attribute("gen_ai.request.model", client.model)
        span.set_attribute("gen_ai.request.max_tokens", request.max_tokens)
        if client.temperature_supported:
            span.set_attribute("gen_ai.request.temperature", request.temperature)
        if client.seed_supported:
            span.set_attribute("gen_ai.request.seed", request.seed)
        span.set_attribute("gen_ai.output.type", "text" if request.tool else "json")
        span.set_attribute("server.address", client.server_address.split("//")[-1])
        span.set_attribute("e2.call.purpose", purpose)
        span.set_attribute("e2.call.tools_offered", bool(request.tool))
        span.set_attribute("e2.request.think", request.think)
        try:
            result = client.chat(request)
        except Exception as exc:
            span.set_attribute("error.type", type(exc).__name__)
            span.set_status(Status(StatusCode.ERROR, str(exc)[:200]))
            raise
        _set_usage(span, result.usage)
        if result.finish_reason:
            span.set_attribute("gen_ai.response.finish_reasons", [result.finish_reason])
        if result.response_model:
            span.set_attribute("gen_ai.response.model", result.response_model)
        if result.response_id:
            span.set_attribute("gen_ai.response.id", result.response_id)
        span.set_attribute("e2.http.attempts", result.attempts)
        span.set_attribute("e2.response.tool_calls", len(result.tool_calls))
        for key, value in result.extra.items():
            span.set_attribute(key, value)
        return result


def traced_embed(tracer: trace.Tracer, client: EmbedClient, inputs: list[str], purpose: str) -> np.ndarray:
    with tracer.start_as_current_span(f"embeddings {client.model}", kind=SpanKind.CLIENT,
                                      record_exception=True) as span:
        span.set_attribute("gen_ai.operation.name", "embeddings")
        span.set_attribute("gen_ai.provider.name", SEMCONV_PROVIDER[client.provider])
        span.set_attribute("gen_ai.request.model", client.model)
        span.set_attribute("e2.call.purpose", purpose)
        span.set_attribute("e2.embeddings.inputs", len(inputs))
        try:
            vectors, usage, attempts = client.embed(inputs)
        except Exception as exc:
            span.set_attribute("error.type", type(exc).__name__)
            span.set_status(Status(StatusCode.ERROR, str(exc)[:200]))
            raise
        _set_usage(span, usage)
        for key, value in client.last_extra.items():
            span.set_attribute(key, value)
        span.set_attribute("gen_ai.embeddings.dimension.count", int(vectors.shape[1]))
        span.set_attribute("e2.http.attempts", attempts)
        return vectors


# ------------------------------------------------------- Ollama residency -----

RELOAD_MS = 1000.0  # a call whose ollama.load_duration_ms exceeds this loaded a model


def ollama_preflight(chat_model: str | None, embed_model: str | None) -> list[str]:
    """Load the run's Ollama models as a run would and report any not resident after.

    The stored runs had the chat and embedding models loaded side by side for the
    whole run. When the machine has too little free memory, Ollama evicts one to
    load the other on every call, and each call then includes a model load.
    Returns the models that were not resident (empty when all are).
    """
    if chat_model:
        _http(f"{OLLAMA_URL}/api/chat", {
            "model": chat_model, "stream": False, "keep_alive": "30m", "think": False,
            "options": {"num_ctx": 4096, "num_predict": 1},
            "messages": [{"role": "user", "content": "hi"}],
        }, {})
    if embed_model:
        _http(f"{OLLAMA_URL}/api/embed", {"model": embed_model, "input": ["hi"], "keep_alive": "30m"}, {})
    request = urllib.request.Request(f"{OLLAMA_URL}/api/ps")
    with urllib.request.urlopen(request, timeout=30) as response:
        loaded = {m["name"] for m in json.loads(response.read()).get("models", [])}
    wanted = [m for m in (chat_model, embed_model) if m]
    return [m for m in wanted if m not in loaded and f"{m}:latest" not in loaded]
