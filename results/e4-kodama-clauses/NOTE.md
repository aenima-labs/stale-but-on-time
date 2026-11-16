# Clause speech on Kodama (voice, exploratory)

Kodama development runs, not yet a paper experiment. They test the presence
setting `speech.clauses` (Kodama branch `w003-backthought-recall`, commit
`3a90b05`): with it on, a voice reply's first sentence is spoken as soon as it
has passed the output checks, while the rest is written and checked whole.

- `off/`: speech.clauses off, the shipped way of speaking a reply.
- `on/`: speech.clauses on.
- Conditions c-blocking and d-blocking-backthought, the voice pack (40 cases,
  one trial each), run in the order c off, c on, d off, d on.
- Local Ollama with `OLLAMA_NUM_PARALLEL=3` (three requests served at once),
  gemma4:e4b and nomic-embed-text, flash attention, q8_0 KV cache. The earlier
  voice runs in `e3-kodama-voice/` used one slot, so their timings are not
  comparable with these; compare `off/` with `on/`.
- Ran 2026-11-12 17:35–18:18 UTC (c off 17:35–17:46, c on 17:46–17:57,
  d off 17:57–18:07, d on 18:07–18:18); each `condition.json` has the exact
  times. 0 errors; all four bundles sealed. Ollama was set back to one slot
  at 18:18 UTC.

## Result: no measurable gain

| condition | clauses | recall pass | first audio median / p90 | on time to 10 s | time to answer median |
|---|---|---|---|---|---|
| c-blocking | off | 73% [57, 87] | 6.85 / 7.78 s | 0.10 [0.06, 0.15] | 8.7 s |
| c-blocking | on | 63% [47, 80] | 6.81 / 8.79 s | 0.09 [0.05, 0.14] | 8.5 s |
| d-blocking-backthought | off | 70% [53, 87] | 6.55 / 7.52 s | 0.11 [0.07, 0.15] | 8.6 s |
| d-blocking-backthought | on | 70% [53, 87] | 6.58 / 7.26 s | 0.11 [0.06, 0.16] | 8.9 s |

- **The first sentence went early in 8 of 40 trials (c) and 15 of 40 (d).** In
  the rest the reply had no sentence of at least 40 characters before its end
  (most gemma4 replies here are one sentence), or there was no reply.
- **Early or not, first audio did not move.** Against the same case with
  clauses off: c +0.1 s median, d 0.0 s. The first sentence's checks took
  2.1–3.0 s, and the model writes the rest of a reply in about 0.5 s after it,
  so first audio waits on the checks either way.
- **Nothing was withheld** (0 of 80): no reply was changed by the whole-reply
  checks after its first sentence was spoken.
- **c's recall pass difference (73% vs 63%) is within the intervals.** Six
  cases changed in each direction or by templating. With three slots Ollama
  batches requests, so replies are not reproducible.
- **One reply in c-on was empty:** the model generated 582 tokens of which
  Ollama passed on no text or tool call. Kodama sends Ollama the same request
  with clauses on or off; it did not recur in d.
- **Three slots alone** gave first audio of 6.85 s (c) and 6.55 s (d), against
  7.6 s and 7.2 s with one slot in `e3-kodama-voice/` the day before. That is
  mostly the advice check running beside the reply instead of before it. The
  comparison is across days.
