# Fact-check, 2026-W49

Checked on 27 Nov 2026. "Ran" means the file was executed and its output matches the text and its
`.expected` file. "Sourced" means the page was fetched and the quoted words or numbers were found there.
"Done work" means the claim was found in the merged change (diff, tests or pull request text).

## 2026-11-30-sim-p3 (2000 small tanks become a pipe)

Work: `psl-pfr-mixer-splitter` (process-sim-lab PR #6, merge commit 6c8aa2e, merged 2026-11-17; read with
`gh pr view 6` and `gh pr diff 6`). The repo's tests were run at 6c8aa2e from a read-only `git archive`
export: 26 tests, OK.

| Claim | Outcome | Evidence |
| --- | --- | --- |
| Two weeks ago I added an isothermal PFR, first order A to B, X = 1 - exp(-k tau) | Done work | PR #6 "feat: add pfr, mixer and splitter units", merged 2026-11-17; `pfr.py` docstring: "conversion X = 1 - exp(-k * tau)" |
| A PFR is the limit of many equal CSTRs in series; X_N = 1 - (1 + k tau / N)^-N tends to 1 - exp(-k tau) | Done work + Sourced | `pfr.py` docstring: "the limit of N equal CSTRs in series, X_N = 1 - (1 + k * tau / N)^-N, which tends to 1 - exp(-k * tau)"; Rawlings and Ekerdt ch. 8 slides 29-30 ("CSTRs in series ... Equation 8.16 for large n is another approximation for delta(theta - tau)", the PFR residence-time distribution); CSTR form from ch. 4 slide 58 ("xA = k tau / (1 + k tau)") |
| One test chains 2000 calls to the CSTR model and compares with the PFR model; two units written separately | Done work | `tests/test_pfr.py::test_beats_cstr_and_equals_many_cstrs_in_series`: loop `for _ in range(n)` with `n = 2000` over `isothermal_cstr_first_order`; CSTR from PR #2, PFR from PR #6 |
| At k tau = 2 the gap is about (k tau)^2 exp(-k tau) / (2N) | Done work + Ran | test comment: "The gap is about Da^2 * e^-Da / (2N) = 1.4e-4 for N = 2000"; `tanks_in_series.py` last column |
| 0.0027 for 100 tanks, 1.35e-4 for 2000; the run gives about 1.35e-4; 2000 tanks came within about 1.35e-4 | Ran | `tanks_in_series.py`: N = 100 gap 2.70e-03 (estimate 2.71e-03), N = 2000 gap 1.35e-04 (estimate 1.35e-04); the repo's own CSTR chained 2000 times at 6c8aa2e gives 1.3531e-4, so every "within" or "gives" in prose says "about" (1.3531e-4 is just over 1.35e-4); the card, the PDF pages and the Short screen show the script's printed 1.35e-4 as a table value |
| The test allows 2e-4 | Done work | `assertAlmostEqual(series_conversion, pfr.conversion, delta=2e-4)` |
| Against 2e-4 a chain needs at least 1354 tanks to pass; 1e-2 accepts 27 tanks or more, so it cannot tell 2000 tanks from 27 | Ran | `tanks_in_series.py`: "tolerance 2e-04: any chain of 1354 tanks or more passes", "tolerance 1e-02: any chain of 27 tanks or more passes" |
| Card and Facebook: 1 tank X = 0.667, 10 tanks 0.838, 2000 tanks 0.86453, PFR 0.86466; 67 % vs 86.5 %; about 0.0135 percentage points | Ran | `tanks_in_series.py` rows 0.666667, 0.838494, 0.864529, PFR 0.864665; 1.3531e-4 = 0.013531 percentage points |
| Limits: isothermal, first order, constant density; the gap formula is the leading term only | Done work + Common knowledge | `pfr.py` assumptions; N = 1 shows the estimate 0.27 vs the real 0.198, so the formula is asymptotic |
| LinkedIn PDF pages | Checked | every number on the 5 pages is from `tanks_in_series.py` or the test file |

Cut or softened: the hook said "I knew the size of that gap before I ran it"; it now says the test predicted it (the
prediction is in the test comment). The estimate "0.27 for 1 tank" was cut: the leading term is wrong at N = 1. Round 1 of
the judge: "so it would miss a loop that quietly stopped early" was wrong (27 tanks is a wrong N, and the test also
pins the chain to its closed form to 10 places); it now says only that 1e-2 cannot tell 2000 tanks from 27. Round 2: "came within 1.35e-4" rounded 1.3531e-4
down; the prose now says "about 1.35e-4" (and "about 0.0135 percentage points" on Facebook).

## 2026-12-01-physical-ai-p1 (where is the sensor? frame order in tf2)

