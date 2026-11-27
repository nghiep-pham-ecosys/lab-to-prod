<!-- Paste into the Hashnode editor (hashnode.com/draft). Not committed to a schedule.
     Title:            Three process models, each tested against a closed-form answer
     Subtitle:         I planted one wrong formula at a time in a CSTR, a PFR and a flash drum. Closed-form tests caught every bug; most property tests did not.
     Tags:             python, testing, simulation, chemistry
     Cover image:      https://nghiep-pham-ecosys.github.io/lab-to-prod/og/posts/three-process-models-tested-against-closed-form-answers.png
     Article settings: "Are you republishing?" -> original URL = https://nghiep-pham-ecosys.github.io/lab-to-prod/posts/three-process-models-tested-against-closed-form-answers/
-->

4 of 5, 4 of 8, 8 of 12. Those are the tests that still passed after I put one wrong formula
into each of three models in my process simulator. Every bug was caught, but almost always by
the same kind of test: one that compares the model with an answer worked out by hand.

This deep dive goes back over the first three units of
[process-sim-lab](https://github.com/nghiep-pham-ecosys/process-sim-lab), a small chemical
process simulation library I am building in public. My Simulation notes covered each unit on
its own. Here I run one experiment across all three: plant a bug, run the unit's own tests,
and see which tests notice.

## Three models, three exact answers

All three units are idealised on purpose: isothermal, steady state, constant density, and for
the flash drum, K-values that do not depend on composition. That is what makes a closed form
possible.

| Unit | Merged in | Closed form | Exact test case |
| --- | --- | --- | --- |
| Stirred tank (CSTR), A to B, first order | [PR #2](https://github.com/nghiep-pham-ecosys/process-sim-lab/pull/2) | X = k tau / (1 + k tau) | tau = 500 s, k tau = 5: X = 5/6 |
| Plug-flow reactor (PFR), same reaction | [PR #6](https://github.com/nghiep-pham-ecosys/process-sim-lab/pull/6) | X = 1 - exp(-k tau) | k tau = ln 2: X = 1/2 |
| Isothermal flash drum | [PR #7](https://github.com/nghiep-pham-ecosys/process-sim-lab/pull/7) | Rachford-Rice root, linear for two components | z = (0.4, 0.6), K = (3, 0.2): psi = 0.2 |

The flash case needs a word. Rachford-Rice, f(psi) = sum z_i (K_i - 1) / (1 + psi (K_i - 1)) = 0,
has no closed form in general. With two components it becomes linear in psi after you clear the
denominators, so psi = -(z1 a1 + z2 a2) / (a1 a2) with a_i = K_i - 1. The test file also builds a
three-component case backwards: pick psi = 0.25, the liquid composition and the K-values, and
compute the feed that must produce them.

Each unit also has property tests: moles are conserved, zero rate gives zero conversion,
conversion rises with volume, bad inputs raise an error. These are true for any reactor or any
drum. That turned out to matter.

## The experiment: one bug at a time

The script
[`closed_form_mutations.py`](https://github.com/nghiep-pham-ecosys/lab-to-prod/blob/main/content/2026-W49/closed_form_mutations.py)
copies a checkout of the repository at the merge commit of PR #7, replaces exactly one line of model code, and
runs that unit's test file. Five bugs, each one I could plausibly write:

```python
MUTATIONS = [  # (label, file, line as merged, line with the bug, test file)
    ("CSTR: plug-flow formula", UNITS + "cstr.py",
     "conversion = damkohler / (1.0 + damkohler)", "conversion = 1.0 - math.exp(-damkohler)", "test_cstr"),
    ("PFR: stirred-tank formula", UNITS + "pfr.py",
     "conversion = -math.expm1(-damkohler)", "conversion = damkohler / (1.0 + damkohler)", "test_pfr"),
    ("PFR: 1 - exp(-Da) instead of expm1", UNITS + "pfr.py",
     "conversion = -math.expm1(-damkohler)", "conversion = 1.0 - math.exp(-damkohler)", "test_pfr"),
    ("Flash: z_i left out of Rachford-Rice", UNITS + "flash.py",
     "return sum(zi * (k_values[c] - 1.0)", "return sum(1.0 * (k_values[c] - 1.0)", "test_flash"),
    ("Flash: no bubble-point check", UNITS + "flash.py",
     "if sum(z[c] * k[c] for c in z) - 1.0 <= 0.0:", "if False:", "test_flash"),
]
```

The output, with Python 3.12:

```text
no bug                                 test_cstr   5/5 pass; caught by: nothing
no bug                                 test_pfr    8/8 pass; caught by: nothing
no bug                                 test_flash 12/12 pass; caught by: nothing
CSTR: plug-flow formula                test_cstr   4/5 pass; caught by: test_matches_analytic_conversion
PFR: stirred-tank formula              test_pfr    4/8 pass; caught by: test_beats_cstr_and_equals_many_cstrs_in_series, test_half_life_case, test_matches_analytic_conversion, test_ninety_percent_conversion
PFR: 1 - exp(-Da) instead of expm1     test_pfr    7/8 pass; caught by: test_small_damkohler_keeps_precision
Flash: z_i left out of Rachford-Rice   test_flash  8/12 pass; caught by: test_binary_sweep_matches_closed_form, test_conserves_moles_and_keeps_state, test_constructed_case, test_unequal_split_matches_closed_form
Flash: no bubble-point check           test_flash 11/12 pass; caught by: test_subcooled_feed_is_all_liquid
```

## Swapping the two reactor formulas: only exact values noticed

The two reactor bugs are mirror images. The CSTR got the PFR formula, and the PFR got the CSTR
formula. In both cases every property test passed. A plug-flow formula in a stirred tank still
conserves moles, still gives zero conversion at zero rate, and still converts more in a bigger
tank. So does the reverse.

The tests that failed all pin a number: X = 5/6, X = 1/2, X = 0.9 at k tau = ln 10, and the
limit of 2000 tanks in series. That last one is a different kind of exact answer: the CSTR model
checks the PFR model, because N equal tanks in series give X = 1 - (1 + k tau / N)^-N, which
tends to the PFR formula as N grows.

A property describes a family of models. A closed form describes one member of it. If the bug
swaps one member for another, only the closed form can tell.

## A symmetric test case hid a bug

The flash bug I find most useful is the one where a closed-form test passed. I dropped z_i, the
feed mole fraction, from Rachford-Rice. The equal-split case, z = (0.5, 0.5) and K = (2, 0.5),
still passed.

The reason is algebra, not luck. With equal z, every term of f(psi) carries the same factor 0.5.
Dropping it multiplies f by 2, and a function and twice that function have the same root. The
bisection lands on psi = 0.5 either way. The unequal case, z = (0.4, 0.6), moved from the exact
0.2 to 0.375, and that test failed.

So a closed form is only as strong as the case you feed it. A test case with symmetric inputs can
make a missing term cancel. When I pick an exact case now, I make the inputs unequal on purpose.

## The property that did catch it is a consequence of the equation

Four flash tests caught the missing z_i. One of them is a property test,
`test_conserves_moles_and_keeps_state`, and I wanted to know why this property test worked when
the reactor ones did not.

It was not the mole balance. In this model the liquid flow of each component is computed from
psi, and the vapour flow is the feed minus the liquid. That balance closes for any psi, right or
wrong. A check that is true by construction tests nothing.

What failed was the next line: the liquid mole fractions must sum to 1. With the bug, they summed
to 1.2143. Here is why that line is strong. With x_i = z_i / (1 + psi a_i) and sum z_i = 1:

```text
sum x_i - 1 = sum z_i (1 - (1 + psi a_i)) / (1 + psi a_i)
            = -psi * sum z_i a_i / (1 + psi a_i)
            = -psi * f(psi)
```

So for psi > 0, the fractions sum to 1 exactly when f(psi) = 0. This property is the
Rachford-Rice equation in another form. It is not a generic sanity check, which is why it caught
a wrong equation.

## Two bugs that one test each caught

The last two bugs were each caught by a single test, and both are edge cases.

`1 - exp(-Da)` gives the same PFR conversion as `-expm1(-Da)` for any normal input. It only breaks
at tiny k tau, where 1 - exp(-Da) loses digits to cancellation. One test, at k tau = 1e-12,
checks 11 decimal places of the ratio X / Da. Without it, the swap is invisible.

Removing the bubble-point check sends an all-liquid feed into the bisection. Only the subcooled
feed test, where sum z_i K_i = 0.55 is below 1, checks for that case.

If either of those tests did not exist, the bug would pass every remaining test. Edge cases are
where a single test is the whole guard.

## What this experiment does not show

Five bugs is a small sample, and I picked them. A mutation testing tool would generate hundreds
of changes, including ones I would not think of. I have not run one on this repository yet.

The closed forms also only exist because the models are idealised. A non-isothermal reactor, or
K-values that depend on composition, have no exact answer to test against. For those I will need
other oracles: limits between models, like the tanks in series, and equations that must hold at
the solution, like the sum of mole fractions.

Next, I want to run a mutation testing tool over the three units and see whether the survivors
look like the bugs above, or like something new.

---

*Originally published on [Lab to Prod](https://nghiep-pham-ecosys.github.io/lab-to-prod/posts/three-process-models-tested-against-closed-form-answers/).*
