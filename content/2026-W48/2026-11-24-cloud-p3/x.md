<!-- X post for 2026-11-24. Schedule on x.com for Tue 24 Nov 08:30 (UTC+07:00).
     Attach: image.png   Alt text: Table of three broken CI runs, toy example: with tests skipped or the secret scan cancelled, a naive 'nothing failed' rule stays green while the ci-result rule turns red; a failed test is red under both.
     First reply after it is live: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-24-cloud-p3/
-->

6 checks reported on the PR that added my merge guard. 2 were skipped, and the summary check still went green. Correctly.

Rule: test and secret scan must succeed, other jobs may be skipped, cancelled is red.

A "nothing failed" rule passes 2 of 3 broken runs (toy example).
