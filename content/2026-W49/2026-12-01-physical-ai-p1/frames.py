"""Where is the sensor in the map? Compose three 2D rigid transforms, in two orders.

Frame tree of lesson 02 (coordinate frames and tf2) in physic-ai-for-everyone, at one instant
of its exercise 1:
    map -> odom          odom is 2.0 m along x of map
    odom -> base_link    the robot is at (1, 0) in odom, turned 90 degrees left
    base_link -> sensor  the sensor is 0.2 m along x of base_link (straight ahead)
A fresh stdlib version written for this post, not the lesson's code.

Run (Python 3.12, stdlib only):  python frames.py
"""
import math
from math import pi


class T:
    """A 2D rigid transform as a 3x3 matrix. Maps a point from the child frame to its parent."""

    def __init__(self, rows):
        self.rows = rows

    def __matmul__(self, other):
        a, b = self.rows, other.rows
        return T([[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)])

    def origin(self):
        """Where the child frame's origin lies in the parent frame, rounded to 6 decimals."""
        return round(self.rows[0][2], 6) + 0.0, round(self.rows[1][2], 6) + 0.0


def transform(x, y, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return T([[c, -s, x], [s, c, y], [0.0, 0.0, 1.0]])


map_odom    = transform(2.0, 0.0, 0.0)
odom_base   = transform(1.0, 0.0, pi / 2)
base_sensor = transform(0.2, 0.0, 0.0)

right = map_odom @ odom_base @ base_sensor  # (3.0, 0.2)
wrong = base_sensor @ odom_base @ map_odom  # (1.2, 2.0)

print("sensor in map, map_odom @ odom_base @ base_sensor:", right.origin())
print("same three transforms, reversed order:           ", wrong.origin())
print(f"distance between the two answers: {math.dist(right.origin(), wrong.origin()):.2f} m")
