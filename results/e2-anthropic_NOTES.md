# e2-anthropic: Experiment 2 with a hosted chat model and hosted embeddings

The full Experiment 2 (six conditions, 40 cases, 5 trials each, 1,200 trials)
with the reference agent's model calls sent to hosted providers, on the same
laptop as the other runs: chat `claude-sonnet-5` (Anthropic), embeddings
`text-embedding-3-small` (OpenAI), as Kodama's hosted instances use hosted
models. 2026-11-13 15:18:46–16:10:31 UTC, commit `70ccc8b`.

```bash
uv run inv e2.run --args="--provider anthropic --embed-provider openai \
  --kodama-secrets <kodama>/config/secrets.yaml --profile e2-anthropic-pilot --out results/e2-anthropic"
```

Cost: **$3.47** from the run's telemetry (`telemetry_summary.md`, prices in
`pricing/prices.yaml` read 2026-11-13), against an estimate of $3.29
[$2.96–$3.62] made from the 60-trial pilot `results/e2-anthropic-pilot`
($0.16; `estimate_vs_actual.md`). 1,580 model calls, 977,655 input and
150,977 output tokens, 42,437 embedding tokens. All six bundles verify.

Identical to the main run: pack, cases, prompts, retriever (BM25 + dense with
reciprocal rank fusion, top 4), conditions, grading, trial seeds (recorded).

Different from the main run (disclose if reported):
- The model and its provider; replies are generated remotely, so latencies
  include the network round trip to Anthropic (and to OpenAI for every
  embedding: recall on the reply path pays it, ~0.3 s median).
- No temperature is sent: Claude 5.x models refuse it (HTTP 400, checked
  2026-11-13); the provider's default applies. The main run used 0.7.
- No seed is sent: no Claude model accepts one. Trials are not reproducible.
- No JSON mode: Anthropic has none; the reply format comes from the prompt
  only (`reply.format_ok` records whether the model followed it).
- The dense half of the retriever uses `text-embedding-3-small` (1,536-d)
  instead of `nomic-embed-text` (768-d), so retrieved pages can differ.
- Hosted calls are retried on HTTP 429 and 5xx (up to 2 retries, as Kodama);
  `e2.http.attempts` on each span records it.

Spans: `telemetry/<condition>.spans.jsonl` (one trace per trial; exact token
counts from the provider's usage fields; no prompt, reply or key recorded).
