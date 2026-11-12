# X posts to schedule by hand: 2026-W47

On x.com: compose, attach the image, add the alt text, choose Schedule. After each post goes live, reply with its blog link.

## Mon 16 Nov, 08:30

Image: `2026-11-16-dsa-p2/image.png`  
Alt text: Java code: two Integer variables holding 127 compare true with ==, two holding 128 compare false, and equals returns true.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-16-dsa-p2/

```text
128 == 128 is false in Java. 127 == 127 is true.

Integer is an object, and == compares references, not values. Java caches Integer objects from -128 to 127, so small numbers share one object and "work" by accident.

Use equals() for objects.
```

## Wed 18 Nov, 08:30

Image: `2026-11-18-ai-eng-p2/image.png`  
Alt text: A card showing recall 0.62: a quality gate with 80 percent precision still caught only 8 of 13 bad answers.  
First reply: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-18-ai-eng-p2/

```text
5 of 13 bad answers passed my LLM quality gate. Its precision was 80%.

Precision: of what the gate flagged, how much was bad? 8/10.
Recall: of what was bad, how much did it catch? 8/13.

One number hides the other. Report both, with counts. (Toy example.)
```
