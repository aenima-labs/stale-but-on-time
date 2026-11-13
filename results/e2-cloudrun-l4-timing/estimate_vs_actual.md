# Estimate and actual: `e2-cloudrun-l4-timing`

Estimate as expected [low–high]; actual from the run's telemetry. ⚠ marks an actual outside the estimated range.

| condition | quantity | estimate | actual |
|---|---|---:|---:|
| none | trials | 40 | 40 |
| none | chat_calls | 40 [36–44] | 40 |
| none | input_tokens | 10,320 [9,288–11,352] | 10,089 |
| none | output_tokens | 656 [590–722] | ⚠ 786 |
| none | embed_tokens | 0 [0–0] | 0 |
| none | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| none | duration_s | 4 min [2 min–8 min] | ⚠ 18 s |
| tool | trials | 40 | 40 |
| tool | chat_calls | 80 [72–88] | 79 |
| tool | input_tokens | 29,852 [26,867–32,837] | 29,008 |
| tool | output_tokens | 2,092 [1,883–2,301] | 1,942 |
| tool | embed_tokens | 440 [396–484] | 399 |
| tool | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| tool | duration_s | 118 s [59 s–4 min] | ⚠ 42 s |
| blocking | trials | 40 | 40 |
| blocking | chat_calls | 40 [36–44] | 40 |
| blocking | input_tokens | 15,720 [14,148–17,292] | 15,656 |
| blocking | output_tokens | 1,316 [1,133–1,499] | 1,197 |
| blocking | embed_tokens | 2,100 [1,890–2,310] | 1,907 |
| blocking | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| blocking | duration_s | 27 s [13 s–53 s] | 26 s |
| lag1 | trials | 40 | 40 |
| lag1 | chat_calls | 40 [36–44] | 40 |
| lag1 | input_tokens | 15,440 [13,896–16,984] | 15,576 |
| lag1 | output_tokens | 1,260 [1,057–1,463] | ⚠ 931 |
| lag1 | embed_tokens | 1,620 [1,458–1,782] | ⚠ 1,365 |
| lag1 | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| lag1 | duration_s | 26 s [13 s–51 s] | 22 s |
| prefetch50 | trials | 40 | 40 |
| prefetch50 | chat_calls | 40 [36–44] | 40 |
| prefetch50 | input_tokens | 15,920 [14,328–17,512] | 15,570 |
| prefetch50 | output_tokens | 1,260 [1,057–1,463] | ⚠ 1,015 |
| prefetch50 | embed_tokens | 1,840 [1,656–2,024] | ⚠ 1,633 |
| prefetch50 | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| prefetch50 | duration_s | 26 s [13 s–52 s] | 23 s |
| hybrid | trials | 40 | 40 |
| hybrid | chat_calls | 64 [58–70] | 65 |
| hybrid | input_tokens | 29,916 [26,924–32,908] | 30,315 |
| hybrid | output_tokens | 1,860 [1,626–2,094] | 1,760 |
| hybrid | embed_tokens | 1,812 [1,631–1,993] | ⚠ 1,487 |
| hybrid | cost_usd | $0.0000 [$0.0000–$0.0000] | $0.0000 |
| hybrid | duration_s | 39 s [20 s–78 s] | 39 s |

Machine: estimated $0.3939 [$0.3100–$0.5617] for 0.32 [0.25–0.46] h; actual 0.20 h → $0.25 (from the job's own start and delete times).
