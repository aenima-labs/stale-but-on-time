# Telemetry summary: `e2`

Per trial: mean (median). Latency: median / 90th percentile, ms.

| condition | trials | model calls | tokens in | tokens out | embed tokens | cost / trial | cost (run) | trial ms (p50 / p90) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 250 | 1.00 (1.00) | 252 (252) | 20 (16) | 0 (0) | $0.0000 | $0.0000 | 412 / 639 |
| tool | 250 | 1.99 (2.00) | 729 (735) | 49 (50) | 11 (11) | $0.0000 | $0.0000 | 1,256 / 1,665 |
| blocking | 250 | 1.00 (1.00) | 391 (391) | 30 (30) | 47 (48) | $0.0000 | $0.0000 | 705 / 1,021 |
| lag1 | 250 | 1.00 (1.00) | 390 (390) | 24 (21) | 35 (35) | $0.0000 | $0.0000 | 595 / 963 |
| prefetch50 | 250 | 1.00 (1.00) | 390 (391) | 27 (24) | 41 (40) | $0.0000 | $0.0000 | 642 / 1,080 |
| hybrid | 250 | 1.62 (2.00) | 768 (874) | 45 (43) | 39 (38) | $0.0000 | $0.0000 | 1,305 / 2,271 |

Run: 1500 trials, 1904 model calls, 729,880 tokens in, 48,454 tokens out, 54,145 embedding tokens, cost $0.0000, 21.7 min of trial time.

## Latency per span kind (ms, median / p90, n)

| span kind | none | tool | blocking | lag1 | prefetch50 | hybrid |
|---|---:|---:|---:|---:|---:|---:|
| chat:reply | 411 / 639 (250) | 781 / 1,092 (248) | 691 / 999 (250) | 582 / 937 (250) | 626 / 1,054 (250) | 935 / 1,362 (156) |
| chat:tool_offer |  | 424 / 637 (250) |  |  |  | 648 / 1,144 (250) |
| embeddings:index | 934 / 934 (1) | 675 / 675 (1) | 706 / 706 (1) | 697 / 697 (1) | 810 / 810 (1) | 897 / 897 (1) |
| embeddings:query |  | 11 / 24 (246) | 12 / 24 (250) | 11 / 25 (250) | 12 / 30 (250) | 13 / 33 (349) |
| execute_tool |  | 11 / 24 (246) |  |  |  | 10 / 29 (99) |
| recall:off_path |  |  |  | 12 / 25 (250) | 12 / 30 (250) | 13 / 34 (250) |
| recall:reply_path |  |  | 12 / 25 (250) |  |  |  |
| recall:tool |  | 11 / 24 (246) |  |  |  | 10 / 29 (99) |
| reply_path | 411 / 639 (250) | 1,255 / 1,656 (250) | 704 / 1,014 (250) | 582 / 937 (250) | 626 / 1,054 (250) | 1,278 / 2,246 (250) |
| trial | 412 / 639 (250) | 1,256 / 1,665 (250) | 705 / 1,021 (250) | 595 / 963 (250) | 642 / 1,080 (250) | 1,305 / 2,271 (250) |

## Notes

- none: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- tool: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- blocking: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- lag1: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- prefetch50: 1 model or embedding call(s) took over 5× the median of their kind (longest 10,071 ms).
- prefetch50: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).
- hybrid: 3 model or embedding call(s) took over 5× the median of their kind (longest 10,114 ms).
- hybrid: indexing the memorome took 1 embedding call(s), 1,868 tokens, $0.0000 (in the run cost, not per trial).

Prices: `pricing/prices.yaml` (each entry has its source and the date it was read).
