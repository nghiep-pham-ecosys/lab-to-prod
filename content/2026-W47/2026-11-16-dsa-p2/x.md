<!-- X post for 2026-11-16. Schedule on x.com for Mon 16 Nov 08:30 (UTC+07:00).
     Attach: image.png   Alt text: Java code: two Integer variables holding 127 compare true with ==, two holding 128 compare false, and equals returns true.
     First reply after it is live: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-16-dsa-p2/
-->

128 == 128 can be false in Java. 127 == 127 is always true.

Integer is an object, and == compares references, not values. Java only guarantees shared Integer objects from -128 to 127, so small numbers "work" by accident.

Use equals() for objects.
