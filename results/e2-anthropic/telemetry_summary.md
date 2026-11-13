# Telemetry summary: `e2-anthropic`

Per trial: mean (median). Latency: median / 90th percentile, ms.

| condition | trials | model calls | tokens in | tokens out | embed tokens | cost / trial | cost (run) | trial ms (p50 / p90) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 200 | 1.00 (1.00) | 331 (330) | 104 (100) | 0 (0) | $0.0017 | $0.3405 | 1,878 / 2,877 |
| tool | 200 | 2.00 (2.00) | 1,353 (1,356) | 227 (218) | 8 (8) | $0.0050 | $0.9946 | 3,888 / 4,983 |
| blocking | 200 | 1.00 (1.00) | 525 (525) | 91 (88) | 44 (44) | $0.0020 | $0.3928 | 1,882 / 2,396 |
| lag1 | 200 | 1.00 (1.00) | 524 (524) | 80 (68) | 31 (31) | $0.0018 | $0.3693 | 1,844 / 2,406 |
| prefetch50 | 200 | 1.00 (1.00) | 521 (523) | 81 (73) | 38 (37) | $0.0019 | $0.3715 | 1,920 / 2,427 |
| hybrid | 200 | 1.90 (2.00) | 1,635 (1,697) | 172 (160) | 38 (38) | $0.0050 | $0.9971 | 3,716 / 4,468 |

Run: 1200 trials, 1580 model calls, 977,655 tokens in, 150,977 tokens out, 42,437 embedding tokens, cost $3.47, 51.7 min of trial time.

## Latency per span kind (ms, median / p90, n)

| span kind | none | tool | blocking | lag1 | prefetch50 | hybrid |
|---|---:|---:|---:|---:|---:|---:|
| chat:reply | 1,873 / 2,828 (200) | 1,938 / 2,671 (200) | 1,524 / 2,048 (200) | 1,478 / 2,068 (200) | 1,549 / 2,071 (200) | 1,518 / 2,051 (180) |
| chat:tool_offer |  | 1,496 / 2,395 (200) |  |  |  | 1,501 / 2,034 (200) |
| embeddings:index | 1,639 / 1,639 (1) | 1,497 / 1,497 (1) | 959 / 959 (1) | 1,133 / 1,133 (1) | 732 / 732 (1) | 896 / 896 (1) |
| embeddings:query |  | 344 / 493 (199) | 336 / 415 (200) | 330 / 431 (200) | 323 / 390 (200) | 324 / 393 (371) |
| execute_tool |  | 345 / 494 (199) |  |  |  | 327 / 395 (171) |
| recall:off_path |  |  |  | 330 / 432 (200) | 324 / 390 (200) | 323 / 392 (200) |
| recall:reply_path |  |  | 336 / 416 (200) |  |  |  |
| recall:tool |  | 345 / 494 (199) |  |  |  | 327 / 395 (171) |
| reply_path | 1,873 / 2,828 (200) | 3,887 / 4,975 (200) | 1,882 / 2,379 (200) | 1,479 / 2,068 (200) | 1,550 / 2,071 (200) | 3,355 / 4,105 (200) |
| trial | 1,878 / 2,877 (200) | 3,888 / 4,983 (200) | 1,882 / 2,396 (200) | 1,844 / 2,406 (200) | 1,920 / 2,427 (200) | 3,716 / 4,468 (200) |

## Notes

- none: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).
- tool: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).
- blocking: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).
- lag1: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).
- prefetch50: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).
- hybrid: indexing the memorome took 1 embedding call(s), 1,770 tokens, $0.0000 (in the run cost, not per trial).

Prices: `pricing/prices.yaml` (each entry has its source and the date it was read).
