"""Two NIST Antoine fits for water, checked against IAPWS-IF97 inside their own valid range.

Antoine constants: NIST Chemistry WebBook (SRD 69), water (CAS 7732-18-5), "Phase change data",
table "Antoine Equation Parameters", log10(P / bar) = A - B / (T / K + C), read 2026-11-27.
Both fits below end at 373 K. NIST's average normal boiling point on the same page is
373.17 +/- 0.04 K, so no NIST water fit covers 1 atm.

Reference: IAPWS-IF97 (Revised Release, 2007), region 4 saturation-pressure equation, Eq. (30) with
the coefficients of Table 34. The script first reproduces the release's own test values (Table 35).

For each temperature T inside a fit's range, the script takes the IAPWS saturation pressure at T,
solves the Antoine fit for the temperature at that pressure, and prints the difference: how far
the fit's boiling temperature is from the reference, inside the range it is valid for.

Run (Python 3.12, stdlib only):  python water_antoine.py
"""
import math

N = [0.0, 0.11670521452767e4, -0.72421316703206e6, -0.17073846940092e2, 0.12020824702470e5,
     -0.32325550322333e7, 0.14915108613530e2, -0.48232657361591e4, 0.40511340542057e6,
     -0.23855557567849, 0.65017534844798e3]   # IAPWS-IF97 Table 34, n1 to n10


def p_sat_iapws(t):
    """Saturation pressure of water in Pa, IAPWS-IF97 Eq. (30)."""
    th = t + N[9] / (t - N[10])
    a = th * th + N[1] * th + N[2]
    b = N[3] * th * th + N[4] * th + N[5]
    c = N[6] * th * th + N[7] * th + N[8]
    return 1e6 * (2 * c / (-b + math.sqrt(b * b - 4 * a * c))) ** 4


FITS = {  # name: (A, B, C, T_min, T_max), NIST WebBook rows for water
    "Bridgeman and Aldrich, 1964": (5.08354, 1663.125, -45.622, 344.0, 373.0),
    "Stull, 1947": (4.6543, 1435.264, -64.848, 255.9, 373.0),
}

print("IAPWS-IF97 Table 35 check (MPa): " + ", ".join(
    f"{t} K -> {p_sat_iapws(t) / 1e6:.9e}" for t in (300.0, 500.0, 600.0)))
for name, (a, b, c, t_min, t_max) in FITS.items():
    print(f"{name}, valid {t_min}-{t_max} K: fit T - reference T at the IAPWS pressure")
    for t in (300.0, 330.0, 350.0, 360.0, 370.0, 372.0, 373.0):
        if t_min <= t <= t_max:
            t_fit = b / (a - math.log10(p_sat_iapws(t) / 1e5)) - c
            print(f"  {t:.0f} K: {t_fit - t:+.3f} K")
