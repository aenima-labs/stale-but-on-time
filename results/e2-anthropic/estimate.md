# Estimate: `e2-anthropic`

- Chat model: anthropic/claude-sonnet-5; embeddings: openai/text-embedding-3-small
- Trials: 1200 in 6 condition(s)
- Profile: telemetry of results/e2-anthropic-pilot
- Prices on 2026-11-13: chat $2.0/$10.0 per M in/out (https://platform.claude.com/docs/en/about-claude/pricing, read 2026-11-13)

Expected [low–high]. The high end of a wide range is a ceiling, not a likely value.

| condition | trials | model calls | tokens in | tokens out | embed tokens | model spend | duration |
|---|---:|---:|---:|---:|---:|---:|---:|
| none | 200 | 200 [180–220] | 68,000 [61,200–74,800] | 20,680 [18,612–22,748] | 0 [0–0] | $0.3428 [$0.3085–$0.3771] | 7 min [6 min–7 min] |
| tool | 200 | 400 [360–440] | 276,100 [248,490–303,710] | 46,880 [42,192–51,568] | 1,840 [1,656–2,024] | $1.02 [$0.92–$1.12] | 13 min [12 min–14 min] |
| blocking | 200 | 200 [180–220] | 108,500 [97,650–119,350] | 19,100 [17,190–21,010] | 10,000 [9,000–11,000] | $0.4082 [$0.3674–$0.4490] | 7 min [6 min–8 min] |
| lag1 | 200 | 200 [180–220] | 105,600 [95,040–116,160] | 14,360 [12,924–15,796] | 7,600 [6,840–8,360] | $0.3550 [$0.3195–$0.3904] | 6 min [5 min–6 min] |
| prefetch50 | 200 | 200 [180–220] | 105,600 [95,040–116,160] | 13,620 [12,258–14,982] | 8,700 [7,830–9,570] | $0.3476 [$0.3128–$0.3823] | 6 min [5 min–6 min] |
| hybrid | 200 | 300 [270–330] | 280,200 [252,180–308,220] | 25,140 [22,626–27,654] | 8,420 [7,578–9,262] | $0.8120 [$0.7308–$0.8932] | 10 min [9 min–11 min] |
| **total** | 1200 | 1,500 [1,350–1,650] | 944,000 [849,600–1,038,400] | 139,780 [125,802–153,758] | 47,180 [43,524–50,836] | $3.29 [$2.96–$3.62] | 48 min [43 min–53 min] |

**Total spend: $3.29 [$2.96–$3.62]**
