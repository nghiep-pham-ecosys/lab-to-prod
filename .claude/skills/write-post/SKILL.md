---
name: write-post
description: Write one weekday post folder (post.md with LinkedIn, X, Facebook, Telegram and YouTube sections plus the image card) for a calendar item. Use when drafting or rewriting a post in content/.
---

# Write a post

Input: one item of `content/calendar.yaml` (date, series, part, slug, topic).
Output: `content/<week>/<date>-<slug>/post.md`, following `content/_template/post.md`.

## Before writing

1. Read `CLAUDE.md` (Voice, Content rules) and `brand/voice-samples.md`.
2. Read the last two posts of the same series, so this part continues them and repeats nothing.
3. Check `claude/lesson-log.md` for what the author actually studied on this topic. Prefer his
   example, his bug, his number.
4. Decide the **one idea**. Write it as one sentence. If it needs "and", it is two posts.
5. Find the hook: a specific number, or a common mistake. If the number is measured, write the
   script first and take the number from its output. If the example is made up, the post says
   "toy example".

## Structure of the LinkedIn section (180-280 words)

1. **Hook** (1-2 lines). The first word is a number or the mistake. No greeting, no "I'm excited".
2. **Context** (1-2 lines). Where the author met this. First person.
3. **The explanation.** Short paragraphs. Code or numbers inline as plain text (LinkedIn has no
   code blocks), at most 6 short lines of code.
4. **Why it matters** in real work (1 short paragraph).
5. **The lesson** the reader can use today (1-2 lines).
6. `Part N of my <series name> notes.`
7. Last line: 3 to 5 hashtags.

No link anywhere in the LinkedIn or X text. No emoji. No question at the end to bait comments.

## The other sections

| Section | Rule |
| --- | --- |
| `## x` | One post, at most 280 characters by X's count, same hook, no link, no hashtags needed |
| `## facebook` | 80-120 words, plainer language for a general audience, ends with the Part line |
| `## telegram` | Under 900 characters (the publisher adds the blog link; the limit is 1,024) |
| `## youtube` | Only when the calendar item has `short:`. Line 1 is the title: keyword first, at most 100 characters, contains `#Shorts`. Lines 2-3 say exactly what the video shows |

## Front matter

- `channels`: `[linkedin, facebook, telegram, x_manual]`, plus `youtube` when there is a Short.
- `short_publish_at`: copy `short.publish_at` from the calendar, else `null`.
- `sources`: 1 or 2 links for climate-ai, simulation and physical-ai posts. A paper or a report,
  not a news article about it. Every number in the post must be in the source.
- `image_alt`: one sentence that says what the image shows, including the key number or code.
- `card`: see `docs/post-format.md`. Pick the layout by content: `code` for a snippet, `stat`
  for one number, `table` for a comparison of 2-4 rows. The headline is not the post title
  repeated: it is the idea in at most 8 words.
- `status: approved`.

## Technical checklist (do not skip)

- [ ] Every code line in the post exists in a file in the post folder and that file was run.
      Java: `Name.java` + `Name.expected`. Python: the script, with its output pasted from a real run.
- [ ] Every number is either produced by a script in the repo or cited in `sources`.
- [ ] Terms are used correctly and consistently (for example "reference" vs "value").
- [ ] Nothing depends on a specific version without naming it.
- [ ] The simplification is honest: if it is only true in the common case, the post says so.
- [ ] No employer, client, colleague, internal system or private conversation is mentioned.

Then run `python tools/validate.py --week <week>` and fix every error and every warning about
length, hashtags or the Part line.
