---
date: 2026-11-26
series: ai-engineering
part: 3
title: "A format check next to the LLM judge"
channels: [linkedin, facebook, telegram, x_manual, youtube]
short_publish_at: 2026-11-26T19:00:00+07:00
sources: []
image_alt: "A table card: the rule-based format check found 5 of 5 posts with no open question at the end; the LLM judge, which passed all 5, caught a stale Short and an overstated claim instead."
status: approved
work: l2p-format-checks
card:
  layout: table
  theme: light
  headline: "Rules count. The judge reads."
  rows:
    - ["Format check", "5 of 5 posts: no question at the end"]
    - ["LLM judge", "a stale Short, an overstated claim"]
  lesson: "If it can be counted, check it in code."
---

## linkedin

5 of 5 approved posts for my first week ended without an open question. My LLM judge had passed all 5.

A rule-based format check I added to my pipeline found it. It runs next to the judge and calls no model.

The judge scores five things, including accuracy, sources and voice. Its means that week were 4.4 to 5.0. The ending was not in its rubric, and its notes never mention a question. My writing rule even said "No question at the end to bait comments."

The check only counts: LinkedIn 150-300 words, a 1-2 line hook, paragraphs of at most 3 lines and 60 words. X at most 280 characters with a number in the hook. A Short of 30-60 s. The question rule is one line of Python:

question = any("?" in p for p in paras[-2:])

Its limit, in a toy example: "Agree?" passes it. The rule sees a question mark, not whether the question is open.

The judge's notes that week flagged what my rules skip: a Short not re-rendered after a fix, a bias of -2.0 called "a small number", and a claim that holds only from 10 Gbps up.

Rules cost nothing and give the same answer every run. The judge reads meaning, but scores only what its rubric names. For now the format check is informational: the approval gate does not read it.

If it can be counted, check it in code. Ask the model only about meaning.

In your LLM evaluations, which checks moved from the judge prompt into code, and which stayed with the model?

Part 3 of my AI Engineering notes.

#LLMOps #AIEngineering #LLMEvaluation #Python

## x

5 of 5 approved posts for my first week had no open question at the end. My LLM judge passed all 5: it was never asked.

A 1-line Python rule found it. But a toy "Agree?" passes that rule too.

Rules count. The judge reads meaning. Keep both.

## facebook

All 5 approved posts for my first week ended without a question for the reader, and my AI judge had passed every one of them.

I found it with a simple format check: a script that counts words, lines and question marks, with no AI involved. The judge was never asked about endings, and my writing rule said not to end with a question.

The opposite also holds. The judge caught a video that was out of date and a claim that was only true in some cases. My counting rules skip that.

So I use both: rules for what can be counted, the AI judge for what needs reading.

Part 3 of my AI Engineering notes.

## telegram

5 of 5 approved posts for my first week ended without an open question, and my LLM judge passed all 5. It was never asked about endings, and my own writing rule said no question at the end.

A rule-based format check found it: word counts, hook length, paragraph size, X length, Short length, and a "?" in the last two paragraphs. No model call.

Its limit, in a toy example: "Agree?" passes the question rule. The judge, in turn, caught a stale Short and an overstated claim, which my rules do not look for.

If it can be counted, check it in code. Ask the model only about meaning.

Part 3 of my AI Engineering notes.

## youtube

LLM Judge vs Format Rules: What Each One Catches #Shorts
A rule-based format check found 5 of 5 approved posts with no open question at the end, after an LLM judge had passed all 5.
The one-line rule, its limit ("Agree?" passes), and what the judge caught instead. Part 3 of my AI Engineering notes.
