"""Isothermal flash: check Rachford-Rice at both ends of [0, 1], then bisect.

Same method as the flash drum in process-sim-lab (pull request #7), rewritten here in a few lines.
The K-values are given and fixed (the ideal-mixture case). The feeds are toy examples; the three
two-phase cases have an exact answer known in advance (two binaries solved in closed form, one
three-component case built backwards from psi = 0.25).

Run: python rachford_rice.py   (standard library only)
"""


def f(z, k, psi):
    """Rachford-Rice: f(psi) = sum z_i (K_i - 1) / (1 + psi (K_i - 1)), psi = V / F."""
    return sum(zi * (ki - 1.0) / (1.0 + psi * (ki - 1.0)) for zi, ki in zip(z, k))


def flash(z, k, tol=1e-12, max_iter=200):
    """Return (phase, psi, bisection steps)."""
    if sum(zi * ki for zi, ki in zip(z, k)) - 1.0 <= 0.0:    # f(0) <= 0: at or below the bubble point
        return "liquid", 0.0, 0
    if 1.0 - sum(zi / ki for zi, ki in zip(z, k)) >= 0.0:    # f(1) >= 0: at or above the dew point
        return "vapour", 1.0, 0
    lo, hi, steps = 0.0, 1.0, 0                              # f(lo) > 0 > f(hi): one root inside
    while hi - lo > tol and steps < max_iter:
        mid = 0.5 * (lo + hi)
        if mid in (lo, hi):
            break
        steps += 1
        if f(z, k, mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return "two-phase", 0.5 * (lo + hi), steps


CASES = [
    # name, z, K, exact psi (None for a single-phase feed)
    ("binary 1", (0.5, 0.5), (2.0, 0.5), 0.5),
    ("binary 2", (0.4, 0.6), (3.0, 0.2), 0.2),
    ("ternary", (0.2, 0.3, 0.5), (5.0, 1.0, 1.0 / 3.0), 0.25),
    ("all liquid", (0.5, 0.5), (0.8, 0.3), None),
    ("all vapour", (0.5, 0.5), (2.0, 4.0), None),
]

for name, z, k, exact in CASES:
    phase, psi, steps = flash(z, k)
    line = f"{name:10s}  f(0) = {f(z, k, 0.0):+.3f}  f(1) = {f(z, k, 1.0):+.3f}  {phase:9s}  psi = {psi:.6f}  steps = {steps}"
    if exact is not None:
        line += f"  error = {abs(psi - exact):.1e}"
    print(line)

print()
print("bracket width after 39 steps:", f"{2.0 ** -39:.2e}", " after 40 steps:", f"{2.0 ** -40:.2e}", " (tol = 1e-12)")

# Skip the end checks on the all-liquid feed: a binary Rachford-Rice equation is linear once the
# denominators are cleared, so its only root is psi = -(z1 a1 + z2 a2) / (a1 a2), a_i = K_i - 1.
z, k = (0.5, 0.5), (0.8, 0.3)
a1, a2 = k[0] - 1.0, k[1] - 1.0
root = -(z[0] * a1 + z[1] * a2) / (a1 * a2)
print("all-liquid feed, root of f without the end checks: psi =", f"{root:.4f}", " f(psi) =", f"{f(z, k, root):.1e}")
