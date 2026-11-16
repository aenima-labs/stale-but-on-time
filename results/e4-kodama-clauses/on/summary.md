| condition | errors | recall pass | asked-continuing | asked-shift | unprompted | abstain (tool) | abstain (tool or template) | abstain (in words) | gold in WM | searched | path ms median / p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c-blocking | 0/40 | 63% [47, 80] | 70% [40, 100] | 90% [70, 100] | 30% [0, 60] | 30% [0, 60] | 30% [0, 60] | 70% [40, 100] | 77% [60, 90] | 0% | 5890 / 9400 |
| d-blocking-backthought | 0/40 | 70% [53, 87] | 80% [50, 100] | 90% [70, 100] | 40% [10, 70] | 10% [0, 30] | 10% [0, 30] | 70% [40, 100] | 77% [60, 90] | 0% | 5886 / 7484 |

| condition | outcomes | Whisper WER | misheard | end of speech to reply audio ms median / p90 | STT ms median | TTS ms median | reply audio s median |
|---|---|---|---|---|---|---|---|
| c-blocking | no_reply 5, reply 35 | 3.0% | 8 | 6813 / 8794 | 357 | 232 | 5.6 |
| d-blocking-backthought | no_reply 4, reply 36 | 3.3% | 8 | 6575 / 7264 | 341 | 249 | 5.8 |

| condition | on time to 10 s, recall cases | on time to 5 s, recall cases | on time to 10 s, all cases | correct answer started by 5 / 8 / 10 s | time to answer s median / p90 (correct recall trials) | dead air s median / p90 |
|---|---|---|---|---|---|---|
| c-blocking | 0.09 [0.05, 0.14] | 0.00 [0.00, 0.00] | 0.08 [0.04, 0.12] | 0% / 20% / 50% | 8.5 / 10.2 | 5.8 / 7.8 |
| d-blocking-backthought | 0.11 [0.06, 0.16] | 0.00 [0.00, 0.00] | 0.09 [0.05, 0.13] | 0% / 23% / 60% | 8.9 / 10.4 | 5.6 / 6.3 |
