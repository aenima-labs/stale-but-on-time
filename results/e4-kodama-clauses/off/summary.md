| condition | errors | recall pass | asked-continuing | asked-shift | unprompted | abstain (tool) | abstain (tool or template) | abstain (in words) | gold in WM | searched | path ms median / p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c-blocking | 0/40 | 73% [57, 87] | 80% [50, 100] | 90% [70, 100] | 50% [20, 80] | 20% [0, 50] | 20% [0, 50] | 60% [30, 90] | 77% [60, 90] | 0% | 5873 / 6775 |
| d-blocking-backthought | 0/40 | 70% [53, 87] | 80% [50, 100] | 90% [70, 100] | 40% [10, 70] | 20% [0, 50] | 20% [0, 50] | 50% [20, 80] | 77% [60, 90] | 0% | 5616 / 6282 |

| condition | outcomes | Whisper WER | misheard | end of speech to reply audio ms median / p90 | STT ms median | TTS ms median | reply audio s median |
|---|---|---|---|---|---|---|---|
| c-blocking | no_reply 4, reply 36 | 3.0% | 8 | 6850 / 7780 | 353 | 217 | 4.9 |
| d-blocking-backthought | no_reply 4, reply 36 | 3.3% | 8 | 6547 / 7522 | 352 | 228 | 5.4 |

| condition | on time to 10 s, recall cases | on time to 5 s, recall cases | on time to 10 s, all cases | correct answer started by 5 / 8 / 10 s | time to answer s median / p90 (correct recall trials) | dead air s median / p90 |
|---|---|---|---|---|---|---|
| c-blocking | 0.10 [0.06, 0.15] | 0.00 [0.00, 0.00] | 0.08 [0.05, 0.12] | 0% / 23% / 53% | 8.7 / 12.4 | 5.8 / 6.8 |
| d-blocking-backthought | 0.11 [0.07, 0.15] | 0.00 [0.00, 0.00] | 0.09 [0.05, 0.13] | 0% / 30% / 53% | 8.6 / 12.2 | 5.5 / 6.5 |
