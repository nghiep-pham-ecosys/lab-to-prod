<!-- X post for 2026-12-01. Schedule on x.com for Tue 01 Dec 08:30 (UTC+07:00).
     Attach: image.png   Alt text: Code card: three 2D transforms, map to odom, odom to base_link turned 90 degrees, base_link to sensor. Multiplied as map_odom @ odom_base @ base_sensor they put the sensor at (3.0, 0.2) in the map; reversed (a toy example), at (1.2, 2.0).
     First reply after it is live: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-12-01-physical-ai-p1/
-->

(3.0, 0.2) or (1.2, 2.0): the same 3 transforms put a robot's sensor 2.55 m apart (toy example). Only the order changed.

Chain them root first, map_odom @ odom_base @ base_sensor, so the frame names cancel in the middle.
