---
name: weekly-report
description: Write the weekly report reports/<week>.md from metrics.csv and published.json, with progress against the six trial targets and one proposed change. Use on Sunday evening.
---

# Weekly report

Output: `reports/<week>.md` for the week that just ended, and one line to the author.

## Get the numbers (do not retype or compute by hand)

```bash
python -m metrics.report --week <week>
```

It prints, as markdown: every post and Short of the week with what was published where and when;
the latest numbers per channel; the median of earlier weeks; follower counts at the start and
end of the week. Paste its tables as they are.

Numbers the tool cannot know come from the author and the pull request: minutes spent reviewing,
edits made, posts corrected after publishing, real comments, direct messages. If they are
missing, write "not recorded" and ask for them in the one-line message. Never estimate them.

## Sections

1. **Summary**: three sentences. What went out, what did not, the one number worth knowing.
2. **Published**: the tool's table.
3. **Numbers**: the tool's table. LinkedIn only appears if the author dropped the export in
   `metrics/inbox/`; if not, say so.
4. **Best and worst post**: one sentence each on the likely reason (hook, topic, time, format).
   Say "likely": five posts are a small sample.
5. **Progress against the six targets** (schedule ≥ 90%, author time ≤ 30 min, corrections 0,
   LinkedIn impressions ≥ 300 per post, +100 followers, ≥ 10 real comments and ≥ 1 message).
6. **This week's experiment**: what the calendar said to try, and what the numbers hint.
7. **One proposed change** for next week: specific, small, reversible. If the author agrees,
   the change is made in `CLAUDE.md` or a skill in the next weekly pull request.
8. **Pipeline health**: failed runs, token days left (from the metrics workflow), anything
   the author must do.

## Rules

- Report failures first and plainly. A missed post is "missed", with the reason.
- Do not draw conclusions the sample cannot support.
- If a post was found wrong after publishing: say it at the top, and remind the author that
  silent approval goes back to manual for two weeks.
- Commit the report on a branch and open a small pull request, or include it in the next weekly
  pull request. Do not push to main.
