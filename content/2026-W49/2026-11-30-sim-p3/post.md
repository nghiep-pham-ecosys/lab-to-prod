---
date: 2026-11-30
series: simulation
part: 3
title: "2000 small tanks become a pipe"
document_title: "2000 small tanks become a pipe: tolerance from the error term"
channels: [linkedin, facebook, telegram, x_manual, youtube]
short_publish_at: 2026-12-01T19:00:00+07:00
sources:
  - https://sites.engineering.ucsb.edu/~jbraw/chemreacfun/ch8/slides-mixing.pdf
  - https://sites.engineering.ucsb.edu/~jbraw/chemreacfun/ch4/slides-matbal.pdf
image_alt: "A table card: conversion of N equal stirred tanks in series against one plug-flow reactor at k tau = 2. 1 tank gives X = 0.667, 10 tanks 0.838, 2000 tanks 0.86453, the plug-flow reactor 0.86466: a gap of 1.35e-4."
status: approved
work: psl-pfr-mixer-splitter
card:
  layout: table
  theme: light
  headline: "Many small tanks become a pipe"
  rows:
    - ["1 tank", "X = 0.667"]
    - ["10 tanks", "X = 0.838"]
    - ["2000 tanks", "X = 0.86453"]
    - ["PFR", "X = 0.86466, gap 1.35e-4"]
  lesson: "Set a test's tolerance from the error term."
---

## linkedin

2000 stirred tanks in a row came within about 1.35e-4 of one plug-flow reactor in my simulator. The test predicted the size of that gap before it ran.

Two weeks ago I added an isothermal plug-flow reactor (PFR) to process-sim-lab, my small process simulation library in Python. One first-order reaction, A to B. Its closed form is X = 1 - exp(-k tau).

A PFR is the limit of many equal stirred tanks (CSTRs) in series. Chain N tanks and you get X = 1 - (1 + k tau / N)^-N, which tends to 1 - exp(-k tau) as N grows.

So one test chains 2000 calls to my CSTR model and compares the result with the PFR model. Two units, written separately, check each other.

The hard part is the tolerance. At k tau = 2, the gap is about (k tau)^2 exp(-k tau) / (2N): 0.0027 for 100 tanks, 1.35e-4 for 2000. The run gives about 1.35e-4.

The test allows 2e-4. Against that, a chain needs at least 1354 tanks to pass. A round 1e-2 would accept any chain of 27 tanks or more, so the comparison could no longer tell 2000 tanks from 27.

The limits: isothermal, first order, constant density, and the gap formula is only the leading term.

The lesson: when a test compares a model with a limit, work out how fast it converges, and set the tolerance from that.

When you compare two solvers or two models, how do you pick the tolerance?

Part 3 of my Simulation notes.

#ChemicalEngineering #ProcessSimulation #Python #SoftwareTesting

## x

2000 stirred tanks in series came within about 1.35e-4 of one plug-flow reactor in my simulator.

The leading error term predicted it: (k tau)^2 e^(-k tau) / 2N.

So the test allows 2e-4, not a round 1e-2. That one would pass with just 27 tanks.

## facebook

Split one stirred tank into many smaller ones in a row, and the chain starts to behave like a pipe.

I tested this in my small process simulator. One stirred tank converts 67% of the feed. A pipe-like reactor of the same size converts 86.5%. With 2000 small tanks in a row, the gap to the pipe was about 0.0135 percentage points.

The useful part was knowing that number in advance. A short formula predicts the gap, so my test can be strict. A loose test would also pass with only 27 tanks.

The lesson: before you compare two models, work out how close they should be.

Part 3 of my Simulation notes.

## telegram

2000 stirred tanks in series came within about 1.35e-4 of one plug-flow reactor (PFR) in my process simulator.

A PFR is the limit of N equal CSTRs in series: X_N = 1 - (1 + k tau / N)^-N tends to 1 - exp(-k tau). So one test chains 2000 calls to the CSTR model and compares with the PFR model.

At k tau = 2 the gap is about (k tau)^2 exp(-k tau) / 2N: 0.0027 for 100 tanks, 1.35e-4 for 2000. The test allows 2e-4, so a chain needs 1354 tanks to pass. A round 1e-2 would pass with 27.

Lesson: set a test's tolerance from the error term, not from habit.

Part 3 of my Simulation notes.

## youtube

CSTRs in Series vs PFR: 2000 Tanks Within About 1.35e-4 #Shorts
A first-order reaction in 1, 10 and 2000 equal stirred tanks in series, compared with one plug-flow reactor at k tau = 2.
The gap shrinks as 1/N and the test tolerance is set from it. Part 3 of my Simulation notes.
