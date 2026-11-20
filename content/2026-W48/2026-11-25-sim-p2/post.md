---
date: 2026-11-25
series: simulation
part: 2
title: "A flash drum: check both ends, then bisect"
channels: [linkedin, facebook, telegram, x_manual]
short_publish_at: null
sources:
  - https://doi.org/10.2118/952327-G
image_alt: "Code card: the Rachford-Rice function checked at both ends, f(0) = sum(z*K) - 1 and f(1) = 1 - sum(z/K). f(0) at or below 0 means all liquid, f(1) at or above 0 means all vapour, otherwise bisection on [0, 1] finds the vapour fraction in 40 steps."
status: approved
work: psl-flash-rachford-rice
card:
  layout: code
  theme: yellow
  headline: "Check both ends before you bisect"
  code:
    - "f(0) = sum(z*K) - 1"
    - "f(1) = 1 - sum(z/K)"
    - "f(0) <= 0   # all liquid"
    - "f(1) >= 0   # all vapour"
    - "> else bisect [0, 1]: 40 steps"
  lesson: "The ends say if a root is in range, and bracket it."
---

## linkedin

40 bisection steps, and my flash drum's vapour fraction matched the exact answer to within 5e-13. The steps were easy. Two checks before them did the real work.

Last week I added an isothermal flash drum to process-sim-lab, my small process simulator in Python. The K-values are given and do not change with composition: the ideal-mixture case.

It rests on one equation, Rachford-Rice:

f(psi) = sum z_i (K_i - 1) / (1 + psi (K_i - 1)) = 0

psi is V/F, the share of the feed that leaves as vapour.

Before solving, look at the two ends:
f(0) = sum z_i K_i - 1. At 0 or below, the feed is at or below its bubble point: all liquid.
f(1) = 1 - sum z_i / K_i. At 0 or above, it is at or above its dew point: all vapour.

Otherwise f(0) > 0 > f(1). With every K above 0, f falls steadily on [0, 1] and has no pole there, so exactly one root sits inside and bisection cannot miss it. Halving [0, 1] until it is narrower than 1e-12 takes 40 steps.

Skip the checks and the equation still has a root, an unphysical one. In my toy all-liquid binary (z = 0.5 and 0.5, K = 0.8 and 0.3), the only root is psi = 3.21: a vapour fraction above 1.

The lesson: evaluate an equation at both ends of the physical range before a solver sees it. The ends say whether a root lies in range and give you the bracket.

When you wrap a numerical solver in a model, what do you check before you call it?

Part 2 of my Simulation notes.

#ProcessSimulation #ChemicalEngineering #Python #NumericalMethods

## x

40 bisection steps put my flash drum's vapour fraction within 5e-13 of the exact answer.

The real work came first: check Rachford-Rice at psi = 0 and psi = 1. All liquid, all vapour, or a bracket with exactly one root inside.

## facebook

A mixture that enters a flash drum leaves as part vapour, part liquid. How much leaves as vapour comes from one equation.

Last week I added this unit to my small process simulator. The trick is to test the equation at its two ends before solving it. At "no vapour" and "all vapour" the signs tell you whether the feed stays liquid, turns fully to vapour, or splits. When it splits, the answer is trapped between 0 and 1, and halving that range 40 times found it to within 5e-13.

The lesson: look at the ends of the range before you solve.

Part 2 of my Simulation notes.

## telegram

40 bisection steps found my flash drum's vapour fraction to within 5e-13 of the exact answer.

The steps were the easy part. Before solving Rachford-Rice, check its two ends:
f(0) = sum z_i K_i - 1 <= 0: all liquid.
f(1) = 1 - sum z_i / K_i >= 0: all vapour.
Otherwise, with every K > 0, f falls steadily on [0, 1], so exactly one root sits inside and bisection cannot miss it.

Skip the checks and a toy all-liquid feed still has a root: psi = 3.21, a vapour fraction above 1.

Part 2 of my Simulation notes.
