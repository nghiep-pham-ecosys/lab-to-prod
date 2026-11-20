"""Swap the CSTR formula in process-sim-lab for a wrong one and count which tests still pass.

The repo's isothermal CSTR (first order, A -> B) returns X = k tau / (1 + k tau). This script
replaces it with X = 1 - exp(-k tau), the formula of a plug-flow reactor, which is wrong for a
CSTR, and runs the repo's own 8 tests against both versions. 5 of the 8 (tests/test_cstr.py) call the
reactor; the other 3 (tests/test_streams.py) test the Stream type only, so the reactor count
is printed too.

Run (Python 3.12, stdlib only), with a checkout of process-sim-lab at the merge commit of PR #2:

    git clone https://github.com/nghiep-pham-ecosys/process-sim-lab
    git -C process-sim-lab checkout 79401877e71f0e4e6cdc51190047e19eef3119e2
    python wrong_formula.py process-sim-lab
"""
import io
import math
import sys
import unittest
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(repo / "src"), str(repo / "tests")]

import process_sim_lab.units as units  # noqa: E402
from process_sim_lab import Stream  # noqa: E402
from process_sim_lab.units import CSTRResult  # noqa: E402

right = units.isothermal_cstr_first_order


def wrong(feed, *, reactant, product, rate_constant, volume, volumetric_flow):
    r = right(feed, reactant=reactant, product=product, rate_constant=rate_constant,
              volume=volume, volumetric_flow=volumetric_flow)   # keeps the input checks
    x = 1.0 - math.exp(-r.damkohler)                             # PFR formula: wrong here
    flows = dict(feed.flows)
    flows[reactant] = feed.flows[reactant] * (1.0 - x)
    flows[product] = flows.get(product, 0.0) + feed.flows[reactant] * x
    outlet = Stream(flows=flows, temperature=feed.temperature, pressure=feed.pressure)
    return CSTRResult(outlet=outlet, conversion=x, space_time=r.space_time, damkohler=r.damkohler)


def run_tests(model):
    units.isothermal_cstr_first_order = model
    for name in ("test_cstr", "test_streams"):
        sys.modules.pop(name, None)   # re-import so the tests pick up the model
    suite = unittest.defaultTestLoader.discover(str(repo / "tests"))
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    failed = sorted(t.id().rsplit(".", 1)[1] for t, _ in result.failures + result.errors)
    reactor_total = unittest.defaultTestLoader.loadTestsFromModule(sys.modules["test_cstr"]).countTestCases()
    reactor_failed = sum(t.id().startswith("test_cstr.") for t, _ in result.failures + result.errors)
    return (result.testsRun - len(failed), result.testsRun, failed,
            reactor_total - reactor_failed, reactor_total)


feed = Stream(flows={"A": 10.0, "W": 50.0})
for label, model in (("right", right), ("wrong", wrong)):
    x = model(feed, reactant="A", product="B", rate_constant=0.01, volume=2.0,
              volumetric_flow=0.004).conversion
    passed, total, failed, r_passed, r_total = run_tests(model)
    print(f"{label}: X = {x:.4f}, tests passed {passed}/{total} (reactor tests {r_passed}/{r_total}), "
          f"failed: {failed or 'none'}")
