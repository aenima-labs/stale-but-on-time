# Estimate: `e2`

- Chat model: ollama/gemma4:e4b; embeddings: ollama/nomic-embed-text
- Trials: 1500 in 6 condition(s)
- Profile: telemetry of results/e2-cloudrun-l4-timing
- Prices on 2026-11-16: chat $0.0/$0.0 per M in/out (local inference, no per-token charge, read 2026-11-13)

Expected [low–high]. The high end of a wide range is a ceiling, not a likely value.

| condition | trials | model calls | tokens in | tokens out | embed tokens | model spend | duration |
|---|---:|---:|---:|---:|---:|---:|---:|
| none | 250 | 250 [225–275] | 63,056 [56,751–69,362] | 4,912 [4,421–5,404] | 0 [0–0] | $0.0000 [$0.0000–$0.0000] | 110 s [99 s–2 min] |
| tool | 250 | 494 [444–543] | 181,300 [163,170–199,430] | 12,138 [10,924–13,351] | 2,494 [2,244–2,743] | $0.0000 [$0.0000–$0.0000] | 4 min [4 min–5 min] |
| blocking | 250 | 250 [225–275] | 97,850 [88,065–107,635] | 7,481 [6,733–8,229] | 11,919 [10,727–13,111] | $0.0000 [$0.0000–$0.0000] | 3 min [2 min–3 min] |
| lag1 | 250 | 250 [225–275] | 97,350 [87,615–107,085] | 5,819 [5,237–6,401] | 8,531 [7,678–9,384] | $0.0000 [$0.0000–$0.0000] | 2 min [2 min–3 min] |
| prefetch50 | 250 | 250 [225–275] | 97,312 [87,581–107,044] | 6,344 [5,709–6,978] | 10,206 [9,186–11,227] | $0.0000 [$0.0000–$0.0000] | 2 min [2 min–3 min] |
| hybrid | 250 | 406 [366–447] | 189,469 [170,522–208,416] | 11,000 [9,900–12,100] | 9,294 [8,364–10,223] | $0.0000 [$0.0000–$0.0000] | 4 min [4 min–4 min] |
| **total** | 1500 | 1,900 [1,710–2,090] | 726,338 [653,704–798,971] | 47,694 [42,924–52,463] | 53,652 [49,407–57,896] | $0.0000 [$0.0000–$0.0000] | 18 min [16 min–20 min] |

**No spend** (local models, local machine).
