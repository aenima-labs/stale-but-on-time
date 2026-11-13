# Estimate: `e2-smoke`

- Chat model: ollama/gemma4:e4b; embeddings: ollama/nomic-embed-text
- Trials: 20 in 2 condition(s)
- Profile: sealed bundles of results/e2 (prompts rebuilt, tokens = characters / 4)
- Prices on 2026-11-13: chat $0.0/$0.0 per M in/out (local inference, no per-token charge, read 2026-11-13)

Expected [low–high]. The high end of a wide range is a ceiling, not a likely value.

| condition | trials | model calls | tokens in | tokens out | embed tokens | model spend | duration |
|---|---:|---:|---:|---:|---:|---:|---:|
| blocking | 10 | 10 [10–10] | 3,790 [2,843–5,041] | 253 [126–2,200] | 475 [356–632] | $0.0000 [$0.0000–$0.0000] | 0 min [0 min–0 min] |
| tool | 10 | 20 [10–20] | 7,155 [2,696–9,563] | 428 [214–4,400] | 84 [63–113] | $0.0000 [$0.0000–$0.0000] | 0 min [0 min–0 min] |
| **total** | 20 | 30 [20–30] | 10,945 [5,539–14,604] | 681 [340–6,600] | 4,459 [4,319–4,645] | $0.0000 [$0.0000–$0.0000] | 0 min [0 min–1 min] |

**No spend** (local models, local machine).

Notes:
- The profile (sealed bundles of results/e2 (prompts rebuilt, tokens = characters / 4); ollama/gemma4:e4b) is not a measured profile of ollama/gemma4:e4b: the range is wide and its top assumes every trial makes the most calls its condition allows and every call writes all 220 output tokens.
