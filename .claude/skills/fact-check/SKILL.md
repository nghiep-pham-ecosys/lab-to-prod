---
name: fact-check
description: Check every number, claim and code sample in a post or article against a source or a real run before it can be approved. Use after writing and before judging.
---

# Fact-check

Work through the text claim by claim. A claim is any sentence a reader could act on or repeat:
a number, a behaviour of a tool, a definition, a comparison, a quote, and anything the author
says he built, measured or fixed.

## First: the work link

Every post and article from 2026-W48 on has `work:` (ids in `content/work.yaml`).

1. Each id is in the ledger and the entry's `merged` date is not after the post date
   (`python tools/validate.py --week <week>` checks this).
2. Open the merged change of each entry: `gh pr view <n>` and `gh pr diff <n>` with
   `-R nghiep-pham-ecosys/<repo>` for a pull request URL; `git show <sha>` in the local clone, or
   `gh api repos/nghiep-pham-ecosys/<repo>/commits/<sha>`, for `private@<sha>`.
3. The post is about that work. A post whose main idea is not in the change fails the check:
   rewrite it to the work or leave it out.

## For each claim, one of five outcomes

| Outcome | When | Action |
| --- | --- | --- |
| **Done work** | What the author built, measured, fixed or tested | Find it in the merged change of the post's `work:`: the diff, a test, or the pull request text. Quote the file and line, or the PR sentence. Not there: cut it. |
| **Ran it** | Code or a computed number | Run the file in the post folder. The output must match the text exactly. Java: `tools/run_samples.sh` (CI runs it too). |
| **Sourced** | A fact about the world | Open the source in `sources` and find the sentence or table that says it. Same number, same unit, same scope. |
| **Common knowledge** | A definition any textbook gives | Keep, but re-read it for precision. |
| **Cannot verify** | Anything else | Rewrite as the author's opinion, soften to what is known, or cut it. Never keep it as a fact. |

## Rules

- Open sources with a fetch, do not rely on memory. Memory is where wrong numbers come from.
- A source must be primary: the paper, the standard, the official documentation, the report.
  A blog post summarising a paper is a lead, not a source.
- Check the direction and the scope of every comparison ("faster" than what, on what, when).
- Check dates and versions: a claim about a product must name the version or say "as of <month>".
- Units and orders of magnitude: recompute any derived number yourself.
- Climate, simulation and physical AI posts: at least one source, and
  `python tools/validate.py --week <week> --check-links` must pass.
- Toy examples are labelled "toy example" in the text and in the image note.
- If a claim touches an employer, client or colleague: cut it, whether or not it is true.
- Work in a private repo: the post names the repo and never links it, and quotes none of its
  code or text. A repo that the ledger does not list is never named.

## Record

Write `content/<week>/fact-check.md`: per post, first a line with its work ids and refs, then
one table with the columns claim, outcome, evidence (file path or link plus the quoted words),
and a final line listing what was cut or softened. The judge and the author read this file.
