# Telemetry summary: `e2-smoke`

Per trial: mean (median). Latency: median / 90th percentile, ms.

| condition | trials | model calls | tokens in | tokens out | embed tokens | cost / trial | cost (run) | trial ms (p50 / p90) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| tool | 10 | 2.00 (2.00) | 746 (750) | 53 (56) | 11 (10) | $0.0000 | $0.0000 | 29,415 / 32,312 |
| blocking | 10 | 1.00 (1.00) | 393 (393) | 33 (36) | 52 (52) | $0.0000 | $0.0000 | 14,207 / 37,319 |

Run: 20 trials, 30 model calls, 11,385 tokens in, 855 tokens out, 4,369 embedding tokens, cost $0.0000, 7.8 min of trial time.

## Latency per span kind (ms, median / p90, n)

| span kind | tool | blocking |
|---|---:|---:|
| chat:reply | 13,092 / 18,208 (10) | 12,043 / 35,949 (10) |
| chat:tool_offer | 13,407 / 15,855 (10) |  |
| embeddings:index | 4,343 / 4,343 (1) | 1,146 / 1,146 (1) |
| embeddings:query | 2,140 / 2,175 (10) | 2,160 / 2,328 (10) |
| execute_tool | 2,140 / 2,176 (10) |  |
| recall:reply_path |  | 2,161 / 2,329 (10) |
| recall:tool | 2,140 / 2,176 (10) |  |
| reply_path | 27,865 / 31,923 (10) | 14,206 / 36,285 (10) |
| trial | 29,415 / 32,312 (10) | 14,207 / 37,319 (10) |

## Notes

- tool: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- blocking: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).

Prices: `pricing/prices.yaml` (each entry has its source and the date it was read).
