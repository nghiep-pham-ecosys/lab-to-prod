---
date: 2026-11-18
series: ai-engineering
part: 2
title: "Precision and recall for an LLM quality gate"
channels: [linkedin, facebook, telegram, x_manual, youtube]
short_publish_at: 2026-11-19T19:00:00+07:00
sources: []
image_alt: "A card showing recall 0.62: a quality gate with 80 percent precision still caught only 8 of 13 bad answers."
status: approved
card:
  layout: stat
  theme: ink
  headline: "80% precision, and 5 bad answers still got through"
  stat:
    value: "0.62"
    label: "recall of the gate"
    note: "Toy example: 13 bad answers, 10 flagged, 8 flagged correctly."
  lesson: "Pick the metric by which mistake costs more."
---

## linkedin

5 of 13 bad answers passed a quality gate, and its precision was 80%.

This is a toy example, but the mistake is one I see often: reporting one number for a gate that can fail in two different ways.

The setup. An LLM answers 100 questions. A reviewer marks 13 answers as bad. An automated gate, which could be a rule or another model, flags 10 answers for blocking. 8 of those 10 really are bad.

Precision asks: of what the gate flagged, how much was really bad? 8 of 10, so 0.80.

Recall asks: of what was really bad, how much did the gate catch? 8 of 13, so 0.62.

Same gate, two very different stories. "80% precise" sounds safe. "Misses 38% of bad answers" does not.

Which one matters depends on the cost of each error:

- If a bad answer reaching a user is expensive (medical, legal, money), optimise recall and accept more false alarms.
- If a false alarm is expensive (a human has to review every flag), optimise precision and accept some misses.

You rarely get both. Moving the threshold trades one for the other, so decide which mistake is worse before tuning.

What I do now: report both numbers, with the counts behind them. 8/10 and 8/13 tell you more than 0.80 and 0.62, because they show how small the sample is.

The script that computes these numbers is in the repository.

Part 2 of my AI Engineering notes.

#LLMOps #AIEngineering #LLMEvaluation #MachineLearning

## x

5 of 13 bad answers passed an LLM quality gate. Its precision was 80%.

Precision: of what the gate flagged, how much was bad? 8/10.
Recall: of what was bad, how much did it catch? 8/13.

One number hides the other. Report both, with counts. (Toy example.)

## facebook

A quality gate with 80% precision can still let 5 of 13 bad answers through.

Toy example: an LLM gives 100 answers and 13 are bad. A gate flags 10 answers, and 8 of those are really bad. Precision is 8 of 10, which sounds good. Recall is 8 of 13: the gate missed 5 bad answers.

Precision tells you how trustworthy a flag is. Recall tells you how much slips past. Which one to optimise depends on which mistake costs more: a bad answer reaching a user, or a human reviewing a false alarm.

Report both numbers, with the counts.

Part 2 of my AI Engineering notes.

## telegram

A quality gate with 80% precision still let 5 of 13 bad answers through (toy example).

Precision = of what was flagged, how much was really bad: 8/10.
Recall = of what was bad, how much was caught: 8/13.

Decide which mistake costs more, then tune. Always report both, with counts.

Part 2 of my AI Engineering notes.

## youtube

Precision vs Recall for LLM Evaluation in 45s #Shorts
Precision and recall for an LLM quality gate, with a toy example: 13 bad answers, 10 flagged, 8 correct. Precision 0.80, recall 0.62.
Why one number is not enough and how to choose which to optimise. Part 2 of my AI Engineering notes.
