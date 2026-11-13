# Telemetry summary: `e2-anthropic-pilot`

Per trial: mean (median). Latency: median / 90th percentile, ms.

| condition | trials | model calls | tokens in | tokens out | embed tokens | cost / trial | cost (run) | trial ms (p50 / p90) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 10 | 1.00 (1.00) | 340 (340) | 103 (66) | 0 (0) | $0.0017 | $0.0172 | 1,509 / 3,364 |
| tool | 10 | 2.00 (2.00) | 1,380 (1,380) | 234 (233) | 9 (10) | $0.0051 | $0.0511 | 3,669 / 4,958 |
| blocking | 10 | 1.00 (1.00) | 542 (542) | 96 (96) | 50 (50) | $0.0020 | $0.0204 | 1,934 / 2,793 |
| lag1 | 10 | 1.00 (1.00) | 528 (528) | 72 (78) | 38 (38) | $0.0018 | $0.0178 | 1,754 / 2,368 |
| prefetch50 | 10 | 1.00 (1.00) | 528 (528) | 68 (60) | 44 (44) | $0.0017 | $0.0174 | 1,838 / 2,135 |
| hybrid | 10 | 1.50 (1.50) | 1,401 (1,401) | 126 (124) | 42 (42) | $0.0041 | $0.0406 | 2,864 / 4,289 |

Run: 60 trials, 75 model calls, 47,200 tokens in, 6,989 tokens out, 12,448 embedding tokens, cost $0.1645, 2.4 min of trial time.

## Latency per span kind (ms, median / p90, n)

| span kind | none | tool | blocking | lag1 | prefetch50 | hybrid |
|---|---:|---:|---:|---:|---:|---:|
| chat:reply | 1,508 / 3,165 (10) | 1,231 / 2,530 (10) | 1,615 / 1,836 (10) | 1,328 / 1,720 (10) | 1,240 / 1,732 (10) | 1,665 / 1,933 (5) |
| chat:tool_offer |  | 1,701 / 2,311 (10) |  |  |  | 1,565 / 1,675 (10) |
| embeddings:index | 1,981 / 1,981 (1) | 825 / 825 (1) | 908 / 908 (1) | 920 / 920 (1) | 945 / 945 (1) | 1,002 / 1,002 (1) |
| embeddings:query |  | 358 / 767 (10) | 328 / 394 (10) | 317 / 410 (10) | 319 / 351 (10) | 318 / 350 (15) |
| execute_tool |  | 359 / 767 (10) |  |  |  | 312 / 338 (5) |
| recall:off_path |  |  |  | 318 / 412 (10) | 320 / 352 (10) | 323 / 345 (10) |
| recall:reply_path |  |  | 329 / 396 (10) |  |  |  |
| recall:tool |  | 359 / 767 (10) |  |  |  | 312 / 338 (5) |
| reply_path | 1,508 / 3,165 (10) | 3,668 / 4,874 (10) | 1,933 / 2,164 (10) | 1,328 / 1,720 (10) | 1,240 / 1,732 (10) | 2,533 / 3,614 (10) |
| trial | 1,509 / 3,364 (10) | 3,669 / 4,958 (10) | 1,934 / 2,793 (10) | 1,754 / 2,368 (10) | 1,838 / 2,135 (10) | 2,864 / 4,289 (10) |

## Notes

- none: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).
- tool: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).
- blocking: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).
- lag1: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).
- prefetch50: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).
- hybrid: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).

Prices: `pricing/prices.yaml` (each entry has its source and the date it was read).
