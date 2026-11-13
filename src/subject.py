"""Reference subject: one conversational agent, five ways to give it memory.

Conditions
  none        no memories are loaded
  tool        agentic search: the model may call ``memory_search`` first
  blocking    retrieve from the ambience including the incoming utterance,
              on the reply path, before the model is called
  lag1        asynchronous: read a blackboard record computed from the
              ambience up to the agent's previous reply (never waits)
  prefetch50  asynchronous: the record was computed from the ambience plus
              the first half of the incoming utterance (streaming transcript)
  hybrid      lag1, and the model may still call ``memory_search`` when the
              loaded memories do not cover the turn

The agent, prompt, retriever, top-k and decoding settings are identical in
every condition; only where the MEMORIES block comes from differs.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

from circumstances.models import (
    Action,
    ContextSnapshotEvent,
    Event,
    MessageAction,
    MessageEvent,
    MetricEvent,
    ObservationEvent,
    PluginDescriptor,
    ToolCallEvent,
    ToolResultEvent,
    TrialSpec,
)
from providers import (
    SEMCONV_PROVIDER,
    ChatClient,
    ChatRequest,
    EmbedClient,
    OllamaChat,
    OllamaEmbed,
    traced_chat,
    traced_embed,
)
from retrieval import BM25, as_document, as_query, rrf_topk, tokenize

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("none", "tool", "blocking", "lag1", "prefetch50", "hybrid")
WINDOW = 3
TOP_K = 4

RULES = """You are Kodama, a voice companion that keeps the stories of {name} ({lifespan}) and speaks about her with her family. You are talking with {listener}.

