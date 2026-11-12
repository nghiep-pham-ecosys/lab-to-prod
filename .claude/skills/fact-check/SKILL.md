---
name: fact-check
description: Check every number, claim and code sample in a post or article against a source or a real run before it can be approved. Use after writing and before judging.
---

# Fact-check

Work through the text claim by claim. A claim is any sentence a reader could act on or repeat:
a number, a behaviour of a tool, a definition, a comparison, a quote.

## For each claim, one of four outcomes

| Outcome | When | Action |
| --- | --- | --- |
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

## Record

Write `content/<week>/fact-check.md`: one table per post with the columns claim, outcome,
evidence (file path or link plus the quoted words), and a final line listing what was cut or
softened. The judge and the author read this file.
