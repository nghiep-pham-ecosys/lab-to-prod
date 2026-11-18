# Paper notes

Short notes on papers the author has read, written in their own words. A merged note is project
work: it gets an entry in `content/work.yaml` (`id: paper-<slug>`, `ref` = the merged pull request)
and may then be the source of a post, like any other work.

## Flow

1. Wednesday: the author reads one paper (chosen from the weekly paper digests).
2. If the paper is worth a post, a note is written here in a pull request: one file per paper,
   `notes/papers/<YYYY-MM-DD>-<slug>.md`, dated the day the note is written.
3. After the merge, add the work entry to `content/work.yaml`. Draft-week may then plan a post on it.

## Rules

- Own words only. Never copy the abstract or long passages; quote at most one short sentence.
- Link the paper itself (arXiv, DOI or the publisher page), not a newsletter.
- Every number in the note is checked against the paper, with the table or figure it comes from.
- Say what the note adds: why it matters for the author's work (process simulation, LLM evaluation,
  data extraction from scientific papers, materials, climate) and what to try next.
- Public-safe: no employer, client or personal data.

## Template

Copy `_template.md` to `<YYYY-MM-DD>-<slug>.md`.
