# Design: an experiment with slow recall

Status: draft for approval, 25 November 2026, second version (slower recall step). No trial of this experiment has been run.
Once approved, this file and the new cases are committed before the first trial.

## 1. Why

The paper measures what a never-wait agent loses when it reads a result one utterance
old. In every set-up so far, waiting for recall cost 8 to 336 ms, so not waiting could
not pay. Recall that takes longer, the case the design exists for, was left as
arithmetic. Both reviews named this as the gap.

## 2. The question

When recall is slow because it does more, does an agent that reads its result one
utterance late do better than an agent that waits for a cheap lookup?

Adding a delay to the present retriever would not answer this. The agent would see the
same notes and the waiting agent would answer later by the delay: the arithmetic again.
Recall has to be slow because it is better, and the cases have to leave room for better
recall. In the present cases the cheap lookup finds the target note in 25 of 30, so
there is no room.

## 3. What is new

### A deeper recall step

The cheap lookup (BM25 and embeddings, fused) returns its 16 best notes instead of 4.
The agent's own model (`gemma4:e4b`, reasoning off, temperature 0) then reads each of
the 16 in turn, with the last three utterances, and says whether the reply needs it:
16 model calls. The notes it says are needed are loaded, at most four, in the order of
the cheap lookup. If it names none, none is loaded.

This step takes seconds because it does more, and its cost grows with the number of
notes it reads. Timing probes on throwaway queries, on the laptop:

| Recall step | Model calls | Time |
|---|---|---|
| Cheap lookup | none | 12 ms |
| Rerank, all 16 notes in one call | 1 | 0.3 to 0.8 s |
| **Judge each of 16 notes (chosen)** | **16** | **2.8 to 4.0 s** |
| One call with a written verdict on each of 16 notes | 1 | 5.9 to 7.9 s |
| Rerank in one call with reasoning on | 1 | 12 to 14 s |

- **Why this one.** Waiting three to four seconds for recall is not acceptable in a
  spoken reply, so the trade is real. A background job has between 3.4 and 9.4 s in the
  present cases (median 6.6 s: the scripted agent line and the listener's last
  utterance at 210 words per minute), so this job is ready one utterance later in most
  cases and not in the shortest.
- **Why not slower still.** The 6 to 8 s step would be ready in about half of the cases
  and the 13 s step in none. Both would mix two causes of failure, a stale record and a
  record that is not ready. The second needs lead-ins of more than two utterances to
  study, which these cases do not have.
- The prompt of this step is written and frozen on four development cases that are not
  in the test set.

### Twenty new cases

A case is *hard* when the cheap lookup, given the whole conversation, ranks the target
note between 5 and 16: outside what it loads, inside what the deeper step reads. The
new cases word the question away from the note. A first check of 18 such wordings with
the retriever alone put the target note outside the top four in 11.

| Cell | Turn | Cheap lookup | Cases |
|---|---|---|---|
| A | stays with the memory in play | finds the note | 10, the present control class |
| B | brings a new need | finds the note | 30, the present new-need classes |
| C | stays with the memory in play | misses the note | 10, new |
| D | brings a new need | misses the note | 10, new |

- In cell C the lead-in is about the target memory but does not quote it. The cheap
  lookup must rank the note between 5 and 16 on the lead-in alone as well.
- In cell D the lead-in is about something else, and the cheap lookup must rank the
  note below 16 on the lead-in alone.
- Only the 48 present notes are used, so the present cases keep their retrieval.
- The cases are fitted to the cheap retriever, which is deterministic and needs no
  model. The deeper step is never run on a test case before the registered run.
- The ten must-abstain cases run as well, to see whether deeper recall changes guessing.

### A real clock

The background job is timed in every trial. If it took longer than the time the
conversation gave it, its record is not loaded, as the never-wait rule demands.

- The time given is computed, not measured: the words of the scripted agent line and of
  the listener's last utterance at 210 words per minute, as in the paper's timing model.
- The job runs alone on the machine. In a deployed agent it would share the model with
  the reply, and take longer.
- The new cases are written for their content. Their lengths are not adjusted to let
  the job finish.

## 4. Conditions

