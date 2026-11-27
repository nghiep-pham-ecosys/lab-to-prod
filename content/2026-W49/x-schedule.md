# X posts to schedule by hand: 2026-W49

On x.com: compose, attach the image, add the alt text, choose Schedule. After each post goes live, reply with its blog link.

## Mon 30 Nov, 08:30

Image: `2026-11-30-sim-p3/image.png`  
Alt text: A table card: conversion of N equal stirred tanks in series against one plug-flow reactor at k tau = 2. 1 tank gives X = 0.667, 10 tanks 0.838, 2000 tanks 0.86453, the plug-flow reactor 0.86466: a gap of 1.35e-4.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-30-sim-p3/

```text
2000 stirred tanks in series came within 1.35e-4 of one plug-flow reactor in my simulator.

The leading error term predicted it: (k tau)^2 e^(-k tau) / 2N.

So the test allows 2e-4, not a round 1e-2. That one would pass with just 27 tanks.
```

## Tue 01 Dec, 08:30

Image: `2026-12-01-physical-ai-p1/image.png`  
Alt text: Code card: three 2D transforms, map to odom, odom to base_link turned 90 degrees, base_link to sensor. Multiplied as map_odom @ odom_base @ base_sensor they put the sensor at (3.0, 0.2) in the map; reversed (a toy example), at (1.2, 2.0).  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-12-01-physical-ai-p1/

```text
(3.0, 0.2) or (1.2, 2.0): the same 3 transforms put a robot's sensor 2.55 m apart (toy example). Only the order changed.

Chain them root first, map_odom @ odom_base @ base_sensor, so the frame names cancel in the middle.
```

## Wed 02 Dec, 08:30

Image: `2026-12-02-sim-p4/image.png`  
Alt text: A stat card: 0.47 K, how far the Stull Antoine fit for water in the NIST WebBook is from the IAPWS-IF97 boiling temperature at 373 K, still inside its valid range. The Bridgeman and Aldrich fit with the same range is within 0.025 K.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-12-02-sim-p4/

```text
0.47 K: how far a NIST Antoine fit for water misses the IAPWS boiling temperature at 373 K, still inside its valid range.

Another fit with the same range stays within 0.025 K. A range check accepts both.

Test every fit against reference data, not just its range.
```
