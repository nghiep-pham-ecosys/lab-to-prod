---
date: 2026-12-02
series: simulation
part: 4
title: "A valid range is not a promise of accuracy"
channels: [linkedin, facebook, telegram, x_manual, youtube]
short_publish_at: 2026-12-03T19:00:00+07:00
sources:
  - https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=4
  - https://iapws.org/technical-guidance/release/IF97-Rev
image_alt: "A stat card: 0.47 K, how far the Stull Antoine fit for water in the NIST WebBook is from the IAPWS-IF97 boiling temperature at 373 K, still inside its valid range. The Bridgeman and Aldrich fit with the same range is about 0.025 K high."
status: approved
work: psl-antoine-lmtd
card:
  layout: stat
  theme: yellow
  headline: "A valid range is not a promise of accuracy"
  stat:
    value: "0.47 K"
    label: "off, inside the valid range"
    note: "Water at 373 K, one NIST fit against IAPWS-IF97."
  lesson: "Test every fit against reference data."
---

## linkedin

0.47 K: how far one NIST Antoine fit for water misses the reference boiling temperature at 373 K. That point is still inside the fit's valid range.

Two weeks ago I added vapour pressure to process-sim-lab, my small process simulator in Python. It uses the Antoine equation, log10(P/bar) = A - B / (T + C), with NIST WebBook constants for benzene, toluene and ethylbenzene.

Each fit carries the temperature range of its data, and my code raises an error outside it. A test adds a second guard: each fit must hit NIST's normal boiling point within the uncertainty NIST states.

Water is not in the table. At 1 atm it boils at about 373.12 K (IAPWS-IF97), and NIST's water fits end at 373 K or start at 379 K. No fit covers 1 atm, so that test cannot run for water.

For this post I checked two water fits that end at 373 K against IAPWS-IF97, the reference equation for water, inside their ranges:

Bridgeman and Aldrich: 0.023 to 0.025 K high from 350 to 373 K.
Stull: 0.27 K low at 330 K, 0.39 K high at 370 K, 0.47 K high at 373 K.

The range check accepts both. Only reference data tells them apart.

The lesson: a valid range says where a fit may be used, not how good it is there. Test every fit against a reference value inside its range.

Which fitted correlations in your code have you checked against reference data, not just their range?

Part 4 of my Simulation notes.

#ChemicalEngineering #ProcessSimulation #Thermodynamics #Python

## x

0.47 K: how far a NIST Antoine fit for water misses the IAPWS boiling temperature at 373 K, still inside its valid range.

Another fit with the same range is about 0.025 K high. A range check accepts both.

Test every fit against reference data, not just its range.

## facebook

Engineers predict how easily a liquid boils with a short formula and three fitted numbers. Each set comes with the temperatures it was fitted on, and my small process simulator refuses to use a set outside them.

But a range is not a quality mark. I compared two published sets for water with the international reference equation. At the temperatures I checked inside their own ranges, one was about 0.025 degrees high. The other was 0.47 degrees off at 373 K. The range check accepts both.

The lesson: also test every fitted formula against trusted reference values.

Part 4 of my Simulation notes.

## telegram

0.47 K: how far one NIST Antoine fit for water misses the IAPWS-IF97 boiling temperature at 373 K, inside its own valid range.

My simulator stores the range of every Antoine fit (benzene, toluene, ethylbenzene, NIST constants) and raises an error outside it. A test also checks each fit against NIST's normal boiling point. Water is left out: no NIST water fit covers 1 atm.

Two water fits that end at 373 K, against IAPWS-IF97: Bridgeman and Aldrich is about 0.025 K high from 350 to 373 K; Stull drifts to 0.47 K high at 373 K. The range check accepts both.

Lesson: a valid range says where a fit may be used, not how good it is there.

Part 4 of my Simulation notes.

## youtube

Antoine Fits for Water: 0.47 K Off Inside the Valid Range #Shorts
Two NIST Antoine fits for water, both valid up to 373 K, checked against the IAPWS-IF97 reference at 373 K: one is about 0.025 K high, the other 0.47 K.
Why a range check is not enough and every fit needs a reference test. Part 4 of my Simulation notes.