Work: `pai-tf2-frames` (physic-ai-for-everyone, ledger ref private@481515f, merged 2026-11-16; named, not linked).
The ledger sha no longer resolves: the repo's history was rewritten before it went public on 2026-11-25. The same
change is commit 95922da "feat: lesson 02 coordinate frames and tf2 (#13)", dated 2026-11-16, read with `git show`
in the local clone. No code or text from it is pasted: `frames.py` is a fresh stdlib script.

| Claim | Outcome | Evidence |
| --- | --- | --- |
| Lesson 02 of physic-ai-for-everyone, a ROS 2 course in English and Vietnamese, covers coordinate frames and tf2 | Done work | 95922da adds `lessons/02-tf2/README.md` ("Lesson 02: Coordinate frames and TF2", English and Tiếng Việt sections) and an English and a Vietnamese lesson page |
| Frames map -> odom -> base_link, with a sensor under base_link | Done work | `frames.launch.py` docstring: "Start the frame tree: map -> odom -> base_link -> sensor" |
| REP-105: map is the parent of odom, odom of base_link; each frame has one parent, except the root | Sourced | rep-0105.rst: "The map frame is the parent of odom, and odom is the parent of base_link"; "each frame can only have one parent" |
| odom 2.0 m along x of map; base_link at (1, 0) in odom, turned 90 degrees left; sensor 0.2 m ahead | Done work | `exercises.md` exercise 1 (same values; paraphrased) |
| map_odom @ odom_base @ base_sensor gives (3.0, 0.2); "ahead" is +y in the map | Ran + Done work | `frames.py`: "(3.0, 0.2)"; `solutions.md` exercise 1 gives (3, 0.2) with the same reasoning (paraphrased) |
| Reversed product gives (1.2, 2.0); the two answers are 2.55 m apart; labelled a toy example written for the post | Ran | `frames.py`: "(1.2, 2.0)", "distance between the two answers: 2.55 m" |
| Turned left is a positive yaw | Sourced | rep-0103.rst: "x forward, y left, z up" (right-handed frames) |
| tf2 does the walk with lookup_transform('map', 'sensor', time) | Done work | `sensor_locator.py` calls `lookup_transform('map', 'sensor', Time())` |
| A test composes the three matrices by hand and checks tf2's answer within 1e-6 | Done work | `test_frames.py::test_tf2_agrees_with_composing_the_matrices_by_hand`: `np.allclose(by_hand, _matrix(whole), atol=1e-6)` |
| Card code lines | Ran | copied from `frames.py` lines 36-38 and the right-hand sides of lines 40-41 |

Not used: the lesson's "silent failure" exercise (a stopped broadcaster leaves a stale transform with no warning). It
is a second idea and was left for a later post.

## 2026-12-02-sim-p4 (a valid range is not a promise of accuracy)

Work: `psl-antoine-lmtd` (process-sim-lab PR #8, merge commit 01c6c10, merged 2026-11-17; `gh pr view 8`,
`gh pr diff 8`). The repo's tests at 01c6c10: 56 tests, OK.

| Claim | Outcome | Evidence |
| --- | --- | --- |
| Antoine equation log10(P/bar) = A - B / (T + C) with NIST WebBook constants for benzene, toluene and ethylbenzene | Done work | `antoine.py` docstring and `ANTOINE` dict (3 entries, source "NIST Chemistry WebBook (SRD 69)") |
| Each fit keeps its temperature range; the code raises an error outside it | Done work | docstring: "Outside that range the functions raise ValueError instead of extrapolating"; `test_rejects_out_of_range_and_unknown` |
| A test checks each fit against NIST's normal boiling point within the uncertainty NIST states | Done work | `test_normal_boiling_points_match_nist_within_its_uncertainty`; comment "The test tolerance is that uncertainty" |
| Water is not in the table; no NIST water fit covers 1 atm, so that test cannot run for water | Done work + Sourced | PR #8 text: "Water is left out on purpose: its NIST fit ranges end at 373 K, below the 373.15 K normal boiling point."; NIST rows 379-573, 273-303, 304-333, 334-363, 344-373, 293-343, 255.9-373 K |
| At 1 atm water boils at about 373.12 K (IAPWS-IF97); NIST's water fits end at 373 K or start at 379 K | Ran + Sourced | `water_antoine.py`: "IAPWS-IF97 boiling temperature at 101325 Pa (Eq. 31): 373.124 K" (IF97 backward equation, Eq. (31)); NIST rows as above. NIST's own average, "Tboil 373.17 ± 0.04 K, AVG, Average of 7 values" (page fetched 27 Nov 2026), is quoted only in the script docstring: it is a literature average and its interval does not contain the IF97 value, so the posts and the Short use the IF97 value |
| IAPWS-IF97 is the reference equation for water; its saturation pressure is Eq. (30) | Sourced | IF97 Revised Release, section 8.1 and Table 34; `water_antoine.py` reproduces Table 35 (300 K: 0.353658941e-2 MPa, 500 K: 0.263889776e1, 600 K: 0.123443146e2) |
| Bridgeman and Aldrich (344-373 K): 0.023 to 0.025 K high from 350 to 373 K (LinkedIn); about 0.025 K high (X, Facebook, Telegram, alt text, YouTube); 0.025 K high at 373 K (Short) | Sourced + Ran | constants from the NIST table; `water_antoine.py`: +0.023 K at 350 K, +0.025 K at 360-373 K. Unrounded the offset reaches 0.0253 K near 365 K, so the posts no longer say "within 0.025 K" |
| Stull (255.9-373 K): 0.27 K low at 330 K, 0.39 K high at 370 K, 0.47 K high at 373 K; Facebook: 0.47 degrees off at 373 K | Sourced + Ran | `water_antoine.py`: -0.268, +0.387, +0.473 K. The script samples 300-373 K only, so no channel says "up to 0.47" or names a maximum over the whole range |
| The range check accepts both fits at these temperatures | Ran | every listed T is inside both ranges (Stull 255.9-373, Bridgeman 344-373 for T >= 350) |