| Agent | What it loads | What it waits for |
|---|---|---|
| Fast, fresh | cheap lookup on the whole conversation | the cheap lookup (ms) |
| Deep, fresh | deeper recall on the whole conversation | the deeper recall |
| Deep, stale | deeper recall on the lead-in, one utterance old | nothing |
| Both | the deep stale record and the cheap fresh lookup | the cheap lookup (ms) |

"Both" is the design an engineer would build first. In the product, with cheap recall,
it added nothing on the new-need cases. Here the stale record can hold a note that the cheap lookup misses.

With no memory loaded, the 20 new cases run once more as a check that their answers
cannot be guessed.

70 cases, five trials each: 1,400 trials in the four conditions and 100 in the check.
About two hours on the laptop, with no hosted model and no cost.

## 5. Expected outcome, recorded before any trial

| Cell | Fast, fresh | Deep, fresh | Deep, stale | Both |
|---|---|---|---|---|
| A: in play, cheap finds | pass | pass | pass | pass |
| B: new need, cheap finds | pass | pass | fail | pass |
| C: in play, cheap misses | fail | pass | pass | pass |
| D: new need, cheap misses | fail | pass | fail | fail |

The stale deep record should beat the fast fresh lookup in cell C only. "Both" should
match the better of the two in every cell and fail only in D. Deep fresh recall should
pass everywhere and answer three to four seconds later than the others. In the few
cases that give the job less time than it takes, the stale record should be missing and
the deep stale agent should fail in every cell.

What the construction of the cases fixes, and what it does not:

- **Fixed:** how the fast fresh agent does in each cell, since the cells are defined by
  what the cheap lookup returns.
- **Open:** whether the deeper step finds the notes the cheap lookup misses; whether it
  drops notes the cheap lookup had; whether eight loaded notes distract the model more
  than four; whether the job finishes in time; how long each agent takes to reply.

Any of these would change the conclusion:

- Deep fresh recall passes fewer than half of the hard trials: the deeper step is not
  better, and the experiment says only that.
- Deep recall passes fewer easy trials than the cheap lookup: reranking hurts.
- "Both" passes fewer trials than the fast fresh agent in cell A or B: the stale record
  distracts.

## 6. Analysis

- Unit: the case. Pass rates by cell and condition with 95% intervals from a bootstrap
  over cases, as in Experiment 2. Grading is unchanged; a key must begin a word.
- Contrasts, fixed here: in each cell, deep stale against fast fresh, both against fast
  fresh, and deep fresh against fast fresh, each as a paired difference over cases.
- Time: the measured duration of the deeper step, the median time to a complete reply
  per condition, and the share of background jobs that finished in time.
- One table of four cells by four agents, and the reply times beside it.

## 7. What the experiment cannot show

- **How often each cell occurs in real conversation.** The cells are built. The result
  says what happens in each, not which matters most in use.
- **Recall slower than the gap between turns.** The step used here takes three to four
  seconds and fits the gap in most cases. Steps of 6 to 14 s are reported only as
  measured durations that would not fit.
- **Another deeper recall.** One step, one model, one prompt. A hosted model or a
  second hop may select better or worse.
- **Scale.** The store has 48 notes, and the deeper step reads a third of them.

## 8. Where it goes in the paper

It becomes the third experiment and takes the place of the product experiment in the
main text.

1. The question and the three ways to place recall.
2. Experiment 1: how far retrieval drifts with one utterance of lag (LoCoMo).
3. Experiment 2: cheap recall. Waiting against not waiting, on new-need and control cases.
4. Experiment 3: slow recall. The four cells and the four agents.
5. Limits and conclusion.

The product, the search tool, the other models and the run histories move to the
appendix. Nothing leaves the repository.

## 9. Order of work

1. Write the 20 cases and four development cases, checking ranks with the cheap
   retriever only. Bump the pack to 1.2.0.
2. Add the deeper step, the four conditions and the clock rule to the reference agent,
   with unit tests. Freeze the prompt on the development cases.
3. Commit cases, code and this file. Then run.
4. Analyse, write the section, restructure the paper, rebuild, review.

## 10. Already done for this design

- 26 trial wordings were ranked with the cheap retriever to see whether hard cases can
  be written against the present notes. No agent model was involved.
- Timing calls were made on three throwaway queries for each of the four model steps in
  the table of section 3. Only durations and the number of selected notes were looked
  at.
