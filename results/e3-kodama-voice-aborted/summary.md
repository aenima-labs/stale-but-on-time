| condition | errors | recall pass | asked-continuing | asked-shift | unprompted | abstain (tool) | abstain (tool or template) | abstain (in words) | gold in WM | searched | path ms median / p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a-tool | 0/40 | 60% [43, 77] | 90% [70, 100] | 70% [40, 100] | 20% [0, 50] | 30% [0, 60] | 30% [0, 60] | 40% [10, 70] | 0% [0, 0] | 78% | 10686 / 40788 |
| d-blocking-backthought | 0/40 | 57% [40, 73] | 70% [40, 100] | 70% [40, 100] | 30% [0, 60] | 20% [0, 50] | 20% [0, 50] | 40% [10, 70] | 67% [50, 83] | 0% | 12099 / 32591 |

| condition | outcomes | Whisper WER | misheard | end of speech to reply audio ms median / p90 | STT ms median | TTS ms median | reply audio s median |
|---|---|---|---|---|---|---|---|
| a-tool | error 2, no_reply 2, reply 36 | 3.3% | 8 | 12206 / 41950 | 366 | 370 | 7.8 |
| d-blocking-backthought | error 6, no_reply 3, reply 31 | 3.3% | 8 | 13953 / 33643 | 351 | 260 | 6.0 |
