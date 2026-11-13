# Estimate and actual: `e2-cloudrun-l4-subset`

Estimate as expected [low–high]; actual from the run's telemetry. ⚠ marks an actual outside the estimated range.

| condition | quantity | estimate | actual |
|---|---|---:|---:|
| none | trials | 10 | 10 |
| none | chat_calls | 10 [10–10] | 10 |
| none | input_tokens | 2,358 [1,768–3,136] | 2,580 |
| none | output_tokens | 163 [81–2,200] | 164 |
| none | embed_tokens | 0 [0–0] | 0 |
| none | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| none | duration_s | 5 s [2 s–10 s] | ⚠ 64 s |
| tool | trials | 10 | 10 |
| tool | chat_calls | 20 [10–20] | 20 |
| tool | input_tokens | 7,155 [2,696–9,563] | 7,463 |
| tool | output_tokens | 428 [214–4,400] | 523 |
| tool | embed_tokens | 84 [63–113] | 110 |
| tool | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| tool | duration_s | 14 s [7 s–28 s] | ⚠ 29 s |
| blocking | trials | 10 | 10 |
| blocking | chat_calls | 10 [10–10] | 10 |
| blocking | input_tokens | 3,790 [2,843–5,041] | 3,930 |
| blocking | output_tokens | 253 [126–2,200] | 329 |
| blocking | embed_tokens | 475 [356–632] | 525 |
| blocking | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| blocking | duration_s | 7 s [4 s–15 s] | 7 s |
| lag1 | trials | 10 | 10 |
| lag1 | chat_calls | 10 [10–10] | 10 |
| lag1 | input_tokens | 3,770 [2,828–5,015] | 3,860 |
| lag1 | output_tokens | 191 [95–2,200] | 315 |
| lag1 | embed_tokens | 332 [249–442] | 405 |
| lag1 | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| lag1 | duration_s | 6 s [3 s–12 s] | 6 s |
| prefetch50 | trials | 10 | 10 |
| prefetch50 | chat_calls | 10 [10–10] | 10 |
| prefetch50 | input_tokens | 3,770 [2,827–5,014] | 3,980 |
| prefetch50 | output_tokens | 216 [108–2,200] | 315 |
| prefetch50 | embed_tokens | 407 [305–541] | 460 |
| prefetch50 | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| prefetch50 | duration_s | 7 s [3 s–13 s] | 6 s |
| hybrid | trials | 10 | 10 |
| hybrid | chat_calls | 17 [10–20] | 16 |
| hybrid | input_tokens | 8,251 [3,728–13,221] | 7,479 |
| hybrid | output_tokens | 319 [159–4,400] | 465 |
| hybrid | embed_tokens | 365 [274–692] | 453 |
| hybrid | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| hybrid | duration_s | 14 s [7 s–28 s] | 10 s |

Machine: estimated $0.1415 [$0.1324–$0.1596] for 0.11 [0.11–0.13] h; actual 0.24 h → $0.30 (from the job's own start and delete times).