Round 1 of the judge found the first draft wrong: it blamed the 0.43 K miss on using the Stull fit 0.6 K past its
range, but the fit is already about 0.4 K off inside its range (IAPWS-IF97). The post was rewritten around that finding,
the script now compares both fits with IAPWS-IF97 inside their ranges, and the calendar topic was changed to match. Round 2 of the judge: the Short said "water boils at 373.17 K" (NIST's literature
average, not the IF97 value at 1 atm); Facebook said "off by up to 0.47 degrees near the boiling point" (not measured
over the whole range); "within 0.025 K" and "0.025 K high from 350 to 373 K" did not match the script. All three were
fixed in every channel, and the script now prints the IF97 boiling temperature at 101325 Pa.

## Article: three-process-models-tested-against-closed-form-answers (2026-12-05)

Work: `psl-cstr-skeleton` (PR #2), `psl-pfr-mixer-splitter` (PR #6), `psl-flash-rachford-rice` (PR #7, merge commit
370a2aa). All three read with `gh pr diff`; tests run at 370a2aa: 5 CSTR, 8 PFR, 12 flash tests pass.

| Claim | Outcome | Evidence |
| --- | --- | --- |
| Mutation table (4/5, 4/8, 7/8, 8/12, 11/12 and the catching tests) | Ran | `content/2026-W49/closed_form_mutations.py` against 370a2aa; output equals `closed_form_mutations.expected` and the article's text block |
| CSTR mutation matches W48's result (4 of 5 reactor tests pass) | Ran | same as `2026-W48/2026-11-23-sim-p1/wrong_formula.expected` |
| Table: X = 5/6 at tau = 500 s, k tau = 5; X = 1/2 at k tau = ln 2; flash z = (0.4, 0.6), K = (3, 0.2) gives psi = 0.2 | Done work | `test_cstr.py`, `test_pfr.py::test_half_life_case`, `test_flash.py::test_unequal_split_matches_closed_form` |
| Binary Rachford-Rice is linear in psi: psi = -(z1 a1 + z2 a2) / (a1 a2); ternary case built backwards from psi = 0.25 | Done work | `test_flash.py` module docstring |
| Equal split z = (0.5, 0.5) passes with z_i dropped because f is scaled by 2; unequal case moves 0.2 -> 0.375 | Ran + algebra | mutated run: psi = 0.49999999999954525 (equal), 0.37499999999954525 (unequal) |
| The mole balance closes for any psi; the sum x = 1 line failed (1.2143) | Done work + Ran | `flash.py`: liquid from psi, `vapour_flows[c] = max(0.0, f - liquid_flows[c])`; mutated run fails at test line 78 `sum(r.x.values())`, value 1.2142857142852985 |
| sum x_i - 1 = -psi f(psi) | Derived | algebra in the article, rechecked by hand |
| Small-Da test at k tau = 1e-12 checks 11 decimal places of X / Da | Done work | `test_small_damkohler_keeps_precision`: `assertAlmostEqual(r.conversion / 1e-12, 1.0, places=11)` |
| Subcooled feed: sum z_i K_i = 0.55 | Done work | `test_subcooled_feed_is_all_liquid` comment: "sum z K = 0.5 * 0.8 + 0.5 * 0.3 < 1" |
| No mutation testing tool has been run on the repo | Author's statement | nothing in the merged changes runs one |
