# Estimate: `e2-anthropic-pilot`

- Chat model: anthropic/claude-sonnet-5; embeddings: openai/text-embedding-3-small
- Trials: 60 in 6 condition(s)
- Profile: sealed bundles of results/e2 (prompts rebuilt; input tokens counted by anthropic/claude-sonnet-5, output tokens = characters / 4)
- Prices on 2026-11-13: chat $2.0/$10.0 per M in/out (https://platform.claude.com/docs/en/about-claude/pricing, read 2026-11-13)

Expected [low–high]. The high end of a wide range is a ceiling, not a likely value.

| condition | trials | model calls | tokens in | tokens out | embed tokens | model spend | duration |
|---|---:|---:|---:|---:|---:|---:|---:|
| none | 10 | 10 [10–10] | 3,307 [3,142–3,472] | 163 [81–2,200] | 0 [0–0] | $0.0082 [$0.0071–$0.0289] | 12 s [5 s–30 s] |
| tool | 10 | 20 [10–20] | 13,493 [6,442–14,239] | 428 [214–4,400] | 84 [63–113] | $0.0313 [$0.0150–$0.0725] | 25 s [6 s–62 s] |
| blocking | 10 | 10 [10–10] | 5,300 [5,035–5,565] | 253 [126–2,200] | 475 [356–632] | $0.0131 [$0.0113–$0.0331] | 14 s [6 s–32 s] |
| lag1 | 10 | 10 [10–10] | 5,287 [5,023–5,552] | 191 [95–2,200] | 332 [249–442] | $0.0125 [$0.0110–$0.0331] | 14 s [6 s–32 s] |
| prefetch50 | 10 | 10 [10–10] | 5,273 [5,009–5,536] | 216 [108–2,200] | 407 [305–541] | $0.0127 [$0.0111–$0.0331] | 14 s [6 s–32 s] |
| hybrid | 10 | 17 [10–20] | 14,980 [8,573–18,951] | 319 [159–4,400] | 365 [274–692] | $0.0332 [$0.0187–$0.0819] | 23 s [8 s–63 s] |
| **total** | 60 | 76 [60–80] | 47,641 [33,223–53,316] | 1,569 [785–17,600] | 13,363 [12,947–14,119] | $0.1112 [$0.0746–$0.2829] | 101 s [39 s–4 min] |

**Total spend: $0.1112 [$0.0746–$0.2829]**

Notes:
- The profile (sealed bundles of results/e2 (prompts rebuilt; input tokens counted by anthropic/claude-sonnet-5, output tokens = characters / 4); ollama/gemma4:e4b) is not a measured profile of anthropic/claude-sonnet-5: the range is wide and its top assumes every trial makes the most calls its condition allows and every call writes all 220 output tokens.
- Duration assumes 0.5–3.0 s per hosted model call (expected 1.2 s); no measured profile of this provider yet.
