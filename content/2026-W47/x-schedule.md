# X posts to schedule by hand: 2026-W47

On x.com: compose, attach the image, add the alt text, choose Schedule. After each post goes live, reply with its blog link.

## Mon 16 Nov, 08:30

Image: `2026-11-16-dsa-p2/image.png`  
Alt text: Java code: two Integer variables holding 127 compare true with ==, two holding 128 compare false, and equals returns true.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-16-dsa-p2/

```text
128 == 128 can be false in Java. 127 == 127 is always true.

Integer is an object, and == compares references, not values. Java only guarantees shared Integer objects from -128 to 127, so small numbers "work" by accident.

Use equals() for objects.
```

## Tue 17 Nov, 08:30

Image: `2026-11-17-ml-p1/image.png`  
Alt text: Code: a 2 by 3 matrix W times a vector x of 3 numbers, plus a bias, gives the 2 numbers 6.1 and minus 0.5. That is one neural network layer.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-17-ml-p1/

```text
2 rows, 3 columns: that is a full neural network layer with 2 neurons and 3 inputs.

Each row of W is one neuron taking a weighted sum of x. W @ x + b, then ReLU.

Rows are outputs, columns are inputs. Shape errors get much easier to read.
```

## Wed 18 Nov, 08:30

Image: `2026-11-18-ai-eng-p2/image.png`  
Alt text: A card showing recall 0.62: a quality gate with 80 percent precision still caught only 8 of 13 bad answers.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-18-ai-eng-p2/

```text
5 of 13 bad answers passed an LLM quality gate. Its precision was 80%.

Precision: of what the gate flagged, how much was bad? 8/10.
Recall: of what was bad, how much did it catch? 8/13.

One number hides the other. Report both, with counts. (Toy example.)
```

## Thu 19 Nov, 08:30

Image: `2026-11-19-cloud-p2/image.png`  
Alt text: Table comparing AWS Site-to-Site VPN (IPsec over the internet, up to 1.25 Gbps per standard tunnel) with Direct Connect (private line, dedicated ports from 1 to 400 Gbps, not encrypted by default).  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-19-cloud-p2/

```text
1.25 Gbps: the ceiling of one standard AWS Site-to-Site VPN tunnel.

VPN: IPsec over the internet, quick to set up.
Direct Connect: private line, dedicated ports from 1 to 400 Gbps, but NOT encrypted by default.

Private is not the same as encrypted.
```

## Fri 20 Nov, 08:30

Image: `2026-11-20-climate-p1/image.png`  
Alt text: A card with the figure under 1 minute: the time the GraphCast machine learning model needs for a 10-day global weather forecast at 0.25 degree resolution.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-20-climate-p1/

```text
10 days of global weather in under 1 minute: that is GraphCast, an ML model (Lam et al.).

It skips the equations but still leans on physics: it is trained on reanalysis. And ECMWF runs its own ML model from the same initial conditions as its physics-based one.
```
