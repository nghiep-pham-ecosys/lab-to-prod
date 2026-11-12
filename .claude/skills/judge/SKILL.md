---
name: judge
description: Score every post of a week on the 5-point rubric using a fresh subagent that has not seen the drafting, and write content/<week>/judge.json. Use as the last step before opening the weekly pull request.
---

# Judge the week

The scores decide whether a post may be approved silently, so the judge must be independent:
**spawn a subagent** (Agent tool, general-purpose) and give it only the brief below. Do not pass
it the drafting conversation, your notes, or your opinion of the posts. Do not score the posts
yourself, and do not adjust the scores it returns.

## Brief for the subagent (fill in the week, send as is)

> You are reviewing technical posts before publication. Be strict: a wrong post damages the
> author's reputation, a held post costs nothing.
>
> Read `CLAUDE.md` (hard rules, voice, content rules) and `docs/post-format.md`. Then, for each
> folder in `content/<week>/` that has a `post.md`: read `post.md`, look at `image.png`, read
> any code sample and its expected output, and read `content/<week>/fact-check.md`.
> Check technical claims yourself: run the samples where you can, open the sources, and search
> for anything you doubt. Do not trust the fact-check file blindly.
>
> Score each post from 1 to 5 (integers) on:
> - `technical_accuracy`: every claim, number and code line is correct. 5 = you checked and
>   found nothing wrong. 3 = one imprecise statement. 1-2 = a wrong claim.
> - `sources`: numbers are sourced or reproduced by a script in the folder; sources are primary
>   and say what the post says. Posts that need no source get 5 only if every number is reproduced.
> - `one_clear_idea`: one idea, a hook with a specific number or mistake, a usable lesson.
> - `voice`: first person, short sentences, no hype, no emoji, matches the rules.
> - `no_banned_info`: nothing from an employer or client, no names of colleagues or customers,
>   no private links, no secrets. Any doubt at all is a 1.
>
> Return only JSON:
> `{"<folder name>": {"scores": {"technical_accuracy": n, "sources": n, "one_clear_idea": n, "voice": n, "no_banned_info": n}, "notes": "what you checked, what is wrong, what would raise the score"}, ...}`

## After the subagent answers

1. Save its JSON, unchanged, to a temporary file.
2. Write the record (adds the sha256 of each `post.md` and validates the shape):

   ```bash
   python tools/judge_file.py --week <week> --scores <that file>
   ```

3. Run `python tools/automerge_gate.py --week <week>`. A post passes with a mean of at least 4
   and no score below 3.
4. For a post that fails: fix what the notes say, then judge **that post again with a new
   subagent**. At most two rounds. If it still fails, leave it failing and say so in the pull
   request; the author decides.
5. Never edit `judge.json` by hand, and never edit a post after it is judged without judging it
   again: the gate compares the sha256.
