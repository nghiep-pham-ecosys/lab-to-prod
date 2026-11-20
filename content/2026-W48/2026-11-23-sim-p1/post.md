---
date: 2026-11-23
series: simulation
part: 1
title: "A CSTR checked against algebra"
channels: [linkedin, facebook, telegram, x_manual, youtube]
short_publish_at: 2026-11-24T19:00:00+07:00
sources:
  - https://sites.engineering.ucsb.edu/~jbraw/chemreacfun/ch4/slides-matbal.pdf
  - https://sites.engineering.ucsb.edu/~jbraw/chemreacfun/
image_alt: "A card with the figure 4 of 5: the reactor tests of a CSTR model that still passed after its formula was swapped for the wrong one, X = 1 - exp(-k tau). Only the test against the closed form X = k tau / (1 + k tau) failed."
status: approved
work: psl-cstr-skeleton
card:
  layout: stat
  theme: light
  headline: "Sanity checks passed a wrong reactor model"
  stat:
    value: "4/5"
    label: "tests passed with the wrong formula"
    note: "Only the test against X = k tau / (1 + k tau) failed."
  lesson: "Test every model against one exact answer."
---

## linkedin

4 of my 5 reactor tests still passed after I swapped the wrong formula into my model.

This is week 1 of process-sim-lab, a small chemical process simulation library I am building in public. The first unit is an isothermal CSTR, a stirred tank reactor, with one first-order reaction, A to B.

At steady state the mole balance on A has a closed form: X = k tau / (1 + k tau), with tau = V / Q.

The merged pull request has 8 tests: 3 for the stream type, 5 for the reactor. Four reactor tests check properties: moles are conserved, zero rate gives zero conversion, conversion rises with volume and stays below 1, bad inputs are rejected.

One test checks the algebra: k = 0.01 1/s, V = 2 m3 and Q = 0.004 m3/s give tau = 500 s and X = 5/6, to 12 decimal places.

Then I tried to break it. I swapped in X = 1 - exp(-k tau), the formula of a plug-flow reactor. Conversion went from 0.8333 to 0.9933. Moles were still conserved. Conversion still rose with volume. Only the closed-form test failed.

Property checks describe any reactor. The closed form describes this one.

The limits: a closed form exists only for simple cases like this one (isothermal, first order, constant density). And it only proves that the code matches my derivation, so the derivation needs a textbook source too.

The lesson: give every model at least one case with an exact answer, and test it with a tight tolerance.

When your simulation has no closed-form answer, what do you test it against?

Part 1 of my Simulation notes.

#ChemicalEngineering #ProcessSimulation #Python #SoftwareTesting

## x

4 of 5 reactor tests still passed when I swapped the wrong formula into my CSTR model.

Moles conserved, conversion rising with volume: any reactor does that. Only the test against the closed form X = k tau / (1 + k tau) failed.

Give every model one case with an exact answer.

## facebook

I put the wrong formula into my reactor model on purpose, and 4 of its 5 tests still passed.

The model is a stirred tank reactor, the first piece of a small process simulation library I am building in public. Four of its tests check things that are true for any reactor, for example: nothing is created or lost, and a bigger tank converts more.

Only one test compares the model with the exact answer from algebra, 5/6 for a given tank and flow. That was the only test that caught the wrong formula.

If a model has a case with an exact answer, test against it.

Part 1 of my Simulation notes.

## telegram

4 of 5 reactor tests still passed after I swapped the wrong formula into my CSTR model.

The model: an isothermal stirred tank with one first-order reaction A -> B. Closed form: X = k tau / (1 + k tau).

The wrong formula: X = 1 - exp(-k tau), the plug-flow one. Conversion went from 0.8333 to 0.9933. Mole balance, zero rate and "rises with volume" tests all passed. Only the test against the closed form failed.

Property checks describe any reactor. The closed form describes this one. Give every model one case with an exact answer.

Part 1 of my Simulation notes.

## youtube

Reactor Model Testing: 4 of 5 Tests Passed a Wrong Formula #Shorts
A CSTR model with 5 tests gets the wrong formula, X = 1 - exp(-k tau). 4 tests still pass; only the test against X = k tau / (1 + k tau) fails.
Why property checks are not enough and why every model needs one exact answer. Part 1 of my Simulation notes.
