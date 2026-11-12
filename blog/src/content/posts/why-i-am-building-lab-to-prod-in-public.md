---
title: "Why I'm building Lab to Prod in public"
description: "A four-week experiment: one technical note every weekday, written with an AI pipeline, gated by one pull request, with every number published."
date: 2026-11-12
series: build-log
tags: [build-in-public, ai-engineering, llmops, content-pipeline]
---

20 posts, 8 short videos and 4 long articles in 4 weeks, with at most 30 minutes of my own time
per week. That is the target of the experiment that starts on Monday 16 November 2026. This
article explains why I am running it, why the whole thing is public, and what would make me stop.

## Where the name comes from

I trained as a chemist. In a lab, a result does not count because you saw it once. It counts
when someone else can follow your notebook and get the same number. Most of the work is not the
experiment. It is the controls, the calibration and the notes.

Today I build AI systems, and the distance between a demo and a system you can trust feels very
familiar. A prompt that works once on your laptop is a result you saw once. Production is the
part where you add the controls: evaluation sets, quality gates, logs, a way to roll back.

"Lab to Prod" is that path. It is also my own path, from a lab bench to production software, and
I am still on it. I am studying data structures in Java, linear algebra, cloud architecture and
climate science at the same time, and I forget things I do not write down.

## Three reasons, in order

**1. To show the work.** Saying "I know LLM evaluation" is cheap. A dated trail of notes,
code and measurements is harder to fake and easier to check. I would rather be judged on that.

**2. To learn properly.** Explaining something in 200 words to another engineer is the fastest
way I know to find out that I do not understand it yet. Each note forces one idea to be clear
enough to survive a stranger reading it.

**3. Because the pipeline is the project.** I work on AI engineering: agents, evaluation,
human approval gates, monitoring. A publishing pipeline needs all four. So instead of describing
those ideas in the abstract, I am building a small real system that uses them, and you can read
every line of it.

## What "in public" means here

Everything lives in [one repository](https://github.com/nghiep-pham-ecosys/lab-to-prod): the calendar,
every post as a markdown file, the code that draws the images and videos, the scripts that
publish, and the metrics that come back.

The weekly loop is short:

1. On Saturday, a Claude Code session drafts next week's five notes, their images, two short
   videos and one article, and opens a single pull request.
2. A validation job checks that pull request: length limits per channel, image and video sizes,
   dates against the calendar, source links for the topics where numbers are easy to get wrong,
   and a list of terms that must never appear.
3. I read it on my phone. I edit, comment, or merge.
4. After the merge, GitHub Actions publishes each post on its day through each platform's
   official API and records the result, so a re-run never posts twice.
5. Every night, a job collects the numbers. Every Sunday, a report compares them with the
   targets and proposes one change for the following week.

The rule that matters most is in step 3: **no merge, no posts.** If I am busy and the pull
request sits there, the week is skipped. That is deliberate. An automated pipeline that
publishes without a human reading it is a way to be wrong at scale.

As I write this, the repository holds the calendar, the validator, the brand assets and this
blog. The publishers are not written yet. You are reading the first entry of the notebook, not
a victory lap.

## The constraints

A few limits shape the design, and I think they make it more interesting:

- **Zero budget.** No paid APIs anywhere. Where a platform charges for posting through its API,
  the pipeline writes a file and I schedule that post by hand. It costs me about five minutes a
  week.
- **Nothing from work.** No code, data, numbers or stories from any employer or client. Every
  example is either measured in this repository, with the script next to it, or labelled as a
  toy example.
- **I answer people myself.** Replies and messages are never automated. If you write to me, you
  get me.
- **A kill switch.** One file named `PAUSE` at the root of the repository stops every publishing
  job. I can create it from my phone.
- **Corrections stay visible.** If a post is wrong, it gets a correction note. It does not get
  deleted.

## How I will know if it works

These are the numbers I committed to before starting. I am writing them down now so I cannot
move them later.

| Measure | Target after 4 weeks |
| --- | --- |
| Published on schedule | at least 90% (18 of 20 notes, 7 of 8 videos) |
| My time | at most 30 minutes a week |
| Posts corrected after publishing for a technical error | 0 |
| Average LinkedIn impressions per post | at least 300 |
| New followers across all channels | 100 |
| Real conversations | at least 10 comments and 1 direct message from an engineer |

The engagement targets are guesses. I will adjust them after the first week of real data, and I
will say so when I do. Five posts a week is also a very small sample, so the weekly experiments
(a different hook, a different format, a different posting time) will produce hints, not
conclusions.

At the end I will score the trial on six criteria: regularity, my effort, technical accuracy,
growth, quality of conversations, and whether I actually learned more. Above 3.5 out of 5, it
continues. Between 2.5 and 3.4, it slows down to three posts a week. Below 2.5, it stops, and I
keep whatever parts were useful.

## What I do not know yet

Three things worry me, and I would rather name them now.

**Can a model grade its own drafts?** From week three, I want to try silent approval: the weekly
pull request merges itself if validation passes and a separate grading step, run by a model that
did not see the drafting, scores every post at least 4 out of 5. I do not know yet whether that
grade means anything. That question gets its own article.

**Will the writing sound like me?** Drafts come from a model. I edit them, and I am responsible
for every sentence, but voice drifts. I will keep comparing against posts I wrote entirely by
hand.

**Is daily too much?** One post per channel per day is the plan. If the numbers say people tune
out, the cadence changes.

## What to expect

- **Monday to Friday:** one short note. Monday is data structures in Java, Tuesday is ML
  foundations, Wednesday is AI engineering, Thursday is cloud and DevOps, Friday alternates
  between climate and simulation.
- **Saturday:** one long article. Either a build log like this one, with the week's numbers and
  failures, or a deeper version of the best note of the week.

If you want to follow along, the [RSS feed](/lab-to-prod/rss.xml) has everything. If you spot a
mistake, open an issue on the repository. That is exactly the kind of review a lab notebook is
for.
