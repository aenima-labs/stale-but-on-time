| condition | errors | recall pass | asked-continuing | asked-shift | unprompted | abstain (tool) | abstain (tool or template) | abstain (in words) | gold in WM | searched | path ms median / p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c-blocking | 0/40 | 63% [47, 80] | 80% [50, 100] | 80% [50, 100] | 30% [0, 60] | 10% [0, 30] | 10% [0, 30] | 70% [40, 100] | 77% [60, 90] | 0% | 5064 / 5585 |
| d-blocking-backthought | 0/40 | 57% [40, 73] | 70% [40, 100] | 70% [40, 100] | 30% [0, 60] | 10% [0, 30] | 10% [0, 30] | 70% [40, 100] | 77% [60, 90] | 0% | 4974 / 5795 |

| condition | outcomes | Whisper WER | misheard | end of speech to reply audio ms median / p90 | STT ms median | TTS ms median | reply audio s median |
|---|---|---|---|---|---|---|---|
| c-blocking | no_reply 4, reply 36 | 3.0% | 8 | 6039 / 6774 | 332 | 201 | 5.6 |
| d-blocking-backthought | no_reply 5, reply 35 | 3.3% | 8 | 5927 / 6709 | 328 | 194 | 5.6 |

| condition | on time to 10 s, recall cases | on time to 5 s, recall cases | on time to 10 s, all cases | correct answer started by 5 / 8 / 10 s | time to answer s median / p90 (correct recall trials) | dead air s median / p90 |
|---|---|---|---|---|---|---|
| c-blocking | 0.16 [0.11, 0.22] | 0.00 [0.00, 0.00] | 0.12 [0.07, 0.17] | 0% / 40% / 60% | 7.7 / 8.8 | 5.0 / 5.7 |
| d-blocking-backthought | 0.10 [0.06, 0.15] | 0.00 [0.00, 0.00] | 0.08 [0.05, 0.12] | 0% / 23% / 50% | 8.1 / 10.4 | 4.9 / 5.7 |
