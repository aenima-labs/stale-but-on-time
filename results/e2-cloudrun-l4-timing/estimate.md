# Estimate: `e2-cloudrun-l4-timing`

- Chat model: ollama/gemma4:e4b; embeddings: ollama/nomic-embed-text
- Trials: 240 in 6 condition(s)
- Profile: telemetry of results/e2-cloudrun-l4-subset
- Prices on 2026-11-13: chat $0.0/$0.0 per M in/out (local inference, no per-token charge, read 2026-11-13)

Expected [low–high]. The high end of a wide range is a ceiling, not a likely value.

| condition | trials | model calls | tokens in | tokens out | embed tokens | model spend | duration |
|---|---:|---:|---:|---:|---:|---:|---:|
| none | 40 | 40 [36–44] | 10,320 [9,288–11,352] | 656 [590–722] | 0 [0–0] | $0.0000 [$0.0000–$0.0000] | 4 min [2 min–8 min] |
| tool | 40 | 80 [72–88] | 29,852 [26,867–32,837] | 2,092 [1,883–2,301] | 440 [396–484] | $0.0000 [$0.0000–$0.0000] | 118 s [59 s–4 min] |
| blocking | 40 | 40 [36–44] | 15,720 [14,148–17,292] | 1,316 [1,133–1,499] | 2,100 [1,890–2,310] | $0.0000 [$0.0000–$0.0000] | 27 s [13 s–53 s] |
| lag1 | 40 | 40 [36–44] | 15,440 [13,896–16,984] | 1,260 [1,057–1,463] | 1,620 [1,458–1,782] | $0.0000 [$0.0000–$0.0000] | 26 s [13 s–51 s] |
| prefetch50 | 40 | 40 [36–44] | 15,920 [14,328–17,512] | 1,260 [1,057–1,463] | 1,840 [1,656–2,024] | $0.0000 [$0.0000–$0.0000] | 26 s [13 s–52 s] |
| hybrid | 40 | 64 [58–70] | 29,916 [26,924–32,908] | 1,860 [1,626–2,094] | 1,812 [1,631–1,993] | $0.0000 [$0.0000–$0.0000] | 39 s [20 s–78 s] |
| **total** | 240 | 304 [274–334] | 117,168 [105,451–128,885] | 8,444 [7,347–9,541] | 19,020 [18,239–19,801] | $0.3939 [$0.3100–$0.5617] | 8 min [4 min–16 min] |

Machine: cloud-run nvidia-l4 6 vCPU 24 GiB in europe-west1 (on-demand, $1.23/h, in-memory file system), start-up 10 min + run + teardown 1 min = 0.3 [0.3–0.5] h → $0.3939 [$0.3100–$0.5617] (included in the total). Hard maximum lifetime 1 h: worst case $1.23. Price: https://cloud.google.com/run/pricing, read 2026-11-13.

**Total spend: $0.3939 [$0.3100–$0.5617]**
