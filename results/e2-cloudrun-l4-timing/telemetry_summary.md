# Telemetry summary: `e2-cloudrun-l4-timing`

Per trial: mean (median). Latency: median / 90th percentile, ms.

| condition | trials | model calls | tokens in | tokens out | embed tokens | cost / trial | cost (run) | trial ms (p50 / p90) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 40 | 1.00 (1.00) | 252 (252) | 20 (16) | 0 (0) | $0.0000 | $0.0000 | 384 / 576 |
| tool | 40 | 1.98 (2.00) | 725 (736) | 49 (52) | 10 (10) | $0.0000 | $0.0000 | 1,087 / 1,308 |
| blocking | 40 | 1.00 (1.00) | 391 (390) | 30 (30) | 48 (48) | $0.0000 | $0.0000 | 663 / 909 |
| lag1 | 40 | 1.00 (1.00) | 389 (389) | 23 (16) | 34 (34) | $0.0000 | $0.0000 | 448 / 845 |
| prefetch50 | 40 | 1.00 (1.00) | 389 (391) | 25 (18) | 41 (40) | $0.0000 | $0.0000 | 483 / 849 |
| hybrid | 40 | 1.62 (2.00) | 758 (881) | 44 (34) | 37 (36) | $0.0000 | $0.0000 | 862 / 1,526 |

Run: 240 trials, 304 model calls, 116,214 tokens in, 7,631 tokens out, 17,999 embedding tokens, cost $0.0000, 2.8 min of trial time.

## Latency per span kind (ms, median / p90, n)

| span kind | none | tool | blocking | lag1 | prefetch50 | hybrid |
|---|---:|---:|---:|---:|---:|---:|
| chat:reply | 383 / 573 (40) | 654 / 871 (39) | 617 / 900 (40) | 434 / 835 (40) | 452 / 840 (40) | 663 / 902 (25) |
| chat:tool_offer |  | 413 / 457 (40) |  |  |  | 509 / 759 (40) |
| embeddings:index | 243 / 243 (1) | 235 / 235 (1) | 239 / 239 (1) | 233 / 233 (1) | 230 / 230 (1) | 234 / 234 (1) |
| embeddings:query |  | 7 / 9 (39) | 8 / 9 (40) | 8 / 8 (40) | 8 / 8 (40) | 7 / 8 (52) |
| execute_tool |  | 7 / 9 (39) |  |  |  | 7 / 7 (12) |
| recall:off_path |  |  |  | 8 / 9 (40) | 8 / 9 (40) | 8 / 9 (40) |
| recall:reply_path |  |  | 8 / 10 (40) |  |  |  |
| recall:tool |  | 7 / 9 (39) |  |  |  | 7 / 7 (12) |
| reply_path | 383 / 573 (40) | 1,085 / 1,308 (40) | 625 / 909 (40) | 434 / 835 (40) | 452 / 840 (40) | 832 / 1,518 (40) |
| trial | 384 / 576 (40) | 1,087 / 1,308 (40) | 663 / 909 (40) | 448 / 845 (40) | 483 / 849 (40) | 862 / 1,526 (40) |

## Notes

- none: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- tool: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- blocking: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- lag1: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- prefetch50: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- hybrid: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).

Prices: `pricing/prices.yaml` (each entry has its source and the date it was read).
