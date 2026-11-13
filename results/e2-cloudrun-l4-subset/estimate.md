# Estimate: `e2-cloudrun-l4-subset`

- Chat model: ollama/gemma4:e4b; embeddings: ollama/nomic-embed-text
- Trials: 60 in 6 condition(s)
- Profile: sealed bundles of results/e2 (prompts rebuilt, tokens = characters / 4)
- Prices on 2026-11-13: chat $0.0/$0.0 per M in/out (local inference, no per-token charge, read 2026-11-13)

Expected [low–high]. The high end of a wide range is a ceiling, not a likely value.

| condition | trials | model calls | tokens in | tokens out | embed tokens | model spend | duration |
|---|---:|---:|---:|---:|---:|---:|---:|
| none | 10 | 10 [10–10] | 2,358 [1,768–3,136] | 163 [81–2,200] | 0 [0–0] | $0.0000 [$0.0000–$0.0000] | 5 s [2 s–10 s] |
| tool | 10 | 20 [10–20] | 7,155 [2,696–9,563] | 428 [214–4,400] | 84 [63–113] | $0.0000 [$0.0000–$0.0000] | 14 s [7 s–28 s] |
| blocking | 10 | 10 [10–10] | 3,790 [2,843–5,041] | 253 [126–2,200] | 475 [356–632] | $0.0000 [$0.0000–$0.0000] | 7 s [4 s–15 s] |
| lag1 | 10 | 10 [10–10] | 3,770 [2,828–5,015] | 191 [95–2,200] | 332 [249–442] | $0.0000 [$0.0000–$0.0000] | 6 s [3 s–12 s] |
| prefetch50 | 10 | 10 [10–10] | 3,770 [2,827–5,014] | 216 [108–2,200] | 407 [305–541] | $0.0000 [$0.0000–$0.0000] | 7 s [3 s–13 s] |
| hybrid | 10 | 17 [10–20] | 8,251 [3,728–13,221] | 319 [159–4,400] | 365 [274–692] | $0.0000 [$0.0000–$0.0000] | 14 s [7 s–28 s] |
| **total** | 60 | 76 [60–80] | 29,093 [16,690–40,990] | 1,569 [785–17,600] | 13,363 [12,947–14,119] | $0.1415 [$0.1324–$0.1596] | 53 s [26 s–106 s] |

Machine: cloud-run nvidia-l4 6 vCPU 24 GiB in europe-west1 (on-demand, $1.23/h, in-memory file system), start-up 5 min + run + teardown 1 min = 0.1 [0.1–0.1] h → $0.1415 [$0.1324–$0.1596] (included in the total). Hard maximum lifetime 1 h: worst case $1.23. Price: https://cloud.google.com/run/pricing, read 2026-11-13.

**Total spend: $0.1415 [$0.1324–$0.1596]**

Notes:
- The profile (sealed bundles of results/e2 (prompts rebuilt, tokens = characters / 4); ollama/gemma4:e4b) is not a measured profile of ollama/gemma4:e4b: the range is wide and its top assumes every trial makes the most calls its condition allows and every call writes all 220 output tokens.
