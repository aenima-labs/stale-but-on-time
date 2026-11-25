# Estimate: `slow-recall`

- Chat model: ollama/gemma4:e4b; embeddings: ollama/nomic-embed-text
- Trials: 1400 in 4 condition(s)
- Profile: telemetry of results/e2
- Prices on 2026-11-25: chat $0.0/$0.0 per M in/out (local inference, no per-token charge, read 2026-11-13)

Expected [low–high]. The high end of a wide range is a ceiling, not a likely value.

| condition | trials | model calls | tokens in | tokens out | embed tokens | model spend | duration |
|---|---:|---:|---:|---:|---:|---:|---:|
| blocking | 350 | 350 [315–385] | 136,920 [123,228–150,612] | 10,353 [9,318–11,388] | 16,499 [14,849–18,149] | $0.0000 [$0.0000–$0.0000] | 4 min [4 min–5 min] |
| deep | 350 | 444 [400–489] | 170,305 [153,275–187,336] | 11,306 [10,175–12,437] | 10,019 [9,017–11,020] | $0.0000 [$0.0000–$0.0000] | 5 min [5 min–6 min] |
| deep_stale | 350 | 444 [400–489] | 170,305 [153,275–187,336] | 11,306 [10,175–12,437] | 10,019 [9,017–11,020] | $0.0000 [$0.0000–$0.0000] | 5 min [5 min–6 min] |
| both | 350 | 444 [400–489] | 170,305 [153,275–187,336] | 11,306 [10,175–12,437] | 10,019 [9,017–11,020] | $0.0000 [$0.0000–$0.0000] | 5 min [5 min–6 min] |
| **total** | 1400 | 1,683 [1,515–1,851] | 647,836 [583,052–712,620] | 44,271 [39,844–48,698] | 54,027 [49,371–58,682] | $0.0000 [$0.0000–$0.0000] | 19 min [17 min–21 min] |

**No spend** (local models, local machine).

Notes:
- deep: not in the profile; the average of the other conditions is used.
- deep_stale: not in the profile; the average of the other conditions is used.
- both: not in the profile; the average of the other conditions is used.
