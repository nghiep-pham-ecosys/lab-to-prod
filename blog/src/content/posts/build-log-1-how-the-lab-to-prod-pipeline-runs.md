---
title: "Build log #1: how the Lab to Prod pipeline runs"
description: "Eight pull requests, 71 tests and one paid API I had to route around: how the pipeline behind this blog is built, before its first post goes out."
date: 2026-11-21
series: build-log
part: 1
tags: [build-in-public, llmops, github-actions, ai-engineering]
---

71 tests, 8 pull requests, 5 channels posting through an API and 2 that I post by hand. That is
the pipeline behind this blog at the end of its build week. This log explains how it runs, what
I got wrong on the way, and what I still cannot measure.

One caveat first. I wrote this before the first scheduled post went out, so there are no reach
numbers here. Those belong to build log #2. Everything below is about the machine, not the
audience.

## One pull request is the only gate

The design has one rule that everything else serves: nothing is published unless I merge a pull
request.

Each week is one branch and one pull request. It contains five post folders, each with a
`post.md`, an image and sometimes a short video, plus one long article like this one. A post
folder is the unit of work. The text for every channel lives in the same file, under one
heading per channel:

```text
content/2026-W47/2026-11-16-dsa-p2/
  post.md            front matter + sections: linkedin, x, facebook, telegram, youtube
  image.png          1200x1200, drawn by code from the card block in post.md
  short.json         scenes of the short video
  short.mp4          1080x1920, rendered from short.json
  short.srt          subtitles, written from the same scenes
  IntegerCache.java  the code the post quotes
  IntegerCache.expected
```

Because a post is a folder of plain files, the review is a normal code review. I can read the
diff on my phone, change a sentence, and merge.

## What runs when

Four GitHub Actions workflows do the work. A fifth, for silent approval, exists but is switched off.

| Workflow | Trigger | Job |
| --- | --- | --- |
| validate | every pull request | tests, content rules, runs the Java samples |
| publish | merge, and every morning | hands posts to each platform, records the result |
| blog | merge, and every morning | builds this site |
| metrics | every night | collects numbers, warns before a token expires |

Two platforms can schedule by themselves, so at merge time the pipeline hands them the whole
week: Facebook gets each post with a scheduled time, YouTube gets each video as private with a
publish time. LinkedIn and Telegram have no scheduling for this kind of access, so a morning job
posts whatever is dated today.

Every successful post is written to a file called `published.json` straight away. On the next
run, anything already in that file is skipped. That one file is why I can re-run a failed job
without posting twice, and it is the first thing I would check if something looked wrong.

## The validator is the part I trust most

The check that gates every pull request is a 500-line Python script. It is boring on purpose.
For each post it checks:

- the X text is at most 280 characters by X's own counting, and LinkedIn at most 3,000;
- there is no link in the LinkedIn or X text;
- the image is exactly 1200x1200, and a video is 1080x1920 and 30 to 60 seconds long;
- a video has subtitles;
- the date, series and part match the calendar;
- posts on climate and simulation carry at least one source link;
- no banned term appears, and nothing that looks like a token is committed.

The banned-term list has one detail I like. The repository is public, so a plain list of
"words I must never publish" would itself publish those words. The public file holds only
SHA-256 hashes of the terms. The validator hashes each word of a post, and each pair of
neighbouring words, and compares.

There is a second check I added late and now consider essential: code that a post quotes must
run. The post about Java's `==` operator claims that `128 == 128` is false for `Integer`
objects. The file `IntegerCache.java` sits next to the post, with its expected output, and the
validate job compiles and runs it. If the claim were wrong, the pull request would be red.

## What I got wrong

**I planned for six API channels. There are five.** The plan listed Hashnode as an automated
channel. When I checked its documentation before writing the code, the old endpoint redirected to
an announcement: since 13 May 2026, every API request needs a paid plan. My rule is zero paid
APIs, so Hashnode became a file that I paste by hand, exactly like X. The lesson is cheap but
real: I read the official documentation of every platform before writing its publisher, and one
of six had changed under me.

**The first banned-term list leaked what it was protecting.** My first version of the list was
plain text. It was caught in review, before the pull request was merged, and replaced with the
hashed version above.

**"Private" is not a setting I can assume.** I had planned around YouTube locking uploads from
unverified apps to private. The documentation now says that restriction is gone. I do not
believe either statement until I see what happens to the first real upload, so the runbook says
to check it by hand.

**The first comment may not work.** On LinkedIn the blog link goes in the first comment, not in
the post. Posting is documented for the access level I have. Commenting is documented under a
different permission. The code tries, and if LinkedIn refuses, the post stays up and I add the
link myself. I will know which it is after the first live run.

## What is deliberately manual

Three things stay with me, and not because they are hard to automate.

1. **Approval.** I read every post before it goes out. From week three I may try silent approval
   for posts that pass an independent grading step, but that switch is off, and it gets its own
   article when I have data on whether the grades mean anything.
2. **Replies.** Comments and messages are never automated.
3. **Going live.** The publish job runs as a dry run until I set one repository variable. During
   the build week it has only ever printed what it would do.

There is also a kill switch: a file named `PAUSE` at the root of the repository stops every
publishing job. I can create it from my phone.

## What I cannot tell you yet

- Whether five posts a week is too many for the people who follow me.
- Whether the short videos are worth making. They are captions and code on a dark background,
  with no voice. They take a minute or two each to render, so they are cheap, which is not the same as
  good.
- Whether a model can grade drafts written by a model. The grading step runs in a separate
  session that does not see the drafting, and its scores are stored with a hash of the post so
  they cannot be reused after an edit. That makes the grade tamper-evident. It does not make it
  right.
- How long the weekly review really takes me. The target is 30 minutes. I will time it.

Next Saturday's article is a deeper version of this week's note on precision and recall: how to
build a quality gate for LLM output, from two numbers to a rubric. Build log #2 follows a week
later, with the first real numbers.

The code is at [github.com/nghiep-pham-ecosys/lab-to-prod](https://github.com/nghiep-pham-ecosys/lab-to-prod).
If you see a mistake in a post, open an issue. That is what a lab notebook is for.
