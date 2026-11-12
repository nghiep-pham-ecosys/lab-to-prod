"""Toy example: one neural network layer is a matrix-vector product, a bias and a ReLU.

Run: python layer.py   (needs numpy)
"""
import numpy as np

W = np.array([[0.5, -1.0, 2.0],
              [1.5, 0.0, -0.5]])   # 2 neurons, 3 inputs each
x = np.array([2.0, 1.0, 3.0])      # 3 input features
b = np.array([0.1, -2.0])          # one bias per neuron

z = W @ x + b
a = np.maximum(z, 0)               # ReLU

print("W shape:", W.shape, "x shape:", x.shape)
print("W @ x     =", W @ x)
print("W @ x + b =", z)
print("ReLU      =", a)
print("by hand, neuron 1:", 0.5 * 2 + -1.0 * 1 + 2.0 * 3 + 0.1)
