<!-- X post for 2026-11-30. Schedule on x.com for Mon 30 Nov 08:30 (UTC+07:00).
     Attach: image.png   Alt text: A table card: conversion of N equal stirred tanks in series against one plug-flow reactor at k tau = 2. 1 tank gives X = 0.667, 10 tanks 0.838, 2000 tanks 0.86453, the plug-flow reactor 0.86466: a gap of 1.35e-4.
     First reply after it is live: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-30-sim-p3/
-->

2000 stirred tanks in series came within 1.35e-4 of one plug-flow reactor in my simulator.

The leading error term predicted it: (k tau)^2 e^(-k tau) / 2N.

So the test allows 2e-4, not a round 1e-2. That one would pass with just 27 tanks.
