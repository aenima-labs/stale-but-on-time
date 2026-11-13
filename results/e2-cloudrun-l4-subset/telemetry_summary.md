# Telemetry summary: `e2-cloudrun-l4-subset`

Per trial: mean (median). Latency: median / 90th percentile, ms.

| condition | trials | model calls | tokens in | tokens out | embed tokens | cost / trial | cost (run) | trial ms (p50 / p90) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 10 | 1.00 (1.00) | 258 (258) | 16 (16) | 0 (0) | $0.0000 | $0.0000 | 335 / 6,406 |
| tool | 10 | 2.00 (2.00) | 746 (750) | 52 (56) | 11 (12) | $0.0000 | $0.0000 | 1,246 / 5,126 |
| blocking | 10 | 1.00 (1.00) | 393 (393) | 33 (36) | 52 (52) | $0.0000 | $0.0000 | 742 / 870 |
| lag1 | 10 | 1.00 (1.00) | 386 (386) | 32 (32) | 40 (40) | $0.0000 | $0.0000 | 778 / 866 |
| prefetch50 | 10 | 1.00 (1.00) | 398 (398) | 32 (32) | 46 (46) | $0.0000 | $0.0000 | 763 / 874 |
| hybrid | 10 | 1.60 (2.00) | 748 (888) | 46 (48) | 45 (45) | $0.0000 | $0.0000 | 1,110 / 1,339 |

Run: 60 trials, 76 model calls, 29,292 tokens in, 2,111 tokens out, 13,161 embedding tokens, cost $0.0000, 2.0 min of trial time.

## Latency per span kind (ms, median / p90, n)

| span kind | none | tool | blocking | lag1 | prefetch50 | hybrid |
|---|---:|---:|---:|---:|---:|---:|
| chat:reply | 334 / 4,281 (10) | 698 / 927 (10) | 654 / 861 (10) | 641 / 855 (10) | 636 / 861 (10) | 952 / 965 (6) |
| chat:tool_offer |  | 371 / 407 (10) |  |  |  | 396 / 578 (10) |
| embeddings:index | 21,240 / 21,240 (1) | 235 / 235 (1) | 229 / 229 (1) | 252 / 252 (1) | 235 / 235 (1) | 231 / 231 (1) |
| embeddings:query |  | 8 / 3,827 (10) | 8 / 11 (10) | 7 / 11 (10) | 7 / 12 (10) | 7 / 9 (15) |
| execute_tool |  | 9 / 3,828 (10) |  |  |  | 8 / 8 (5) |
| recall:off_path |  |  |  | 8 / 11 (10) | 8 / 12 (10) | 8 / 10 (10) |
| recall:reply_path |  |  | 9 / 11 (10) |  |  |  |
| recall:tool |  | 9 / 3,828 (10) |  |  |  | 8 / 8 (5) |
| reply_path | 335 / 4,281 (10) | 1,245 / 5,102 (10) | 666 / 869 (10) | 641 / 855 (10) | 636 / 862 (10) | 985 / 1,330 (10) |
| trial | 335 / 6,406 (10) | 1,246 / 5,126 (10) | 742 / 870 (10) | 778 / 866 (10) | 763 / 874 (10) | 1,110 / 1,339 (10) |

## Notes

- none: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- tool: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- blocking: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- lag1: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- prefetch50: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- hybrid: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).

Prices: `pricing/prices.yaml` (each entry has its source and the date it was read).
