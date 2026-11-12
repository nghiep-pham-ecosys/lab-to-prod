# Sim

Small simulations for the Simulation and Physical AI series. Everything here is a toy example
unless a file says otherwise; no plant data, no proprietary models.

| File | What |
| --- | --- |
| `tank.py` | a draining tank (Torricelli outflow, RK4) and a one-parameter calibration against simulated sensor data |
| `01-tank-digital-twin.ipynb` | the same, as a notebook with plots: model, sensor, calibrate, compare |

```bash
uv run --with numpy python sim/tank.py
```

```bash
uv run --with numpy --with matplotlib --with jupyterlab jupyter lab sim/
```
