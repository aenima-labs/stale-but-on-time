| condition | errors | recall pass | asked-continuing | asked-shift | unprompted | abstain (tool) | abstain (tool or template) | abstain (in words) | gold in WM | searched | path ms median / p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a-tool | 0/40 | 63% [47, 80] | 90% [70, 100] | 90% [70, 100] | 10% [0, 30] | 40% [10, 70] | 40% [10, 70] | 50% [20, 80] | 0% [0, 0] | 75% | 9008 / 9598 |
| b-backthought | 0/40 | 23% [10, 40] | 40% [10, 70] | 0% [0, 0] | 30% [0, 60] | 0% [0, 0] | 10% [0, 30] | 80% [50, 100] | 27% [10, 43] | 0% | 5537 / 6304 |
| c-blocking | 0/40 | 70% [53, 87] | 80% [50, 100] | 80% [50, 100] | 50% [20, 80] | 10% [0, 30] | 10% [0, 30] | 60% [30, 90] | 77% [60, 90] | 0% | 6289 / 8354 |
| d-blocking-backthought | 0/40 | 67% [50, 83] | 80% [50, 100] | 80% [50, 100] | 40% [10, 70] | 10% [0, 30] | 10% [0, 30] | 40% [10, 70] | 77% [60, 90] | 0% | 6165 / 6789 |
| e-backthought-tool | 0/40 | 63% [47, 80] | 90% [70, 100] | 80% [50, 100] | 20% [0, 50] | 30% [0, 60] | 30% [0, 60] | 40% [10, 70] | 27% [10, 43] | 70% | 8634 / 9327 |

| condition | outcomes | Whisper WER | misheard | end of speech to reply audio ms median / p90 | STT ms median | TTS ms median | reply audio s median |
|---|---|---|---|---|---|---|---|
| a-tool | no_reply 5, reply 35 | 3.0% | 8 | 10365 / 11088 | 400 | 564 | 8.1 |
| b-backthought | no_reply 4, reply 36 | 3.0% | 8 | 6615 / 7595 | 381 | 310 | 4.5 |
| c-blocking | no_reply 5, reply 35 | 3.0% | 8 | 7568 / 9832 | 367 | 364 | 6.3 |
| d-blocking-backthought | no_reply 4, reply 36 | 3.0% | 8 | 7211 / 8324 | 339 | 300 | 5.5 |
| e-backthought-tool | no_reply 4, reply 36 | 3.3% | 8 | 10086 / 10657 | 336 | 382 | 8.6 |

| condition | on time to 10 s, recall cases | on time to 5 s, recall cases | on time to 10 s, all cases | correct answer started by 5 / 8 / 10 s | time to answer s median / p90 (correct recall trials) | dead air s median / p90 |
|---|---|---|---|---|---|---|
| a-tool | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.02] | 0% / 0% / 3% | 12.5 / 16.2 | 9.3 / 10.0 |
| b-backthought | 0.03 [0.01, 0.05] | 0.00 [0.00, 0.00] | 0.02 [0.00, 0.04] | 0% / 3% / 20% | 9.0 / 14.7 | 5.6 / 6.4 |
| c-blocking | 0.05 [0.02, 0.09] | 0.00 [0.00, 0.00] | 0.05 [0.02, 0.07] | 0% / 10% / 37% | 9.9 / 14.7 | 6.6 / 8.8 |
| d-blocking-backthought | 0.08 [0.04, 0.11] | 0.00 [0.00, 0.00] | 0.06 [0.03, 0.09] | 0% / 23% / 50% | 9.1 / 13.4 | 6.2 / 7.0 |
| e-backthought-tool | 0.01 [0.00, 0.03] | 0.00 [0.00, 0.00] | 0.02 [0.00, 0.04] | 0% / 3% / 7% | 12.7 / 16.6 | 8.7 / 9.6 |
