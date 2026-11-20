# X posts to schedule by hand: 2026-W48

On x.com: compose, attach the image, add the alt text, choose Schedule. After each post goes live, reply with its blog link.

## Mon 23 Nov, 08:30

Image: `2026-11-23-sim-p1/image.png`  
Alt text: A card with the figure 4 of 5: the reactor tests of a CSTR model that still passed after its formula was swapped for the wrong one, X = 1 - exp(-k tau). Only the test against the closed form X = k tau / (1 + k tau) failed.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-23-sim-p1/

```text
4 of 5 reactor tests still passed when I swapped the wrong formula into my CSTR model.

Moles conserved, conversion rising with volume: any reactor does that. Only the test against the closed form X = k tau / (1 + k tau) failed.

Give every model one case with an exact answer.
```

## Tue 24 Nov, 08:30

Image: `2026-11-24-cloud-p3/image.png`  
Alt text: Table of three broken CI runs, toy example: with tests skipped or the secret scan cancelled, a naive 'nothing failed' rule stays green while the ci-result rule turns red; a failed test is red under both.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-24-cloud-p3/

```text
6 checks reported on the PR that added my merge guard. 2 were skipped, and the summary check still went green. Correctly.

Rule: test and secret scan must succeed, other jobs may be skipped, cancelled is red.

A "nothing failed" rule passes 2 of 3 broken runs (toy example).
```

## Wed 25 Nov, 08:30

Image: `2026-11-25-sim-p2/image.png`  
Alt text: Code card: the Rachford-Rice function checked at both ends, f(0) = sum(z*K) - 1 and f(1) = 1 - sum(z/K). f(0) at or below 0 means all liquid, f(1) at or above 0 means all vapour, otherwise bisection on [0, 1] finds the vapour fraction in 40 steps.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-25-sim-p2/

```text
40 bisection steps put my flash drum's vapour fraction within 5e-13 of the exact answer.

The real work came first: check Rachford-Rice at psi = 0 and psi = 1. All liquid, all vapour, or a bracket with exactly one root inside.
```

## Thu 26 Nov, 08:30

Image: `2026-11-26-ai-eng-p3/image.png`  
Alt text: A table card: the rule-based format check found 5 of 5 posts with no open question at the end; the LLM judge, which passed all 5, caught a stale Short and an overstated claim instead.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-26-ai-eng-p3/

```text
5 of 5 approved posts for my first week had no open question at the end. My LLM judge passed all 5: it was never asked.

A 1-line Python rule found it. But a toy "Agree?" passes that rule too.

Rules count. The judge reads meaning. Keep both.
```

## Fri 27 Nov, 08:30

Image: `2026-11-27-ai-eng-p4/image.png`  
Alt text: A table card, toy example on a made-up 7-page handbook: with the chunk text only, BM25 ranked the right chunk 14th of 28; with the document title and section copied into each chunk, it ranked 4th.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-27-ai-eng-p4/

```text
14 of 28: where BM25 ranked the chunk that answered my RAG test question. The chunk never named the meter. The page title did, and chunking cut it off.

Copying title + section into each chunk moved it to rank 4. Toy corpus, no vector database, no API call.
```
