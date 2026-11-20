<!-- X post for 2026-11-25. Schedule on x.com for Wed 25 Nov 08:30 (UTC+07:00).
     Attach: image.png   Alt text: Code card: the Rachford-Rice function checked at both ends, f(0) = sum(z*K) - 1 and f(1) = 1 - sum(z/K). f(0) at or below 0 means all liquid, f(1) at or above 0 means all vapour, otherwise bisection on [0, 1] finds the vapour fraction in 40 steps.
     First reply after it is live: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-25-sim-p2/
-->

40 bisection steps put my flash drum's vapour fraction within 5e-13 of the exact answer.

The real work came first: check Rachford-Rice at psi = 0 and psi = 1. All liquid, all vapour, or a bracket with exactly one root inside.
