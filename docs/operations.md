# Operations

## The switches

| Switch | Where | Effect |
| --- | --- | --- |
| `PUBLISH_LIVE` = `true` | repository variable | `publish.yml` really posts. Anything else, or unset: dry run |
| `AUTOMERGE_ENABLED` = `true` | repository variable | `automerge.yml` may merge the weekly pull request on Sunday 22:00. Unset: it does nothing |
| `PAUSE` file | repository root | every publishing run exits without posting; silent approval stops too |
| label `hold` | on the weekly pull request | silent approval skips it |
| label `weekly` | on the weekly pull request | marks the pull request that silent approval looks at |
| `channels:` | `publish/config.yaml` | per channel: `api`, `manual` or `off` |
| `LINKEDIN_TOKEN_ISSUED` | repository variable, `YYYY-MM-DD` | lets `metrics.yml` warn 7 days before the 60-day token expires |

Repository variables: Settings → Secrets and variables → Actions → Variables.
To pause from a phone: GitHub app → repository → "+" → create a file named `PAUSE` on `main`.

## The workflows

| Workflow | Runs | Does |
| --- | --- | --- |
| `validate` | every pull request, pushes to main | tests, validation, Java samples |
| `blog` | merge to main, daily 08:20, pull requests (build only) | builds and deploys the blog |
| `publish` | merge to main, Mon-Sat 08:15, pull requests (dry run only), manual | posts or schedules; commits `published.json` |
| `metrics` | daily 22:00, manual | writes `metrics/metrics.csv`; red when a token needs attention |
| `automerge` | Sunday 22:00, manual; only when enabled | holds failing posts, merges the rest, starts `publish` and `blog` |

All times are Asia/Ho_Chi_Minh. GitHub's scheduler can run several minutes late.

## Going live, one channel at a time

1. Add the channel's secrets (`docs/setup.md`).
2. Keep `PUBLISH_LIVE` unset and read a dry run: Actions → publish → Run workflow, with `date` set
   to a day that has an approved post. The plan is printed in the run summary.
3. To test one channel for real, set every other channel to `off` in `publish/config.yaml`,
   merge that, set `PUBLISH_LIVE` to `true`, and run the workflow with `only` set to that channel.
4. Check the post on the platform, then check `published.json`.

## When something goes wrong

- **A channel is red.** The run summary has the platform's error. Fix it and re-run: channels
  that already succeeded are skipped.
- **A post is wrong.** Do not delete it. Add a correction as a comment on the platform and a note
  in the post folder. Set `AUTOMERGE_ENABLED` to `false` for two weeks.
- **Stop everything now.** Create the `PAUSE` file. A post that Facebook or YouTube has already
  scheduled must also be cancelled on the platform itself (Meta Business Suite, YouTube Studio).