Rules:
- Reply in one to three short spoken sentences.
- State facts about Tessaly, her family and her life only if they appear under MEMORIES or earlier in this conversation. Never guess and never infer a missing fact.
- If the listener asks for something the memories do not contain, say plainly that you do not know, and set "abstained" to true.
- If a memory is relevant to what the listener just said, bring it up, even if they did not ask.
"""
REPLY_FORMAT = 'Answer with one JSON object: {"reply": "<what you say aloud>", "abstained": <true or false>}'
NO_MEMORIES_SEARCH = (
    "MEMORIES\nNo memories are loaded yet. Use the memory_search tool whenever a memory "
    "could be relevant to what the listener just said, and always before saying that "
    "you do not know."
)
STALE_MEMORIES_SEARCH = (
    "If these memories do not cover what the listener just said, use the memory_search "
    "tool before you answer, and always before saying that you do not know."
)
SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "memory_search",
        "description": "Search Tessaly's memories. Returns the most relevant memory notes.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "what to look for"}},
            "required": ["query"],
        },
    },
}


class Memorome:
    def __init__(self, name: str, embedder: EmbedClient, tracer: trace.Tracer) -> None:
        data = json.loads((ROOT / "fixtures" / f"{name}.json").read_text())
        self.persona: dict[str, str] = data["persona"]
        self.ids = list(data["memorome"])
        self.texts = [data["memorome"][i] for i in self.ids]
        self.embedder = embedder
        self.tracer = tracer
        self.bm25 = BM25([tokenize(t) for t in self.texts])
        self.dense = self._embed([as_document(t) for t in self.texts], "index")

    def _embed(self, inputs: list[str], purpose: str) -> np.ndarray:
        vectors = traced_embed(self.tracer, self.embedder, inputs, purpose)
        return vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12)

    def recall(self, query: str, placement: str) -> list[str]:
        """Hybrid top-k page ids. The query embedding is computed live."""
        with self.tracer.start_as_current_span("memory.recall") as span:
            span.set_attribute("e2.recall.placement", placement)
            span.set_attribute("e2.recall.top_k", TOP_K)
            q = self._embed([as_query(query)], "query")[0]
            top = rrf_topk(self.bm25.scores(tokenize(query)), self.dense @ q, TOP_K)
            pages = [self.ids[i] for i in top]
            span.set_attribute("e2.recall.page_ids", pages)
            return pages

    def block(self, page_ids: list[str]) -> str:
        if not page_ids:
            return "MEMORIES\n(no memories are loaded for this turn)"
        lines = [f"- {self.texts[self.ids.index(i)]}" for i in page_ids]
        return "MEMORIES\n" + "\n".join(lines)


def ambience(utterances: list[str]) -> str:
    return " ".join(utterances[-WINDOW:])


def first_half(text: str) -> str:
    words = text.split()
    return " ".join(words[: max(1, math.ceil(len(words) / 2))])


class RecallSession:
    def __init__(self, subject: RecallSubject, trial: TrialSpec, span: trace.Span) -> None:
        self.subject = subject
        self.trial = trial
        self.span = span  # the trial span; every call of this trial is its child
        config = trial.case.fixture.config
        with trace.use_span(span, end_on_exit=False):
            self.memorome = subject.memorome(str(config["memorome"]))
        self.history = [dict(turn) for turn in config["history"]]  # type: ignore[arg-type]

    def _chat(
        self, system: str, user: str, *, tools: bool = False, purpose: str = "reply"
    ) -> tuple[dict, str | None]:
        """One model call. Returns the parsed reply object and, if the model
        called ``memory_search`` instead of replying, the search query."""
        request = ChatRequest(
            system=system,
            messages=[*self.history, {"role": "user", "content": user}],
            # Native tool calling when the tool is offered; JSON mode otherwise.
            tool=SEARCH_TOOL if tools else None,
            temperature=self.subject.temperature,
            seed=self.trial.seed % (2**31),
            # The model's reasoning mode would otherwise spend the whole token
            # budget before any reply; a voice turn has no time for it.
            # Reasoning tokens count against the budget, so it is larger there.
            max_tokens=2048 if self.subject.think else 220,
            think=self.subject.think,
        )
        result = traced_chat(self.subject.tracer, self.subject.chat_client, request, purpose)
        for name, arguments in result.tool_calls:
            query = arguments.get("query") if isinstance(arguments, dict) else None
            if name == "memory_search" and isinstance(query, str) and query.strip():
                return {}, query
        content = result.content.strip()
        start, end = content.find("{"), content.rfind("}")
        try:
            parsed = json.loads(content[start : end + 1]) if start >= 0 else {}
        except json.JSONDecodeError:
            parsed = {}
        if not isinstance(parsed, dict) or not isinstance(parsed.get("reply"), str):
            parsed = {"reply": content}  # spoken text without the required wrapper
        return parsed, None

    def _turn(self, user: str) -> list[Event]:
        condition = self.subject.condition
        rules = RULES.format(**self.memorome.persona)
        said = [turn["content"] for turn in self.history]
        events: list[Event] = [MessageEvent(sequence=0, role="user", content=user)]
        offpath_ms = 0.0
        pages: list[str] = []
        based_on = "nothing"

        # Work done before the listener finished speaking is off the reply path.
        if condition in ("lag1", "prefetch50", "hybrid"):
            started = time.perf_counter()
            if condition in ("lag1", "hybrid"):
                pages = self.memorome.recall(ambience(said), "off_path")
                based_on = "ambience up to the previous agent reply"
            else:
                pages = self.memorome.recall(
                    ambience([*said, first_half(user)]), "off_path"
                )
                based_on = "ambience plus the first half of the incoming utterance"
            offpath_ms = (time.perf_counter() - started) * 1000

        # ---- reply path starts: the listener has finished speaking ----------
        tracer = self.subject.tracer
        with tracer.start_as_current_span("reply_path") as path_span:
            path_started = time.perf_counter()
            llm_calls = 1
            if condition == "blocking":
                pages = self.memorome.recall(ambience([*said, user]), "reply_path")
                based_on = "ambience including the incoming utterance"
            elif condition in ("tool", "hybrid"):
                offer = (
                    NO_MEMORIES_SEARCH
                    if condition == "tool"
                    else self.memorome.block(pages) + "\n\n" + STALE_MEMORIES_SEARCH
                )
                direct, query = self._chat(
                    rules + "\n" + offer + "\n\n" + REPLY_FORMAT, user, tools=True,
                    purpose="tool_offer",
                )
                if query is None and isinstance(direct.get("abstained"), bool):
                    # The model answered without searching; that answer is the reply.
                    total_ms = (time.perf_counter() - path_started) * 1000
                    return self._finish(events, direct, pages, based_on, 0.0, total_ms, offpath_ms, 1)
                llm_calls = 2
                if query is None:
                    # No search and no well-formed reply (tool mode cannot enforce
                    # JSON). Ask again in JSON mode; the wasted call stays on the path.
                    events.append(ObservationEvent(sequence=0, name="reply.repaired", value=True))
                    path_span.set_attribute("e2.reply.repaired", True)
                else:
                    with tracer.start_as_current_span("execute_tool memory_search") as tool_span:
                        tool_span.set_attribute("gen_ai.operation.name", "execute_tool")
                        tool_span.set_attribute("gen_ai.tool.name", "memory_search")
                        tool_span.set_attribute("gen_ai.tool.type", "function")
                        tool_span.set_attribute("gen_ai.tool.call.id", "search-1")
                        found = self.memorome.recall(query, "tool")
                    # Search results come first; blackboard pages are kept after them.
                    pages = found + [p for p in pages if p not in found]
                    based_on = "model-written search query"
                    events.append(
                        ToolCallEvent(
                            sequence=0, call_id="search-1", name="memory_search",
                            arguments={"query": query},
                        )
                    )
                    events.append(
                        ToolResultEvent(
                            sequence=0, call_id="search-1", name="memory_search", output=found
                        )
                    )

            pre_generation_ms = (time.perf_counter() - path_started) * 1000
            answer, _ = self._chat(
                rules + "\n" + self.memorome.block(pages) + "\n\n" + REPLY_FORMAT, user
            )
            total_ms = (time.perf_counter() - path_started) * 1000
            return self._finish(
                events, answer, pages, based_on, pre_generation_ms, total_ms, offpath_ms, llm_calls
            )

    @staticmethod
    def _finish(
        events: list[Event],
        answer: dict,
        pages: list[str],
        based_on: str,
        pre_generation_ms: float,
        total_ms: float,
        offpath_ms: float,
        llm_calls: int,
    ) -> list[Event]:
        reply = answer.get("reply")
        format_ok = isinstance(reply, str) and isinstance(answer.get("abstained"), bool)
        events.append(
            ContextSnapshotEvent(sequence=0, components={"recall": pages, "based_on": based_on})
        )
        events.append(
            MessageEvent(sequence=0, role="assistant", content=reply if isinstance(reply, str) else "")
        )
        events.append(
            ObservationEvent(sequence=0, name="reply.abstained", value=answer.get("abstained") is True)
        )
        events.append(ObservationEvent(sequence=0, name="reply.format_ok", value=format_ok))
        for name, value, unit in (
            ("path.pre_generation_ms", pre_generation_ms, "ms"),
            ("path.total_ms", total_ms, "ms"),
            ("offpath.recall_ms", offpath_ms, "ms"),
            ("path.llm_calls", float(llm_calls), "count"),
        ):
            events.append(MetricEvent(sequence=0, name=name, value=value, unit=unit))
        return events

    def _run(self, user: str) -> list[Event]:
        """One turn inside the trial span. Outcome metrics are copied onto the span."""
        with trace.use_span(self.span, end_on_exit=False, record_exception=False):
            try:
                events = self._turn(user)
            except Exception as exc:
                self.span.record_exception(exc)
                self.span.set_attribute("error.type", type(exc).__name__)
                self.span.set_status(Status(StatusCode.ERROR, str(exc)[:200]))
                raise
        for event in events:
            if isinstance(event, MetricEvent):
                self.span.set_attribute(f"e2.{event.name}", event.value)
            elif isinstance(event, ObservationEvent) and isinstance(event.value, bool):
                self.span.set_attribute(f"e2.{event.name}", event.value)
        return events

    async def execute(self, action: Action, *, timeout_s: float) -> Sequence[Event]:
        del timeout_s
        if not isinstance(action, MessageAction):
            raise TypeError(f"unsupported action: {type(action)!r}")
        return await asyncio.to_thread(self._run, action.content)

    async def close(self) -> None:
        self.span.end()


class RecallSubject:
    def __init__(
        self,
        condition: str,
        model: str = "gemma4:e4b",
        temperature: float = 0.7,
        think: bool = False,
        *,
        chat_client: ChatClient | None = None,
        embed_client: EmbedClient | None = None,
        tracer: trace.Tracer | None = None,
    ) -> None:
        if condition not in CONDITIONS:
            raise ValueError(condition)
        self.condition = condition
        self.chat_client = chat_client or OllamaChat(model)
        self.embed_client = embed_client or OllamaEmbed()
        self.model = self.chat_client.model
        self.temperature = temperature
        self.think = think
        self.tracer = tracer or trace.NoOpTracer()
        self._memoromes: dict[str, Memorome] = {}
        models = {"chat": self.model, "embed": self.embed_client.model}
        if self.chat_client.provider != "ollama" or self.embed_client.provider != "ollama":
            # Recorded in the bundle lock only for hosted runs, so a local run's
            # descriptor is the same as in the stored bundles.
            models["chat_provider"] = self.chat_client.provider
            models["embed_provider"] = self.embed_client.provider
        self.descriptor = PluginDescriptor(
            id=f"async-recall-ref.{condition}",
            version="1",
            capabilities=["message.text"],
            models=models,
        )

    def memorome(self, name: str) -> Memorome:
        if name not in self._memoromes:
            self._memoromes[name] = Memorome(name, self.embed_client, self.tracer)
        return self._memoromes[name]

    async def prepare(self, trial: TrialSpec) -> RecallSession:
        span = self.tracer.start_span(
            "trial",
            kind=SpanKind.INTERNAL,
            context=trace.set_span_in_context(trace.INVALID_SPAN),  # a new trace per trial
            attributes={
                "e2.condition": self.condition,
                "circumstances.run_id": trial.run_id,
                "circumstances.trial_id": trial.trial_id,
                "circumstances.case_id": trial.case.id,
                "circumstances.trial.attempt": trial.attempt,
                "circumstances.trial.seed": trial.seed,
                "gen_ai.provider.name": SEMCONV_PROVIDER[self.chat_client.provider],
                "gen_ai.request.model": self.model,
                "e2.embed.provider": self.embed_client.provider,
                "e2.embed.model": self.embed_client.model,
            },
        )
        try:
            return RecallSession(self, trial, span)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)[:200]))
            span.end()
            raise
