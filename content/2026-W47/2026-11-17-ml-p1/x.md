<!-- X post for 2026-11-17. Schedule on x.com for Tue 17 Nov 08:30 (UTC+07:00).
     Attach: image.png   Alt text: Code: a 2 by 3 matrix W times a vector x of 3 numbers, plus a bias, gives the 2 numbers 6.1 and minus 0.5. That is one neural network layer.
     First reply after it is live: https://nghiep-pham-ecosys.github.io/lab-to-prod/notes/2026-11-17-ml-p1/
-->

2 rows, 3 columns: that is a full neural network layer with 2 neurons and 3 inputs.

Each row of W is one neuron taking a weighted sum of x. W @ x + b, then ReLU.

Rows are outputs, columns are inputs. Shape errors get much easier to read.
