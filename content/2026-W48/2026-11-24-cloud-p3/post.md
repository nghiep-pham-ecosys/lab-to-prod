---
date: 2026-11-24
series: cloud-devops
part: 3
title: "A merge guard for a private repo on the free plan"
channels: [linkedin, facebook, telegram, x_manual]
short_publish_at: null
sources:
  - https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
  - https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
image_alt: "Table of three broken CI runs, toy example: with tests skipped or the secret scan cancelled, a naive 'nothing failed' rule stays green while the ci-result rule turns red; a failed test is red under both."
status: approved
work: cfe-ci-guard
card:
  layout: table
  theme: dark
  headline: "Nothing failed is not everything ran"
  rows:
    - ["Tests skipped", "naive: green. ci-result: red."]
    - ["Scan cancelled", "naive: green. ci-result: red."]
    - ["Test failed", "naive: red. ci-result: red."]
  lesson: "Name the jobs that must succeed. Toy example."
---

## linkedin

6 checks reported on the pull request that added my merge guard. 2 were skipped, and the summary check still went green. That was correct, and getting it right was the real work.

The repo is a private course repo on GitHub Free. On that plan, branch protection and rulesets only cover public repos, so GitHub will not block a bad merge on a private one. The guard has to live where I control it.

It has three parts.

- a pre-push hook that runs gitleaks on the commits being pushed, and blocks the push on a finding or when gitleaks is missing;
- a pr-title check, because the title becomes the squash commit subject;
- ci-result, one job that waits for every other job in the CI workflow and sums them up.

My merge script requires just two checks: ci-result and pr-title. So ci-result must tell "skipped by design" from "did not run".

A naive rule, "green when nothing failed", cannot. In a toy example with 3 broken runs (tests skipped, secret scan cancelled, a test failed), it lets 2 through. The rule I merged: test and gitleaks must succeed, every other job must succeed or be skipped, and cancelled is red. It lets 0 of 3 through.

This matters beyond free plans. Even with branch protection, GitHub accepts a required check that was skipped.

The lesson: when one check stands for many, name the jobs that must succeed.

In your CI, which job would hurt most if it were skipped and nobody noticed, and how do you catch that today?

Part 3 of my Cloud & DevOps notes.

#GitHubActions #DevOps #CICD #LearningInPublic

## x

6 checks reported on the PR that added my merge guard. 2 were skipped, and the summary check still went green. Correctly.

Rule: test and secret scan must succeed, other jobs may be skipped, cancelled is red.

A "nothing failed" rule passes 2 of 3 broken runs (toy example).

## facebook

Who stops a bad merge when the platform will not? On GitHub's free plan, branch protection only covers public repos, so for my private course repo I built the guard myself.

It has three parts. A hook on my machine scans every push for leaked secrets. One check makes sure pull request titles follow the commit format. And one summary check, ci-result, looks at every other job in the CI workflow.

The hard part was the summary. "Nothing failed" is not enough: a skipped test job or a cancelled secret scan also "did not fail". So the rule names the jobs that must succeed.

Nothing failed is not the same as everything ran.

Part 3 of my Cloud & DevOps notes.

## telegram

A merge guard for a private repo on GitHub Free, where branch protection only covers public repos.

Three parts:
- pre-push hook: gitleaks on the pushed commits, blocks the push on a finding or when gitleaks is missing
- pr-title check: the title becomes the squash commit subject
- ci-result: one job that sums up the other jobs of the CI workflow

The catch is in ci-result. "Green when nothing failed" lets 2 of 3 broken runs through in a toy example (tests skipped, scan cancelled). The rule I merged: test and gitleaks must succeed, other jobs may be skipped, cancelled is red.

Nothing failed is not the same as everything ran.

Part 3 of my Cloud & DevOps notes.
