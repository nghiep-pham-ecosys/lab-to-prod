---
date: 2026-11-17
series: ml-foundations
part: 1
title: "A matrix-vector product is one neural network layer"
channels: [linkedin, facebook, telegram, x_manual]
short_publish_at: null
sources: []
image_alt: "Code: a 2 by 3 matrix W times a vector x of 3 numbers, plus a bias, gives the 2 numbers 6.1 and minus 0.5. That is one neural network layer."
status: approved
card:
  layout: code
  theme: copper
  headline: "One layer is one matrix times one vector"
  code:
    - "W = [[0.5, -1.0,  2.0],"
    - "     [1.5,  0.0, -0.5]]"
    - "x = [2, 1, 3]"
    - "b = [0.1, -2.0]"
    - "> W @ x + b   # [6.1, -0.5]"
  lesson: "2 rows, 2 neurons. 3 columns, 3 inputs. Toy example."
---

## linkedin

2 rows and 3 columns. That is a complete neural network layer with 2 neurons and 3 inputs.

For a long time I read "dense layer" and "matrix multiplication" as two separate topics. They are the same thing, and seeing it removed a lot of fog for me.

A toy example:

W = [[0.5, -1.0, 2.0], [1.5, 0.0, -0.5]]
x = [2, 1, 3]
b = [0.1, -2.0]

W @ x + b gives [6.1, -0.5].

Each row of W is one neuron. The first neuron computes 0.5 x 2 - 1.0 x 1 + 2.0 x 3 + 0.1 = 6.1. That is a weighted sum of the inputs, which is exactly what one row of a matrix-vector product does.

Then comes the activation. ReLU turns [6.1, -0.5] into [6.1, 0]. Without that step, stacking layers would be pointless: a matrix times a matrix is just another matrix, so ten linear layers collapse into one.

Why this helps in practice: shapes stop being magic. A weight matrix of shape (2, 3) takes 3 numbers in and gives 2 numbers out. When a framework reports a shape mismatch, I now read it as "the columns of this matrix do not match the length of that vector" and I know where to look.

The lesson: when a layer confuses you, write its matrix shape down. Rows are outputs, columns are inputs.

The script is in the repository.

Part 1 of my ML Foundations notes.

#MachineLearning #LinearAlgebra #DeepLearning #LearningInPublic

## x

2 rows, 3 columns: that is a full neural network layer with 2 neurons and 3 inputs.

Each row of W is one neuron taking a weighted sum of x. W @ x + b, then ReLU.

Rows are outputs, columns are inputs. Shape errors get much easier to read.

## facebook

A neural network layer is less mysterious than it sounds: it is one matrix multiplied by one list of numbers.

Take a matrix with 2 rows and 3 columns. Each row is one "neuron". It multiplies each of the 3 inputs by a weight and adds the results. Two rows, so two outputs. Add a small number called the bias, replace negative results with zero, and that is a complete layer.

In my toy example the inputs 2, 1 and 3 become 6.1 and 0.

A deep network repeats this step many times. The rule I remember: rows are outputs, columns are inputs.

Part 1 of my ML Foundations notes.

## telegram

A neural network layer is one matrix times one vector.

W has 2 rows and 3 columns: 2 neurons, 3 inputs. Each row takes a weighted sum of the inputs. Add a bias, apply ReLU, done.

Toy example: W @ x + b = [6.1, -0.5], and ReLU makes it [6.1, 0].

Rows are outputs, columns are inputs.

Part 1 of my ML Foundations notes.
