---
date: 2026-11-20
series: climate-ai
part: 1
title: "How ML weather forecasting differs from physics-based models"
channels: [linkedin, facebook, telegram, x_manual]
short_publish_at: null
sources:
  - https://arxiv.org/abs/2212.12794
  - https://www.ecmwf.int/en/about/media-centre/news/2025/ecmwfs-ai-forecasts-become-operational
image_alt: "A card with the figure under 1 minute: the time the GraphCast machine learning model needs for a 10-day global weather forecast at 0.25 degree resolution."
status: approved
card:
  layout: stat
  theme: copper
  headline: "An ML model forecasts 10 days of global weather in under"
  stat:
    value: "1 min"
    label: "GraphCast, 0.25 degree grid"
    note: "Source: Lam et al., GraphCast (arXiv 2212.12794)."
  lesson: "Fast, but it still stands on physics twice."
---

## linkedin

10 days of global weather in under 1 minute. That is what the GraphCast model produces at 0.25 degree resolution, according to its authors.

I come from chemistry, where a simulation means solving equations step by step. Weather forecasting worked the same way for decades, so I wanted to understand what the ML models do differently.

A physics-based model divides the atmosphere into a grid and solves the equations of fluid motion and thermodynamics forward in time. It is trusted and it is expensive.

An ML model skips the equations at forecast time. It is trained on decades of past atmospheric states and learns the mapping from "the atmosphere now" to "the atmosphere a few hours later". Then it repeats that step.

The GraphCast paper reports better scores than the most accurate operational deterministic systems on 90% of 1,380 verification targets. ECMWF, the European forecasting centre, put its own ML model into operations on 25 February 2025 and reports about 1,000 times less energy to make a forecast.

Here is the part that is easy to miss. The ML model still stands on physics twice. Its training data is reanalysis, which is built with a physics-based model plus observations. And ECMWF runs its ML model side by side with the physics-based one, from the same initial conditions.

The lesson: ML did not replace the physics here. It learned a fast shortcut from it, which is how I now look at ML surrogates in any simulation field.

Part 1 of my Climate x AI notes.

#ClimateAI #WeatherForecasting #MachineLearning #ClimateTech

## x

10 days of global weather in under 1 minute: that is GraphCast, an ML model (Lam et al.).

It skips the equations but still leans on physics: it is trained on reanalysis. And ECMWF runs its own ML model from the same initial conditions as its physics-based one.

## facebook

An ML model can now produce a 10-day global weather forecast in under one minute. That figure comes from the authors of a model called GraphCast.

Traditional forecasting solves the equations of the atmosphere step by step on a supercomputer. The ML model does not solve them. It has learned from decades of past weather what the atmosphere usually does next.

It still depends on physics. Its training data is built with a physics-based model. And Europe's forecasting centre starts its own ML model from the same initial picture of the atmosphere as its physics-based one.

ML did not replace the physics. It learned a fast shortcut from it.

Part 1 of my Climate x AI notes.

## telegram

An ML model (GraphCast) makes a 10-day global weather forecast in under 1 minute.

Physics-based models solve the equations of the atmosphere step by step. ML models learn the step "now -> a few hours later" from decades of past data.

But ML still leans on physics: the training data (reanalysis) comes from a physics-based model plus observations, and ECMWF starts its own ML model from the same initial conditions as its physics-based one.

Part 1 of my Climate x AI notes.
