---
date: 2026-11-16
series: dsa-in-java
part: 2
title: "Java == vs equals: same value, different object"
channels: [linkedin, facebook, telegram, x_manual, youtube]
short_publish_at: 2026-11-17T19:00:00+07:00
sources: []
image_alt: "Java code: two Integer variables holding 127 compare true with ==, two holding 128 compare false, and equals returns true."
status: approved
card:
  layout: code
  theme: paper
  headline: "Same value, different object"
  code:
    - "Integer a = 127, b = 127;"
    - "a == b        // true"
    - "Integer c = 128, d = 128;"
    - "> c == d        // false"
    - "c.equals(d)   // true"
  lesson: "== compares references. equals() compares values."
---

## linkedin

128 == 128 can be false in Java. 127 == 127 is always true. Same code, same types, one number apart.

I hit this in week 2 of my data structures course and it took me longer than I want to admit.

Integer a = 127, b = 127;
a == b is true.

Integer c = 128, d = 128;
c == d is false on a default JVM.

Here is what is going on. Integer is an object, not a primitive. On objects, == does not compare values. It asks: are these two variables pointing at the same object in memory?

The language guarantees a cache of Integer objects for -128 to 127. When you write Integer a = 127, Java hands you the cached object, so a and b point at the same one and == says true. Above 127 nothing is guaranteed. A default JVM creates two separate objects with the same value, and == says false.

The same trap exists for String. Two strings built at runtime with the same characters are usually two different objects.

c.equals(d) is true in every case, because equals() compares the values.

Why this matters for data structures: every search, every contains(), every hash map lookup depends on the right notion of "equal". Use == there and your tests pass with small numbers and fail in production with big ones.

The rule I use now: == for primitives (int, char, boolean). equals() for everything that is an object.

Part 2 of my DSA in Java notes.

#Java #DataStructures #LearningInPublic #SoftwareEngineering

## x

128 == 128 can be false in Java. 127 == 127 is always true.

Integer is an object, and == compares references, not values. Java only guarantees shared Integer objects from -128 to 127, so small numbers "work" by accident.

Use equals() for objects.

## facebook

128 == 128 can be false in Java, but 127 == 127 is always true.

The reason: Integer is an object, and on objects == asks "is this the same object in memory?", not "is this the same value?". Java keeps a cache of Integer objects from -128 to 127, so small numbers share one object and the comparison works by accident. Above 127 a default JVM gives you two different objects with the same value.

The fix is one habit: use == for primitives like int, and equals() for objects like Integer and String.

Part 2 of my DSA in Java notes.

## telegram

128 == 128 can be false in Java. 127 == 127 is always true.

Integer is an object, and == compares references. Java only guarantees shared Integer objects from -128 to 127, so small numbers work by accident.

Rule: == for primitives, equals() for objects.

Part 2 of my DSA in Java notes.

## youtube

Java == vs equals: Why 128 == 128 Can Be False #Shorts
Why two Integer variables holding 128 are not == on a default JVM, while 127 always works: == compares references, and Java caches Integer objects from -128 to 127.
Use equals() to compare objects. Part 2 of my DSA in Java notes. Code and full note on the blog.
