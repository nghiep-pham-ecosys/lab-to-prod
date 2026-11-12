"""A toy digital twin of a draining tank: a physics model calibrated against sensor data.

The "plant" here is also simulated (with a different valve coefficient and sensor noise), so
every number is a toy example. The point is the loop: model -> compare with data -> calibrate.

Model: A * dh/dt = q_in - k * sqrt(h)
    h     liquid level [m]
    A     tank cross-section [m^2]
    q_in  inflow [m^3/s]
    k     valve coefficient [m^2.5/s]  (outflow follows Torricelli's law, proportional to sqrt(h))
"""
from __future__ import annotations

import numpy as np

AREA = 1.0       # m^2
Q_IN = 0.02      # m^3/s
K_TRUE = 0.012   # what the "real" valve does
K_GUESS = 0.010  # what the datasheet says
H0 = 1.0         # m
T_END = 1800.0   # s
DT = 1.0         # s


def dhdt(h: float, k: float, q_in: float = Q_IN, area: float = AREA) -> float:
    return (q_in - k * np.sqrt(max(h, 0.0))) / area


def simulate(k: float, h0: float = H0, t_end: float = T_END, dt: float = DT) -> tuple[np.ndarray, np.ndarray]:
    """Integrate the level with classical Runge-Kutta (RK4). Returns (time, level)."""
    t = np.arange(0.0, t_end + dt, dt)
    h = np.empty_like(t)
    h[0] = h0
    for i in range(len(t) - 1):
        k1 = dhdt(h[i], k)
        k2 = dhdt(h[i] + 0.5 * dt * k1, k)
        k3 = dhdt(h[i] + 0.5 * dt * k2, k)
        k4 = dhdt(h[i] + dt * k3, k)
        h[i + 1] = h[i] + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
    return t, h


def steady_state(k: float, q_in: float = Q_IN) -> float:
    """Level at which outflow equals inflow."""
    return (q_in / k) ** 2


def sensor(k: float = K_TRUE, every: int = 10, noise: float = 0.02, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    """Noisy level readings from the 'real' tank: one sample every `every` seconds."""
    t, h = simulate(k)
    rng = np.random.default_rng(seed)
    idx = np.arange(0, len(t), every)
    return t[idx], h[idx] + rng.normal(0.0, noise, size=len(idx))


def rmse(k: float, t_obs: np.ndarray, h_obs: np.ndarray) -> float:
    t, h = simulate(k)
    return float(np.sqrt(np.mean((np.interp(t_obs, t, h) - h_obs) ** 2)))


def calibrate(t_obs: np.ndarray, h_obs: np.ndarray, lo: float = 0.006, hi: float = 0.020, steps: int = 141) -> float:
    """Grid search for the valve coefficient that best explains the readings."""
    grid = np.linspace(lo, hi, steps)
    errors = [rmse(k, t_obs, h_obs) for k in grid]
    return float(grid[int(np.argmin(errors))])


if __name__ == "__main__":
    t_obs, h_obs = sensor()
    k_fit = calibrate(t_obs, h_obs)
    print(f"datasheet k = {K_GUESS:.4f}  RMSE = {rmse(K_GUESS, t_obs, h_obs):.3f} m  steady level = {steady_state(K_GUESS):.2f} m")
    print(f"calibrated k = {k_fit:.4f}  RMSE = {rmse(k_fit, t_obs, h_obs):.3f} m  steady level = {steady_state(k_fit):.2f} m")
    print(f"true k       = {K_TRUE:.4f}  (known only because the plant is simulated too)")
