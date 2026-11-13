# Estimate and actual: `e2-anthropic`

Estimate as expected [low–high]; actual from the run's telemetry. ⚠ marks an actual outside the estimated range.

| condition | quantity | estimate | actual |
|---|---|---:|---:|
| none | trials | 200 | 200 |
| none | chat_calls | 200 [180–220] | 200 |
| none | input_tokens | 68,000 [61,200–74,800] | 66,140 |
| none | output_tokens | 20,680 [18,612–22,748] | 20,822 |
| none | embed_tokens | 0 [0–0] | 0 |
| none | cost_usd | $0.3428 [$0.3085–$0.3771] | $0.3405 |
| none | duration_s | 7 min [6 min–7 min] | 6 min |
| tool | trials | 200 | 200 |
| tool | chat_calls | 400 [360–440] | 400 |
| tool | input_tokens | 276,100 [248,490–303,710] | 270,501 |
| tool | output_tokens | 46,880 [42,192–51,568] | 45,356 |
| tool | embed_tokens | 1,840 [1,656–2,024] | ⚠ 1,542 |
| tool | cost_usd | $1.02 [$0.92–$1.12] | $0.9946 |
| tool | duration_s | 13 min [12 min–14 min] | 13 min |
| blocking | trials | 200 | 200 |
| blocking | chat_calls | 200 [180–220] | 200 |
| blocking | input_tokens | 108,500 [97,650–119,350] | 105,080 |
| blocking | output_tokens | 19,100 [17,190–21,010] | 18,246 |
| blocking | embed_tokens | 10,000 [9,000–11,000] | ⚠ 8,900 |
| blocking | cost_usd | $0.4082 [$0.3674–$0.4490] | $0.3928 |
| blocking | duration_s | 7 min [6 min–8 min] | 7 min |
| lag1 | trials | 200 | 200 |
| lag1 | chat_calls | 200 [180–220] | 200 |
| lag1 | input_tokens | 105,600 [95,040–116,160] | 104,775 |
| lag1 | output_tokens | 14,360 [12,924–15,796] | ⚠ 15,961 |
| lag1 | embed_tokens | 7,600 [6,840–8,360] | ⚠ 6,240 |
| lag1 | cost_usd | $0.3550 [$0.3195–$0.3904] | $0.3693 |
| lag1 | duration_s | 6 min [5 min–6 min] | 6 min |
| prefetch50 | trials | 200 | 200 |
| prefetch50 | chat_calls | 200 [180–220] | 200 |
| prefetch50 | input_tokens | 105,600 [95,040–116,160] | 104,230 |
| prefetch50 | output_tokens | 13,620 [12,258–14,982] | ⚠ 16,286 |
| prefetch50 | embed_tokens | 8,700 [7,830–9,570] | ⚠ 7,540 |
| prefetch50 | cost_usd | $0.3476 [$0.3128–$0.3823] | $0.3715 |
| prefetch50 | duration_s | 6 min [5 min–6 min] | ⚠ 7 min |
| hybrid | trials | 200 | 200 |
| hybrid | chat_calls | 300 [270–330] | ⚠ 380 |
| hybrid | input_tokens | 280,200 [252,180–308,220] | ⚠ 326,929 |
| hybrid | output_tokens | 25,140 [22,626–27,654] | ⚠ 34,306 |
| hybrid | embed_tokens | 8,420 [7,578–9,262] | 7,595 |
| hybrid | cost_usd | $0.8120 [$0.7308–$0.8932] | ⚠ $0.9971 |
| hybrid | duration_s | 10 min [9 min–11 min] | ⚠ 12 min |
