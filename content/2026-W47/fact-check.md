# Fact-check, 2026-W47

Checked on 12 Nov 2026. "Ran" means the file was executed and its output matches the text.
"Sourced" means the page was opened and the quoted words were found there.

## 2026-11-16-dsa-p2 (Java == vs equals)

| Claim | Outcome | Evidence |
| --- | --- | --- |
| `Integer a = 127, b = 127; a == b` is true | Ran | `IntegerCache.java`, run by the validate job on GitHub Actions (JDK 21); output equals `IntegerCache.expected` |
| `Integer c = 128, d = 128; c == d` is false | Ran | same |
| `c.equals(d)` is true | Ran | same |
| Two strings with the same characters can be different objects | Ran | same file: `"lab" == new String("lab")` is false |
| Java guarantees shared Integer objects for -128 to 127 | Common knowledge | Java Language Specification, section 5.1.7 sets this range as a minimum; above it the result depends on the JVM (false by default). The post says "can be false" and "on a default JVM" for that reason |

Not run on the author's machine (no JDK installed); the CI run is the evidence.

## 2026-11-17-ml-p1 (matrix-vector product)

| Claim | Outcome | Evidence |
| --- | --- | --- |
| `W @ x + b` = [6.1, -0.5] | Ran | `layer.py`, output in `layer.expected` |
| Neuron 1: 0.5 x 2 - 1.0 x 1 + 2.0 x 3 + 0.1 = 6.1 | Ran | last line of `layer.py` |
| ReLU gives [6.1, 0] | Ran | `layer.py` |
| Stacked linear layers without activation collapse into one | Common knowledge | product of matrices is a matrix; with biases the composition is still affine |

## 2026-11-18-ai-eng-p2 (precision and recall)

| Claim | Outcome | Evidence |
| --- | --- | --- |
| precision 8/10 = 0.80, recall 8/13 = 0.62 | Ran | `quality_gate.py` |
| 5 of 13 bad answers passed, 38% | Ran | `quality_gate.py` |
| Labelled as a toy example | Checked | LinkedIn, X, Facebook, Telegram texts and the image note all say "toy example" |

## 2026-11-19-cloud-p2 (VPN or Direct Connect)

| Claim | Outcome | Evidence |
| --- | --- | --- |
| Standard VPN tunnel: up to 1.25 Gbps | Sourced | docs.aws.amazon.com/vpn/latest/s2svpn/vpn-limits.html: "Maximum bandwidth per standard VPN tunnel: Up to 1.25 Gbps" |
| A Site-to-Site VPN connection has two tunnels | Sourced | docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html: "Each Site-to-site VPN connection has two tunnels" |
| Dedicated Direct Connect ports: 1, 10, 100, 400 Gbps | Sourced | docs.aws.amazon.com/directconnect/latest/UserGuide/dedicated_connection.html: "The possible values are 1 Gbps, 10 Gbps, 100 Gbps, and 400 Gbps." |
| Port provisioning can take up to 72 business hours | Sourced | same page: "It can take up to 72 business hours for AWS to review your request and provision a port" |
| Direct Connect is not encrypted by default; options are MACsec or VPN over it | Sourced | .../encryption-in-transit.html: "AWS Direct Connect does not encrypt your traffic that is in transit by default." |

Softened: the draft said a VPN is "ready in minutes" and Direct Connect takes "weeks". Neither
is in the documentation, so the post now says "quick to set up" and quotes the 72 business hours.
Left out: the 5 Gbps large bandwidth tunnel (only with Transit Gateway or Cloud WAN); the post
says "standard tunnel" so the 1.25 Gbps figure stays correct.

## 2026-11-20-climate-p1 (ML weather forecasting)

| Claim | Outcome | Evidence |
| --- | --- | --- |
| GraphCast: 10 days, 0.25 degree, under one minute | Sourced | arxiv.org/abs/2212.12794 abstract: "over 10 days at 0.25 degree resolution globally, in under one minute" |
| Better than the most accurate operational deterministic systems on 90% of 1,380 targets | Sourced | same abstract; the post uses the abstract's wording and does not name a specific system |
| Trained on reanalysis | Sourced | same abstract: "can be trained directly from reanalysis data" |
| ECMWF took its ML model into operations on 25 February 2025 | Sourced | ecmwf.int news item of that date |
| About 1,000 times less energy to make a forecast | Sourced | same page: "a reduction of approximately 1,000 times in energy use for making a forecast" |
| Runs side by side with the physics-based model, same initial conditions | Sourced | same page: "side by side with its traditional physics-based Integrated Forecasting System"; "uses the same initial conditions" |
| Reanalysis is built with a physics-based model plus observations | Common knowledge | definition of reanalysis (data assimilation into a forecast model) |

Left out: the hardware GraphCast ran on (not in the abstract) and its time step.

## Article: Build log #1

| Claim | Outcome | Evidence |
| --- | --- | --- |
| 71 tests | Ran | `python -m pytest -q`: 71 passed |
| 8 pull requests for the build | Checked | pull requests 1 to 8 of the repository |
| 5 API channels, 2 manual | Checked | `publish/config.yaml` |
| Validator is about 500 lines | Checked | `wc -l tools/validate.py`: 521 |
| Hashnode API is paid since 13 May 2026 | Sourced | hashnode.com/announcements/graphql-api: "Every API request, queries and mutations, now requires a Pro plan" |
| YouTube: unverified projects no longer locked to private | Sourced | developers.google.com/youtube/v3/revision_history, entry of 2 Nov 2026; flagged in the article as unconfirmed until a real upload |

Softened: "render in about a minute each" became "a minute or two" (not timed precisely).

## Changes after the first judging round

- DSA: "128 == 128 is false" became "can be false" / "on a default JVM"; the cache range is stated as a guarantee, not a limit.
- AI Eng: "my quality gate" became "a quality gate" (the gate is a toy example).
- Cloud: added the two AWS pages the figures come from to `sources`; "1 to 400 Gbps" now says "dedicated ports".
- Climate: the short texts attributed "same initial conditions" to GraphCast; the source says it about ECMWF's own model. Fixed in X, Facebook and Telegram. The LinkedIn hook now starts with a number.
