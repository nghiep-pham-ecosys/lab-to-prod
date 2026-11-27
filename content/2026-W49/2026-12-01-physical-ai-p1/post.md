---
date: 2026-12-01
series: physical-ai
part: 1
title: "Where is the sensor? Frame order in tf2"
channels: [linkedin, facebook, telegram, x_manual]
short_publish_at: null
sources:
  - https://github.com/ros-infrastructure/rep/blob/master/rep-0105.rst
  - https://github.com/ros-infrastructure/rep/blob/master/rep-0103.rst
image_alt: "Code card: three 2D transforms, map to odom, odom to base_link turned 90 degrees, base_link to sensor. Multiplied as map_odom @ odom_base @ base_sensor they put the sensor at (3.0, 0.2) in the map; reversed (a toy example), at (1.2, 2.0)."
status: approved
work: pai-tf2-frames
card:
  layout: code
  theme: dark
  headline: "Same three transforms, wrong order: 2.55 m off"
  code:
    - "map_odom    = transform(2.0, 0.0, 0.0)"
    - "odom_base   = transform(1.0, 0.0, pi / 2)"
    - "base_sensor = transform(0.2, 0.0, 0.0)"
    - "> map_odom @ odom_base @ base_sensor  # (3.0, 0.2)"
    - "base_sensor @ odom_base @ map_odom  # (1.2, 2.0)"
  lesson: "Chain root first, so the frame names cancel."
---

## linkedin

(3.0, 0.2) or (1.2, 2.0): in a toy check I wrote for this post, the same three transforms put a robot's sensor in two places 2.55 m apart. Only the order of the product changed.

This comes from lesson 02 of physic-ai-for-everyone, a ROS 2 course I am writing in English and Vietnamese. The lesson covers coordinate frames and tf2, the ROS 2 library that keeps track of them.

The frames follow REP-105: map -> odom -> base_link, and I hang a sensor under base_link. Each frame has one parent, except the root, map. The lesson's exercise freezes one instant:

odom is 2.0 m along x of map.
base_link is at (1, 0) in odom, turned 90 degrees left.
sensor is 0.2 m straight ahead of base_link.

Each transform is a 3x3 matrix that maps a point from a child frame into its parent. Multiply from the root down: map_odom @ odom_base @ base_sensor gives (3.0, 0.2). The robot faces +y, so "ahead" is +y in the map.

Reverse the product and you get (1.2, 2.0). No error and no warning, just a wrong place.

tf2 does this walk for you with lookup_transform('map', 'sensor', time). A test in the lesson composes the three matrices by hand and checks that tf2's answer matches within 1e-6.

The lesson: write each transform as parent_child and check that the frame names cancel in the middle, map_odom, odom_base, base_sensor. If they do not, the order is wrong.

When a robot puts a sensor reading in the wrong place, what do you check first?

Part 1 of my Physical AI notes.

#ROS2 #Robotics #PhysicalAI #Python

## x

(3.0, 0.2) or (1.2, 2.0): the same 3 transforms put a robot's sensor 2.55 m apart (toy example). Only the order changed.

Chain them root first, map_odom @ odom_base @ base_sensor, so the frame names cancel in the middle.

## facebook

A robot needs to know where each part of it is. Its camera or sensor sits on the robot, the robot sits somewhere on the map, and every step is a move plus a turn.

A lesson in my ROS 2 course combines three such steps to find a sensor on the map. In the right order, the answer is (3.0, 0.2). In a toy check for this post, the reverse order gave (1.2, 2.0), 2.55 m away. Nothing warns you.

The lesson: start from the map and walk down to the sensor, one parent at a time.

Part 1 of my Physical AI notes.

## telegram

(3.0, 0.2) or (1.2, 2.0): the same three 2D transforms put a robot's sensor 2.55 m apart (toy example). Only the order changed.

The frame tree follows REP-105: map -> odom -> base_link, plus a sensor under base_link. At one instant: odom is 2.0 m along x of map, base_link is at (1, 0) in odom turned 90 degrees left, the sensor is 0.2 m ahead of base_link.

Root first, map_odom @ odom_base @ base_sensor = (3.0, 0.2). Reversed, (1.2, 2.0), with no error.

tf2's lookup_transform does this walk for you. The lesson's test checks it against the hand-composed matrices within 1e-6.

Part 1 of my Physical AI notes.
