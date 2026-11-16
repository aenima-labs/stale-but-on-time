# Cheaper output checks on Kodama (voice, exploratory)

Kodama development runs, not yet a paper experiment. Kodama commit `53f6e2f`
(branch `w003-backthought-recall`): the greeting and advice classifiers stop
as soon as their first score, written first, shows the turn is not a greeting
or not an advice ask. That score alone decides "allow", so the decision is the
one the whole verdict gives; the model just does not write the rest.

- Conditions c-blocking and d-blocking-backthought, voice pack (40 cases, one
  trial each), speech.clauses off.
- Local Ollama with one slot (`OLLAMA_NUM_PARALLEL=1`), as in
  `e3-kodama-voice/` (Kodama `f992ca3`, 2026-11-11/12), which is the
  comparison. That comparison is across days.
- Ran 2026-11-12: c 21:25–21:35 UTC, d 21:35–21:45 UTC. 0 errors, both
  bundles sealed.

## Result: about 1.3–1.5 s sooner, decisions unchanged by construction

| condition | run | recall pass | first audio median / p90 | time to answer median | on time to 10 s |
|---|---|---|---|---|---|
| c-blocking | `f992ca3` (e3-kodama-voice) | 70% [53, 87] | 7.57 / 9.83 s | 9.9 s | 0.05 [0.02, 0.09] |
| c-blocking | `53f6e2f` (here) | 63% [47, 80] | 6.04 / 6.77 s | 7.7 s | 0.16 [0.11, 0.22] |
| d-blocking-backthought | `f992ca3` (e3-kodama-voice) | 67% [50, 83] | 7.21 / 8.32 s | 9.1 s | 0.08 [0.04, 0.11] |
| d-blocking-backthought | `53f6e2f` (here) | 57% [40, 73] | 5.93 / 6.71 s | 8.1 s | 0.10 [0.06, 0.15] |

- **Per call** (six-case smoke at one slot, same day, before and after): advice
  check 1.04 → 0.57 s, greeting check 0.82 → 0.40 s, all output checks
  2.17 → 1.73 s. The main reply also waits less behind the advice check.
- **Recall pass went down, but not because of the change.** Only 5 of 40
  replies per condition were word-for-word the same as in `e3-kodama-voice/`:
  the model's replies vary between runs. In every case that flipped, the
  greeting and advice checks allowed the reply. The two replies that became
  the limit sentence were templated by the uncited-claim check, which this
  change does not touch, on a different draft. Two runs of the same code
  differed by 10 points too (`e4-kodama-clauses/`, c off vs on), and the
  intervals here overlap.
- **One empty reply** (d, shift-hip-year): the model generated 80 tokens of
  which Ollama passed on no text or tool call, so there was nothing to speak.
  The same happened once in `e4-kodama-clauses/` (582 tokens). It is not
  caused by streaming or clause speech; this run had neither.
