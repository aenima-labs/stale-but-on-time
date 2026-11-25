# Telemetry summary: `slow-recall`

Per trial: mean (median). Latency: median / 90th percentile, ms.

| condition | trials | model calls | tokens in | tokens out | embed tokens | cost / trial | cost (run) | trial ms (p50 / p90) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 100 | 1.00 (1.00) | 246 (246) | 18 (16) | 0 (0) | $0.0000 | $0.0000 | 385 / 678 |
| blocking | 350 | 1.00 (1.00) | 389 (390) | 27 (24) | 46 (46) | $0.0000 | $0.0000 | 615 / 973 |
| both | 350 | 17.00 (17.00) | 3,832 (3,823) | 141 (142) | 79 (80) | $0.0000 | $0.0000 | 5,728 / 6,054 |
| deep | 350 | 17.00 (17.00) | 3,983 (3,969) | 144 (144) | 46 (46) | $0.0000 | $0.0000 | 5,954 / 6,296 |
| deep_stale | 350 | 17.00 (17.00) | 3,723 (3,719) | 136 (132) | 33 (35) | $0.0000 | $0.0000 | 5,685 / 6,028 |

Run: 1500 trials, 18300 model calls, 4,198,726 tokens in, 158,442 tokens out, 80,660 embedding tokens, cost $0.0000, 106.1 min of trial time.

## Latency per span kind (ms, median / p90, n)

| span kind | none | blocking | both | deep | deep_stale |
|---|---:|---:|---:|---:|---:|
| chat:recall_judge |  |  | 317 / 332 (5600) | 326 / 346 (5600) | 324 / 338 (5600) |
| chat:reply | 384 / 673 (100) | 603 / 956 (350) | 613 / 941 (350) | 695 / 980 (350) | 533 / 835 (350) |
| embeddings:index | 794 / 794 (1) | 618 / 618 (1) | 591 / 591 (1) | 777 / 777 (1) | 623 / 623 (1) |
| embeddings:query |  | 11 / 14 (350) | 13 / 28 (700) | 15 / 18 (350) | 15 / 16 (350) |
| recall:off_path |  |  | 11 / 12 (350) |  | 16 / 17 (350) |
| recall:reply_path |  | 11 / 14 (350) | 18 / 34 (350) | 16 / 18 (350) |  |
| reply_path | 384 / 673 (100) | 614 / 967 (350) | 633 / 965 (350) | 5,953 / 6,292 (350) | 533 / 836 (350) |
| trial | 385 / 678 (100) | 615 / 973 (350) | 5,728 / 6,054 (350) | 5,954 / 6,296 (350) | 5,685 / 6,028 (350) |

## Notes

- none: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- blocking: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- both: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- deep: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- deep_stale: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).

Prices: `pricing/prices.yaml` (each entry has its source and the date it was read).
