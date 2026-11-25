"""The deeper recall step, the clock rule and the agents of the experiment with slow recall."""

import hashlib
import json
from types import SimpleNamespace

import numpy as np
from opentelemetry import trace

import providers
import subject as s


class FakeEmbed(providers.EmbedClient):
    """Bag-of-words vectors, so that the cheap lookup ranks by shared words."""

    provider = "ollama"
    model = "fake-embed"

    def embed(self, inputs):
        out = np.zeros((len(inputs), 256), dtype=np.float32)
        for row, text in enumerate(inputs):
            for word in s.tokenize(text):
                out[row, int(hashlib.sha1(word.encode()).hexdigest(), 16) % 256] += 1.0
        return out, providers.Usage(0, 0), 1


class FakeChat(providers.ChatClient):
    """Rates a note 3 if it contains one of ``wanted``, else 0; replies with a fixed sentence."""

    provider = "ollama"
    model = "fake-chat"

    def __init__(self, wanted):
        self.wanted = wanted
        self.judge_requests = []
        self.reply_systems = []

    def chat(self, request):
        if request.system.startswith("You select memories"):
            self.judge_requests.append(request)
            note = request.messages[0]["content"].split("NOTE\n")[1]
            content = json.dumps({"score": 3 if any(w in note for w in self.wanted) else 0})
        else:
            self.reply_systems.append(request.system)
            content = json.dumps({"reply": "Here is what I know.", "abstained": False})
        return providers.ChatResult(content=content, tool_calls=[], usage=providers.Usage(1, 1))


LEAD_IN = [
    {"role": "user", "content": "Grandma kept bees, didn't she?"},
    {"role": "assistant", "content": "She did, for many years, at the end of the garden."},
]
LAST = "On another note, who did she play chess with?"


def run(condition, wanted):
    chat = FakeChat(wanted)
    subj = s.RecallSubject(condition, chat_client=chat, embed_client=FakeEmbed())
    trial = SimpleNamespace(
        seed=7,
        case=SimpleNamespace(fixture=SimpleNamespace(config={"memorome": "tessaly-v1", "history": LEAD_IN})),
    )
    session = s.RecallSession(subj, trial, trace.INVALID_SPAN)
    events = session._turn(LAST)
    recall = [e.components["recall"] for e in events if e.kind == "context_snapshot"][-1]
    obs = {e.name: e.value for e in events if e.kind == "observation"}
    met = {e.name: e.value for e in events if e.kind == "metric"}
    return recall, obs, met, chat


# ---------------------------------------------------------------- pure parts
def test_select_rated_takes_the_best_four_at_or_above_the_threshold():
    pages = ["a", "b", "c", "d", "e", "f"]
    assert s.select_rated(pages, [1, 2, 3, 2, 3, 2]) == ["c", "e", "b", "d"]
    assert s.select_rated(pages, [1, 0, 1, 1, 0, 1]) == []


def test_speaking_time_follows_the_word_count():
    assert s.speaking_ms(" ".join(["word"] * 7)) == 2000.0  # 7 words at 210 a minute


# ---------------------------------------------------------------- the agents
def test_deep_recall_rates_sixteen_notes_and_loads_the_rated_ones():
    recall, obs, met, chat = run("deep", wanted=["Mr Okafor"])
    assert recall == ["g-chess"]
    assert len(chat.judge_requests) == s.CANDIDATES == 16
    assert met["path.llm_calls"] == 17  # sixteen ratings and the reply, all on the reply path
    assert obs["recall.rated"]["selected"] == ["g-chess"]
    # every rating sees the whole conversation, the last utterance included
    assert LAST in chat.judge_requests[0].messages[0]["content"]


def test_deep_recall_is_not_sampled():
    _, _, _, chat = run("deep", wanted=[])
    assert {r.temperature for r in chat.judge_requests} == {0.0}
    assert not any(r.think for r in chat.judge_requests)


def test_stale_deep_recall_sees_only_the_lead_in_and_stays_off_the_reply_path():
    recall, obs, met, chat = run("deep_stale", wanted=["six hives"])
    assert recall == ["b-bees"]
    assert obs["recall.ready"] is True
    assert met["path.llm_calls"] == 1 and met["recall.judge_calls"] == 16
    assert all(LAST not in r.messages[0]["content"] for r in chat.judge_requests)
    assert met["offpath.available_ms"] == s.speaking_ms(LEAD_IN[1]["content"]) + s.speaking_ms(LAST)


def test_a_record_that_is_not_ready_is_not_loaded(monkeypatch):
    monkeypatch.setattr(s, "speaking_ms", lambda text: 0.0)  # the conversation gave the job no time
    recall, obs, _, chat = run("deep_stale", wanted=["six hives"])
    assert recall == []
    assert obs["recall.ready"] is False
    assert obs["recall.rated"]["selected"] == ["b-bees"]  # what the job would have delivered
    assert "no memories are loaded" in chat.reply_systems[-1]


def test_both_puts_the_fresh_lookup_first_and_adds_the_stale_record():
    fresh, _, _, _ = run("blocking", wanted=[])
    recall, _, met, _ = run("both", wanted=["six hives", "second prize"])
    assert recall[: len(fresh)] == fresh  # the cheap lookup on the whole conversation
    assert set(recall) >= {"b-bees", "b-honey"} and len(recall) == len(set(recall))
    assert met["path.llm_calls"] == 1


def test_the_new_conditions_do_not_change_the_old_ones():
    assert s.CONDITIONS == ("none", "tool", "blocking", "lag1", "prefetch50", "hybrid")
    assert s.ALL_CONDITIONS == s.CONDITIONS + ("deep", "deep_stale", "both")
