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
import urllib.request
from collections.abc import Sequence
from pathlib import Path

import numpy as np

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
from retrieval import BM25, EMBED_MODEL, OLLAMA_URL, as_document, as_query, rrf_topk, tokenize

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


def _post(path: str, body: dict) -> dict:
    request = urllib.request.Request(
        f"{OLLAMA_URL}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read())


class Memorome:
    """One person's notes and the retriever over them.

    "Memorome" is the term of Xiao et al. (2026), "Memory is Not Search", Section 2,
    for the whole collection of one person's memories.
    """

    def __init__(self, name: str) -> None:
        data = json.loads((ROOT / "fixtures" / f"{name}.json").read_text())
        self.persona: dict[str, str] = data["persona"]
        self.ids = list(data["memorome"])
        self.texts = [data["memorome"][i] for i in self.ids]
        self.bm25 = BM25([tokenize(t) for t in self.texts])
        self.dense = self._embed([as_document(t) for t in self.texts])

    @staticmethod
    def _embed(inputs: list[str]) -> np.ndarray:
        vectors = np.asarray(
            _post("/api/embed", {"model": EMBED_MODEL, "input": inputs})["embeddings"],
            dtype=np.float32,
        )
        return vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12)

    def recall(self, query: str) -> list[str]:
        """Hybrid top-k page ids. The query embedding is computed live."""
        q = self._embed([as_query(query)])[0]
        top = rrf_topk(self.bm25.scores(tokenize(query)), self.dense @ q, TOP_K)
        return [self.ids[i] for i in top]

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
    def __init__(self, subject: RecallSubject, trial: TrialSpec) -> None:
        self.subject = subject
        self.trial = trial
        config = trial.case.fixture.config
        self.memorome = subject.memorome(str(config["memorome"]))
        self.history = [dict(turn) for turn in config["history"]]  # type: ignore[arg-type]

    def _chat(self, system: str, user: str, *, tools: bool = False) -> tuple[dict, str | None]:
        """One model call. Returns the parsed reply object and, if the model
        called ``memory_search`` instead of replying, the search query."""
        body: dict = {
            "model": self.subject.model,
            "stream": False,
            # The model's reasoning mode would otherwise spend the whole token
            # budget before any reply; a voice turn has no time for it.
            "think": self.subject.think,
            "keep_alive": "30m",
            "options": {
                "temperature": self.subject.temperature,
                "seed": self.trial.seed % (2**31),
                # Reasoning tokens count against the budget, so it is larger there.
                "num_predict": 2048 if self.subject.think else 220,
                "num_ctx": 4096,
            },
            "messages": [
                {"role": "system", "content": system},
                *self.history,
                {"role": "user", "content": user},
            ],
        }
        if tools:
            body["tools"] = [SEARCH_TOOL]  # native tool calling; no JSON mode
        else:
            body["format"] = "json"
        message = _post("/api/chat", body).get("message", {})
        for call in message.get("tool_calls") or []:
            function = call.get("function", {})
            query = function.get("arguments", {}).get("query")
            if function.get("name") == "memory_search" and isinstance(query, str) and query.strip():
                return {}, query
        content = (message.get("content") or "").strip()
        start, end = content.find("{"), content.rfind("}")
        try:
            parsed = json.loads(content[start : end + 1]) if start >= 0 else {}
        except json.JSONDecodeError:
            parsed = {}
        if not isinstance(parsed, dict) or not isinstance(parsed.get("reply"), str):
            parsed = {"reply": content}  # spoken text without the required wrapper
        return parsed, None

    def _run(self, user: str) -> list[Event]:
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
                pages = self.memorome.recall(ambience(said))
                based_on = "ambience up to the previous agent reply"
            else:
                pages = self.memorome.recall(ambience([*said, first_half(user)]))
                based_on = "ambience plus the first half of the incoming utterance"
            offpath_ms = (time.perf_counter() - started) * 1000

        # ---- reply path starts: the listener has finished speaking ----------
        path_started = time.perf_counter()
        llm_calls = 1
        if condition == "blocking":
            pages = self.memorome.recall(ambience([*said, user]))
            based_on = "ambience including the incoming utterance"
        elif condition in ("tool", "hybrid"):
            offer = (
                NO_MEMORIES_SEARCH
                if condition == "tool"
                else self.memorome.block(pages) + "\n\n" + STALE_MEMORIES_SEARCH
            )
            direct, query = self._chat(
                rules + "\n" + offer + "\n\n" + REPLY_FORMAT, user, tools=True
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
            else:
                found = self.memorome.recall(query)
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

    async def execute(self, action: Action, *, timeout_s: float) -> Sequence[Event]:
        del timeout_s
        if not isinstance(action, MessageAction):
            raise TypeError(f"unsupported action: {type(action)!r}")
        return await asyncio.to_thread(self._run, action.content)

    async def close(self) -> None:
        return None


class RecallSubject:
    def __init__(
        self,
        condition: str,
        model: str = "gemma4:e4b",
        temperature: float = 0.7,
        think: bool = False,
    ) -> None:
        if condition not in CONDITIONS:
            raise ValueError(condition)
        self.condition = condition
        self.model = model
        self.temperature = temperature
        self.think = think
        self._memoromes: dict[str, Memorome] = {}
        self.descriptor = PluginDescriptor(
            id=f"async-recall-ref.{condition}",
            version="1",
            capabilities=["message.text"],
            models={"chat": model, "embed": EMBED_MODEL},
        )

    def memorome(self, name: str) -> Memorome:
        if name not in self._memoromes:
            self._memoromes[name] = Memorome(name)
        return self._memoromes[name]

    async def prepare(self, trial: TrialSpec) -> RecallSession:
        return RecallSession(self, trial)
