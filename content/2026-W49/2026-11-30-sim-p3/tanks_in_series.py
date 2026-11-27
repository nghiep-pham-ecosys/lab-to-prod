"""N equal CSTRs in series against one PFR of the same total volume.

Isothermal, first-order A -> B, constant density. Same inputs as the test in process-sim-lab
PR #6 (tests/test_pfr.py): k = 0.02 1/s, V = 1 m3, Q = 0.01 m3/s, so tau = 100 s and Da = k tau = 2.

Each tank is solved with its own closed form, F_A,out = F_A,in / (1 + Da/N), and the tanks are
chained one after another, as the test does with 2000 calls. The PFR is X = 1 - exp(-Da).
The last column is the leading error term, Da^2 exp(-Da) / (2N).

Run (Python 3.12, stdlib only):  python tanks_in_series.py
"""
import math

k, volume, q = 0.02, 1.0, 0.01
tau = volume / q
da = k * tau
x_pfr = -math.expm1(-da)
print(f"tau = {tau:.0f} s, Da = {da:.0f}, PFR X = {x_pfr:.6f}")
print(f"{'N':>5} {'X (N tanks)':>12} {'PFR - X':>10} {'Da^2 e^-Da / 2N':>16}")
for n in (1, 2, 5, 10, 100, 2000):
    fa = 10.0                                  # mol/s of A in the feed
    for _ in range(n):
        fa = fa / (1.0 + k * (volume / n) / q)  # one tank of volume V/N
    x = 1.0 - fa / 10.0
    print(f"{n:>5} {x:>12.6f} {x_pfr - x:>10.2e} {da**2 * math.exp(-da) / (2 * n):>16.2e}")

# Which tank counts would a given tolerance accept? The gap shrinks as N grows, so the first N
# that passes is the weakest chain the test cannot tell from 2000 tanks.
for tol in (1e-2, 2e-4):
    n = 1
    while x_pfr - (1.0 - (1.0 + da / n) ** -n) >= tol:
        n += 1
    print(f"tolerance {tol:.0e}: any chain of {n} tanks or more passes")
