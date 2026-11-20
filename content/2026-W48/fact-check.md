# Fact-check, 2026-W48

Checked from 20 Nov 2026. "Ran" means the file was executed and its output matches the text.
"Sourced" means the page was opened and the quoted words were found there.

## 2026-11-24-cloud-p3 (merge guard for a private repo on GitHub Free)

Work: `cfe-ci-guard` (claude-for-everyone-vi, private@fb18777, merged 2026-11-17; PR #15, issue #14, read with gh, not linked). Checked on 20 Nov 2026.

| Claim | Outcome | Evidence |
| --- | --- | --- |
| 6 checks reported on the PR that added the guard; 2 skipped; the summary check went green | Done work | `gh pr view 15` status rollup: test SUCCESS, pr-title SUCCESS, gitleaks SUCCESS, live-smoke SKIPPED, model-sync SKIPPED, ci-result SUCCESS |
| The 2 skips were correct | Done work | the CI workflow at fb18777: live-smoke runs only on a manual dispatch; model-sync is disabled by a constant false condition (paraphrased) |
| The repo is private, on GitHub Free | Done work | `gh repo view` visibility PRIVATE; `gh api orgs/<org>` plan.name `free`; issue #14 says the same (paraphrased) |
| On Free, branch protection and rulesets only cover public repos | Sourced | docs.github.com .../about-protected-branches: "Protected branches are available in public repositories with GitHub Free and GitHub Free for organizations"; .../about-rulesets: "Rulesets are available in public repositories with GitHub Free and GitHub Free for organizations, and in public and private repositories with GitHub Pro, GitHub Team, and GitHub Enterprise Cloud." |
| Pre-push hook runs gitleaks on the pushed commits; blocks on a finding or when gitleaks is missing | Done work | the repo's pre-push hook at fb18777: scans the pushed commits with gitleaks, blocks on a finding, and blocks when gitleaks is missing (paraphrased) |
| pr-title exists because the title becomes the squash commit subject | Done work | the pr-title workflow's header comment says the title becomes the squash commit subject (paraphrased) |
| ci-result waits for every other job in the CI workflow | Done work | the CI workflow: ci-result always runs and needs the four other CI jobs (pr-title is a separate workflow) |
| The merge script requires just two checks, ci-result and pr-title | Done work | ecosys `tools/ship/_shiplib.py`: `DEFAULT_REQUIRED = ("ci-result", "pr-title")`; issue #14 says the same (paraphrased) |
| Merged rule: test and gitleaks must succeed, every other job success or skipped, cancelled is red | Done work | the ci-result step of the CI workflow encodes this rule over the job results (paraphrased, not quoted) |
| Toy example: naive rule lets 2 of 3 broken runs through, ci-result 0 of 3 | Ran | `ci_result.py`, output equals `ci_result.expected`; its rule mirrors the merged rule above |
| Labelled as a toy example | Checked | LinkedIn, X, Telegram text, card lesson and image_alt say "toy example" (Facebook has no toy numbers) |
| With branch protection, GitHub accepts a skipped required check | Sourced | .../about-protected-branches: "Required status checks must have a `successful`, `skipped`, or `neutral` status before collaborators can make changes to a protected branch." |

Fixed: "6 checks ran" (2 of them did not run) is now "6 checks reported"; "the guard still went green" is now "the summary check"; "ci-result waits for every other job" and the Facebook and Telegram equivalents now say "in the CI workflow" (pr-title is outside it); "my merge script reads only" is now "requires just two checks"; "GitHub counts a skipped required check as passing" is now "accepts", the source's wording; a phrase copied from a private step name is now "skipped by design". X trimmed to fit ("The rule:" to "Rule:").
Not used: the PR text says the hook runs "gitleaks and the branch rules", but the diff runs gitleaks only, so the post claims gitleaks only. The repo the PR text names as a model is not in the ledger and is not named.

## 2026-11-25-sim-p2 (flash drum: check both ends, then bisect)

Work: `psl-flash-rachford-rice` (process-sim-lab PR #7, merge commit 370a2aa, merged 2026-11-17; read with `gh pr view 7` and `gh pr diff 7`). Checked on 20 Nov 2026. Measured numbers come from running `isothermal_flash` at 370a2aa (a read-only `git archive` export; its 12 flash tests pass).

| Claim | Outcome | Evidence |
| --- | --- | --- |
| Last week I added an isothermal flash drum to process-sim-lab | Done work | PR #7 "feat: add isothermal flash drum solved with rachford-rice", merged 2026-11-17 (post dated 2026-11-25) |
| K-values given, not dependent on composition: the ideal-mixture case | Done work | `src/process_sim_lab/units/flash.py` docstring: "the K-values are given at the drum temperature and pressure and do not depend on composition (ideal mixtures, as in the spec)" |
| f(psi) = sum z_i (K_i - 1) / (1 + psi (K_i - 1)), psi = V/F | Done work + Common knowledge | flash.py docstring: "Rachford-Rice f(psi) = sum_i z_i * (K_i - 1) / (1 + psi * (K_i - 1)) = 0", "vapour fraction psi = V / F"; source paper cited in the PR (Rachford and Rice, JPT 4(10), 1952; title, authors, volume and issue confirmed in the Crossref record of DOI 10.2118/952327-G) |
| f(0) = sum z_i K_i - 1 <= 0: at or below bubble point, all liquid; f(1) = 1 - sum z_i / K_i >= 0: at or above dew point, all vapour | Done work | flash.py docstring: "f(0) = sum_i z_i K_i - 1 <= 0 feed at or below its bubble point: all liquid, psi = 0"; "f(1) = 1 - sum_i z_i / K_i >= 0 feed at or above its dew point: all vapour, psi = 1"; algebra rechecked |
| With every K > 0, f falls on [0, 1] with no pole there, so exactly one root and bisection cannot miss it | Done work | flash.py docstring: "f(psi) falls strictly on [0, 1] (f' = -sum_i z_i (K_i - 1)^2 / ... < 0), and with K_i > 0 its poles psi = 1 / (1 - K_i) all lie outside [0, 1]"; PR text: "always brackets the physical root when every K > 0" |
| Halving [0, 1] to narrower than 1e-12 takes 40 steps | Ran | `rachford_rice.py`: "after 39 steps: 1.82e-12 after 40 steps: 9.09e-13 (tol = 1e-12)"; `isothermal_flash(tol=1e-12)` at 370a2aa returns `iterations` = 40 on all 8 two-phase cases tried |
| 40 steps, matched the exact answer to within 5e-13 (hook, all channels) | Ran + Done work | `isothermal_flash` at 370a2aa: errors 4.55e-13, 2.73e-13, 4.55e-13 on the PR's binary 0.5, binary 0.2 and ternary 0.25 cases; 3.0e-14 to 4.55e-13 on the 5-point sweep test; PR text: "the error is 2.7e-13". The bound also follows from the method: half of 9.09e-13 |
| Code sample output | Ran | `python3 rachford_rice.py` output equals `rachford_rice.expected` (diff empty) |
| Toy all-liquid binary (z 0.5/0.5, K 0.8/0.3): the only root is psi = 3.21, above 1 | Ran | `rachford_rice.py`: "psi = 3.2143 f(psi) = -5.6e-17"; hand check 0.45 / 0.14 = 3.214; binary RR is linear after clearing denominators (tests/test_flash.py header), poles at 1.43 and 5, so one root. Same feed as `test_subcooled_feed_is_all_liquid`; PR code returns "liquid", 0 steps |
| Labelled as a toy example | Checked | LinkedIn "my toy all-liquid binary", Telegram "a toy all-liquid feed"; X, Facebook and the card do not use the toy numbers |
| Source link answers 200 | Failed | `http_status("https://doi.org/10.2118/952327-G")` = 403 (redirects to OnePetro, which answers 403 to the checker); the Crossref API record answers 200. `--check-links` will fail on this post. Author decision |

Fixed: "The K-values are given and fixed, so this is the ideal-mixture case" now says they "do not change with composition" (fixed K alone is not what makes a mixture ideal; the code's own wording is composition-independent); "Skip the checks and the equation still has a root to find" now says "a root, an unphysical one" (with the PR's bisection on [0, 1] a skipped check would not return 3.21); "The ends tell you whether a root exists" (LinkedIn) and "if a root exists" (card lesson) now say "lies in range" / "is in range", since the toy case shows a root can exist outside [0, 1]; Telegram now states the "every K > 0" condition. LinkedIn trimmed from 286 to under 280 words; format_check has no warning for this post.
Not used: the sources cannot be opened (paywalled), so no sentence from the paper is quoted; the equation form is checked against the merged code and textbook algebra only. Open: the post still needs image.png (render-image), and the 403 source link needs an author decision (manual merge, a different open primary source, or an allowlist).

## 2026-11-26-ai-eng-p3 (a format check next to the LLM judge)

Work: `l2p-format-checks` (lab-to-prod, https://github.com/nghiep-pham-ecosys/lab-to-prod/pull/27, merge commit 20ea834, merged 2026-11-15T23:53Z = 16 Nov 06:53 +07; ledger date 2026-11-16, not after the post date). Read with `gh pr view 27` and `git show 20ea834`. Checked on 20 Nov 2026.

| Claim | Outcome | Evidence |
| --- | --- | --- |
| 5 of 5 approved W47 posts ended without an open question | Ran / Done work | `format_vs_judge.py` (output equals `format_vs_judge.expected`): "format check: 5 of 5 LinkedIn posts with no open question at the end"; PR #27 text: "all 5 LinkedIn posts warn \"no open question at the end\""; all 5 have `status: approved` at 20ea834 |
| The LLM judge had passed all 5 | Ran | same run: "judge: 5 of 5 passed (mean >= 4 and no score below 3)", the `pass_rule` of W47 `judge.json` (judged 2026-11-12) |
| Judge means that week were 4.4 to 5.0 | Ran | same run: means 4.4, 5.0, 4.8, 4.4, 4.6 |
| The judge scores five things, including accuracy, sources and voice | Ran | same run: "rubric: technical_accuracy, sources, one_clear_idea, voice, no_banned_info" |
| The ending was not in its rubric; its notes never mention a question | Ran | same run: "notes mention a question=False" for all 5; no rubric key covers the ending |
| My writing rule said "No question at the end to bait comments." | Ran | same run prints `.claude/skills/write-post/SKILL.md` at 20ea834: "No question at the end to bait comments." (replaced later by PR #31) |
| The check runs next to the judge and calls no model | Done work | `tools/format_check.py` docstring: "Never calls a model."; `tools/judge_file.py` writes it into `judge.json` under `format`; PR text "no model" |
| Norms: LinkedIn 150-300 words, 1-2 line hook, paragraphs at most 3 lines and 60 words, X at most 280 characters with a number in the hook, Short 30-60 s | Done work | `tools/format_check.py` lines 21-26 (`LINKEDIN_WORDS = (150, 300)`, `LINKEDIN_HOOK_LINES = 2`, `PARAGRAPH_MAX_LINES = 3`, `PARAGRAPH_MAX_WORDS = 60`, `X_CHARS = v.X_LIMIT`, `SHORT_SECONDS`) and `check_x` (`re.search(r"\d", hook)`); PR text lists the same |
| The question rule is one line: `question = any("?" in p for p in paras[-2:])` | Done work / Ran | `tools/format_check.py` line 46, identical at 20ea834 and on main; the script asserts its copy gives the same answer as `check_linkedin` |
| Toy example: "Agree?" passes the rule | Ran | same run: "toy ending 'Agree?' -> open question = True"; labelled "toy example" in LinkedIn, X and Telegram |
| The judge's notes flagged a Short not re-rendered after a fix | Sourced | W47 `judge.json` at 20ea834, 2026-11-16-dsa-p2: "the Short had not been re-rendered after the round-1 fix" |
| ... a bias of -2.0 called "a small number" | Sourced | same file, 2026-11-17-ml-p1: "Facebook calls the bias 'a small number' while the example bias is -2.0" |
| ... a claim that holds only from 10 Gbps up | Sourced | same file, 2026-11-19-cloud-p2: "Facebook says Direct Connect is 'much bigger', true only from 10 Gbps up" |
| The format check is informational: the approval gate does not read it | Done work | PR text: "The silent-approval gate does not read it (informational)."; on main `tools/automerge_gate.py` has no reference to `format` (only `tools/judge_file.py` line 38 writes it) |
| Rules cost nothing and give the same answer every run | Common knowledge | deterministic code with no model call |

Softened: "5 of 5 posts in my first week ended without an open question" is now "5 of 5 approved posts for my first week" in every channel: PR #31 added a question to the four posts of 17-20 Nov before they went out, so the published versions differ.
Added: the W47 writing rule ("No question at the end to bait comments.") in LinkedIn, Facebook and Telegram. Without it the hook reads as a miss by the judge; the posts followed the rule of the time.
Cut: "The judge catches what no rule can" and "no rule could see" (a stale Short can be caught in code, by a render hash); now "what my rules skip". Cut "Each covers the other's blind spot" (overclaim, and needed for the 280-word target).
Fixed: "at most 3 lines or 60 words" is "3 lines and 60 words" (the code warns when either is exceeded). The script now applies the full pass rule (mean >= 4 and no score below 3), not only the mean, and prints the rubric and the old writing rule; `format_vs_judge.expected` was regenerated from a real run.

## 2026-11-27-ai-eng-p4 (BM25 locally: put the title back in the chunk)

Work: `cfe-rag-bm25` (claude-for-everyone-vi, private@e40a896, merged 2026-11-16; PR #10, read in the local clone, not linked). Checked on 20 Nov 2026. Measured numbers come from running the module's scripts at e40a896 (a read-only `git archive` export in scratch, the clone's own venv, then deleted). Evidence below gives paths and numbers only; no text of the private repo is pasted here or in the post.

| Claim | Outcome | Evidence |
| --- | --- | --- |
| BM25 ranked the right chunk 14th of 28 with chunk text only (hook, all channels, card) | Ran | the module's context script at e40a896: without title/section the right chunk is at rank 14 (paraphrased) |
| With the document title and section copied into each chunk, rank 4 (all channels, card) | Ran | same run: "with title/section ... rank 4" (translated) |
| 28 chunks | Ran | the module's BM25 script: first line prints 28 chunks; recount in the same export: 28 chunks from 7 files |
| Corpus: a made-up lab handbook, 7 pages | Done work | the module README: 7 handbook pages, stated as fictional, every code and number made up; the handbook folder holds 7 files |
| Retrieval is BM25 in the Python standard library | Done work | the module's BM25 solution imports only `math`, `re`, `unicodedata`, `collections` |
| Runs locally: no API key, no embedding model, no vector database | Ran | the context script run again with `ANTHROPIC_API_KEY` and `CLAUDE_MOCK` unset: same rank 14 / rank 4 output, no network call in the BM25 path |
| The right chunk never names the step (calibration) or the meter; those words are in the page title | Ran + Done work | chunk text at e40a896 checked in Python: the Vietnamese words for "calibration", "meter" and "pH" are absent; they are in the page's `# ` title; the chunk sits under the section titled "frequency" |
| The question said "how long", the heading said "frequency"; BM25 matches words, not meaning | Done work | the query string in the context script and the section heading of the handbook page (approximate English, not quoted); the script's own closing note says BM25 does not know the two phrasings mean the same |
| Rank 4 misses a top-3 cut | Done work | the module's search helper defaults to k = 3, so the default search returns 3 chunks |
| A top 5 would include it | Ran | rank 4 <= 5 |
| `f"Document: {title}. Section: {section}.\n{chunk}"` | Ran | the line is `with_context()` in the post folder's own toy script `bm25_title.py` (public, English); the private module does the same in its own words, not quoted |
| `bm25_title.py` output | Ran | `python3 -I bm25_title.py` output equals `bm25_title.expected` (diff empty). The post does not quote its numbers (9 chunks, score 0, then rank 4 of 9) |
| Module 04 tests pass | Ran | `pytest modules/04-rag/tests` at e40a896: 11 passed (background only; the post does not claim it) |
| Labelled as a toy example | Checked | after the fix: LinkedIn, X, Facebook, Telegram, a card row and image_alt say "toy example" or "toy corpus" |

Fixed: the corpus is made up, so every channel now says "toy example" (CLAUDE.md voice rule and this skill); the table card has a third row "Corpus / Toy example: 7 made-up pages" and image_alt says so. "A top 5, or embeddings later, would cover that" is now "A top 5 would include it. Embeddings might close the gap too; I have not measured that yet" (embeddings were never run on this query; the README's claim about embeddings is not a measurement). Telegram "Python standard library only" is now "BM25 in the Python standard library" (the module's scripts import the course client package, so only the BM25 part is stdlib-only). Facebook trimmed back to 119 words after the toy label (validate warned at 122). format_check: OK for this post; validate: only "image.png is missing" (render step not done).
Not used: the module's Claude-written context (contextual retrieval) and the README's 2024 retrieval-failure numbers from an outside blog post; neither was measured here. Open for the author: the post does not name the repo (the skill says a private repo is named, never linked; cloud-p3 does not name it either), and the measured numbers come from the private repo while the public script next to the post is a different toy with different numbers. The card now has 3 rows: check the render.

Update 20 Nov 2026 (author's choice: reword, keep the numbers): the rank 14 / rank 4 of 28 numbers come from the private module, whose corpus is Vietnamese, while the public `bm25_title.py` is a different English toy (9 chunks; score 0 with chunk text only, rank 4 of 9 with title and section). `post.md` now says so. LinkedIn: a new paragraph after the 14 -> 4 line (measured on the course module, in Vietnamese; the quoted question and heading are translated; the public script is a smaller English toy with the same effect). Telegram: "in Vietnamese" after "7 made-up pages", the same script sentence, and "(translated here)" after "how long" and "frequency". Facebook: "a made-up Vietnamese lab handbook" and "A smaller English toy script shows the same effect." X: "Toy corpus (in Vietnamese)". To stay within the targets, LinkedIn dropped the paragraph "When a RAG answer is wrong, check first ..." (the lesson line already says to measure the rank of the right chunk), "small made-up corpus" became "toy corpus", two sentences were merged, and the closing question was shortened; Facebook was tightened in four places. Card and image_alt unchanged (still accurate: a made-up 7-page handbook, 14 of 28, then 4). x.md and x-schedule.md re-exported with `python -m publish.run export --week 2026-W48`. validate word counts: LinkedIn 280, Facebook 120; X 273 characters; format_check OK for this post; validate 0 errors. Re-judge this post only.

## 2026-11-23-sim-p1 (a CSTR checked against algebra)

Work: `psl-cstr-skeleton` (process-sim-lab, https://github.com/nghiep-pham-ecosys/process-sim-lab/pull/2, merge commit 7940187, merged 2026-11-13T03:18Z, before the post date; repo public). Read with `gh pr view 2` and `gh pr diff 2`. Checked on 20 Nov 2026. The repo's 8 tests pass at 7940187 (read-only `git archive` export of the local clone); `wrong_formula.py` was also run on a fresh `git clone` at 7940187, exactly as its docstring says.

| Claim | Outcome | Evidence |
| --- | --- | --- |
| Week 1 of process-sim-lab, built in public | Done work | PR #2 title "feat: week 1 skeleton with spec, stream and isothermal cstr"; `gh repo view` visibility PUBLIC; repo listed under `repos.public` in `content/work.yaml` |
| Isothermal CSTR, one first-order reaction A to B | Done work | `src/process_sim_lab/units/cstr.py` docstring: "Isothermal CSTR with one first-order, irreversible, liquid-phase reaction A -> B" |
| Steady-state mole balance on A gives X = k tau / (1 + k tau), tau = V / Q | Done work + Sourced | cstr.py docstring: "space time tau = V / Q", "conversion X = k * tau / (1 + k * tau)"; Rawlings & Ekerdt ch. 4 slides (sources[0]), slide 58: "xA = kτ / (1 + kτ)" (constant density, Q = Qf, slide 57); slide 53: "cAs = cAf / (1 + kτ)" |
| Limits: isothermal, first order, constant density | Done work | cstr.py docstring: "constant density, steady state, perfect mixing", "isothermal, one reaction" |
| 8 tests: 3 for the stream type, 5 for the reactor | Done work | `tests/test_streams.py` 3 test methods (Stream only, no reactor import), `tests/test_cstr.py` 5; `python -m unittest` at 7940187: "Ran 8 tests ... OK"; PR text: "8 unittest cases" |
| Four reactor tests check properties: moles conserved, zero rate gives zero conversion, conversion rises with volume and stays below 1, bad inputs rejected | Done work | test_cstr.py: `test_conserves_moles_and_keeps_state`, `test_zero_rate_means_no_conversion`, `test_conversion_rises_with_volume` (`assertLess(large.conversion, 1.0)`), `test_rejects_bad_inputs` |
| k = 0.01 1/s, V = 2 m3, Q = 0.004 m3/s give tau = 500 s and X = 5/6, to 12 decimal places | Done work | test_cstr.py `test_matches_analytic_conversion`: "# k = 0.01 1/s, V = 2 m3, Q = 0.004 m3/s -> tau = 500 s, Da = 5, X = 5/6", `assertAlmostEqual(r.conversion, 5.0 / 6.0, places=12)` |
| Swap in X = 1 - exp(-k tau): 4 of 5 reactor tests still pass, only the closed-form test fails (hook, all channels, card) | Ran | `wrong_formula.py` (output equals `wrong_formula.expected`, same on two runs and on a fresh clone): "wrong: X = 0.9933, tests passed 7/8 (reactor tests 4/5), failed: ['test_matches_analytic_conversion']" |
| Conversion went from 0.8333 to 0.9933 | Ran | same run: "right: X = 0.8333", "wrong: X = 0.9933"; hand check 5/6 = 0.83333, 1 - e^-5 = 0.99326 |
| Moles still conserved, conversion still rose with volume | Ran | same run: only `test_matches_analytic_conversion` failed, so `test_conserves_moles_and_keeps_state` and `test_conversion_rises_with_volume` passed with the wrong formula |
| X = 1 - exp(-k tau) is the plug-flow formula | Sourced + Common knowledge | same slides, slide 97: for constant Q the PFR balance "dcj/dτ = Rj ... is identical to the constant-volume batch reactor"; slide 11, eq. 4.9: "cA = cA0 e−kt"; so X = 1 - e^(-kτ). Also the ledger entry `psl-pfr-mixer-splitter` |
| A closed form exists only for simple cases; it proves the code matches the derivation, not the derivation | Common knowledge | author's judgement, phrased as a limit; not a measured claim |
| Second source answers 200 | Sourced | sites.engineering.ucsb.edu/~jbraw/chemreacfun/ is the book page ("Chemical Reactor Analysis and Design Fundamentals, 2nd Edition, James B. Rawlings ... John G. Ekerdt"); `validate --check-links` reports no link error for this post |

Fixed: the hook "7 of my 8 tests still passed" counted the 3 Stream tests, which never call the reactor, so they pass with any formula. Every channel, the card (value "4/5", label "reactor tests passed with the wrong formula") and image_alt now say "4 of 5 reactor tests"; LinkedIn now says "8 tests: 3 for the stream type, 5 for the reactor"; Facebook "Most of its tests" is now "Four of its tests"; the YouTube title and description use 4 of 5. `wrong_formula.py` now also prints the reactor-test count and `wrong_formula.expected` was regenerated from a real run. LinkedIn trimmed back to 280 words or fewer (validate warned at 281). format_check: OK for this post; validate: only image.png, short.mp4 and short.srt missing (render step not done).
Open for the author: the swap experiment is a run in the post folder against the merged code, not part of PR #2 (recorded as Ran; the post's main idea, the closed-form test, is in the PR). Confirm that framing, and that the hook may change from 7/8 to 4/5. The Short script (render-short) must use 4 of 5, not 7 of 8. The script needs a clone of the public repo, so CI does not run it.

## Article: Build log #2 (2026-11-28, `build-log-2-when-github-cron-runs-8-hours-late`)

Work: `l2p-backup-cron` (https://github.com/nghiep-pham-ecosys/lab-to-prod/pull/29, merge e9e6cc2, merged 2026-11-16T02:31Z), `l2p-open-question` (.../pull/31, merge 1316837, 2026-11-16T04:37Z), `l2p-wait-for-slot` (.../pull/33, merge 3d9cafd, 2026-11-17T10:33Z). All before 2026-11-28. Read with `gh pr view`/`gh pr diff`, issues #28 and #32, and `gh run list`/`gh run view`. "Record" = `published.json` and `metrics/metrics.csv` on `publish-state` (cf886e9; its metrics rows equal e071199, the writer's ref), run through `python -m metrics.report --week 2026-W47`. Checked on 20 Nov 2026; this section replaces the writer's notes in `fact-check-build-log-p2.md`.

| Claim | Outcome | Evidence |
| --- | --- | --- |
| Hook: 17 Nov LinkedIn post 7 h 54 min late, 16:09 instead of 08:15 | Record + Done work | `2026-11-17/linkedin` at 09:09:45Z (16:09:45 +07); run 44052974883 created 09:09:33Z; PR #33: "On 17 Nov the LinkedIn post went out at 16:09 instead of 08:15" |
| 16 Nov: no scheduled run by 09:20; started by hand; post at 09:28 | Done work + Record | issue #28: "no scheduled run at all by 09:20"; workflow_dispatch run 43792387362 at 02:28:35Z; `2026-11-16/linkedin` at 02:28:58Z. (PR #29 says "dispatch at 09:29"; the record says 09:28) |
| Docs: "If the load is sufficiently high enough, some queued jobs may be dropped." | Sourced | docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows (fetched, HTTP 200), schedule note, exact words |
| PR #29 added a second cron 45 min later for publish and blog | Done work | PR #29 diff: `15 1` + `0 2 * * 1-6` (publish), `20 1` + `5 2 * * *` (blog) |
| A second run is safe: publisher skips posts already in `published.json` | Done work + Ran | `publish/run.py` line 64-65 `state.done(...)` -> "already published, skipped"; log of fallback run 44267457578 (18 Nov): "linkedin 2026-11-18: already published, skipped" |
| A scheduled publish run started on 16 Nov at 14:55; most likely the 08:15 run, 6 h 40 min late | Record + Derived | `gh run list --workflow publish.yml`: the only `schedule` run that day is 43827258403, created 07:55:42Z; PR #29 (the 09:00 backup cron) merged 02:31Z, after that slot; 07:55 - 01:15 = 6 h 40 min; issue #32 counts it in the 01:15 row. The run does not name its cron, so the text says "most likely" |
| 17 Nov: both crons about 8 h late | Record | runs 44052974883 (09:09Z, 7.9 h after 01:15) and 44060551032 (09:59Z, 8.0 h after 02:00) |
| Delay table (4 rows) | Done work + Record | copied from issue #32; recomputed from `gh run list --event schedule`: publish 07:52/07:34/07:55/09:09 (13,14,16,17 Nov), blog 07:59/07:37/07:53/08:00/09:14 (13-17), metrics 21:37/21:02/19:31/19:59/23:33 (12-16); ranges 6.3-7.9 h, 6.3-7.9 h, 4.5-8.5 h match |
| Docs: "the `schedule` event can be delayed during periods of high loads" | Sourced | same docs page: "The schedule event can be delayed during periods of high loads of GitHub Actions workflow runs" |
| Old operations doc said "several minutes late" | Done work | PR #29 diff, removed line "GitHub's scheduler can run several minutes late." |
| Early crons 00:30 and 03:30 local for publish and blog; YAML excerpt | Done work | `.github/workflows/publish.yml` lines 15-17 at 3d9cafd (unchanged on main), verbatim; `blog.yml` lines 15-17 `30 17 * * *`, `30 20 * * *` |
| 08:15 and 09:00 crons stay as fallbacks | Done work | publish.yml lines 18-20; PR #33 "The fallback crons stay" |
| `0-5` because 17:30 UTC Sunday is 00:30 Monday local | Common knowledge | Asia/Ho_Chi_Minh is UTC+7, no DST |
| First job of each run is `wait` | Done work | publish.yml `wait` has no `needs`; `publish` `needs: wait` (blog the same) |
| `decide()` code sample | Done work + Ran | `tools/wait_until.py` lines 24-33, verbatim; `pytest tests/test_wait_until.py`: 10 passed |
| Longest wait 5.5 h; docs: "each job in a workflow can run for up to 6 hours of execution time" | Done work + Sourced | `--max-wait-min` default 330; docs.github.com/en/actions/reference/limits (HTTP 200): "Each job in a workflow can run for up to 6 hours of execution time." |
| Decision table: 00:30 skip (7 h 45), 02:45 wait 5 h 30, 05:00 wait 3 h 15, 06:30 wait 1 h 45 (UTC date the day before), 16:09 go | Ran | `decide()` called for each local time on 18 Nov: skip "7:45:00 away (> 5:30:00)", 19800 s, 11700 s, 6300 s (23:30Z on the 17th), 0 s "go now"; the same cases are in the 10 tests |
| A run skips when an older scheduled run of the same workflow is still in progress | Done work | `other_waiters` docstring "in-progress scheduled runs older than this one"; `gh run list --status in_progress` |
| `gh` failure assumes no other waiter | Done work | `in_progress_schedule_runs` returns `[]` on error; test `test_gh_error_assumes_no_other_waiter` |
| After the wait, checkout of the default branch head | Done work | publish.yml / blog.yml `ref: ${{ github.event_name == 'schedule' && github.event.repository.default_branch || '' }}`; PR #33 text |
| Four review findings, all fixed before merge; PAUSE file merged during the wait | Done work | PR #33 "Checks": the four findings, "All 4 are fixed in the second commit"; "A `PAUSE` file or a fix merged during the wait therefore counts" |
| LinkedIn 18/19/20 Nov at 08:15; runs started 06:54/06:29/06:42 and waited | Record | `at` 01:15:14Z, 01:15:13Z, 01:15:12Z; `wait` jobs of runs 44203428305, 44421177849, 44639880347 from 23:54:45Z, 23:29:30Z, 23:42:23Z to 01:15:0xZ |
| These runs started about 3 h late or more | Derived | latest early cron 03:30; earliest start 06:29 (2 h 59 min) |
| Old skill line "No question at the end to bait comments." | Done work | PR #31 diff, removed line in `.claude/skills/write-post/SKILL.md` |
| Reversed about two hours after the first LinkedIn post | Record + Done work | LinkedIn 09:28 local; PR #31 merged 04:37Z = 11:37 local (2 h 09 min) |
| Question rule: own paragraph, before Part N, reader's own experience with this exact topic, never yes/no or "Agree?" | Done work | PR #31 write-post diff, step 6 |
| Thursday question quote | Done work | PR #31 diff and `content/2026-W47/2026-11-19-cloud-p2/post.md` on main, line 42, verbatim |
| Monday left alone; 4 posts edited; stored hashes stale; nothing held | Done work | PR #31 body and its Note |
| Short 1: 29 views, Short 2: 1 view; 57% average view of Short 1 | Record | metrics.csv 2026-11-20 rows; avg_view_pct 57.17 on the 2026-11-16 Short |
| DEV announcement article (the 4-week experiment): 15 views, 1 comment | Record | metrics.csv 2026-11-20, `article:why-i-am-building-lab-to-prod-in-public`; its description: "A four-week experiment" |
| Facebook and YouTube 0 followers | Record | metrics.report "Followers during the week": 0 -> 0 |
| LinkedIn numbers absent (manual export) | Record | no LinkedIn rows in metrics.csv |
| Every tracked channel post due by Friday posted or scheduled; LinkedIn 3 of 5 at 08:15; the other 2 before the fix | Record | metrics.report: 12 of 13, the 13th is the 21 Nov DEV article; fix merged 17 Nov 17:33 local, after both late posts |
| 00:30 cron on time would skip; 03:30 cron on time would wait 4 h 45 min | Ran | `decide()` at 00:30 local: skip; at 03:30 local: 17100 s |
| Runbook: start by hand at 09:30 | Done work | PR #33 operations.md: "If a morning post is still missing at 09:30, run the workflow by hand." |
| Quality-gate deep dive promised for 28 Nov is parked; topics wait for merged work | Record | build log #1 (dated 2026-11-21): "Next Saturday's article is ... how to build a quality gate for LLM output"; `content/calendar.yaml` parked list and its comment "goes back into a week ... once the work behind it is merged" |
| This week's experiment: hook opens with a measured number | Record | calendar 2026-W48 `experiment` |
| All 8 external links | Checked | curl: HTTP 200 for each |

Fixed in this pass: "The run I called skipped was not skipped" stated as fact, but the run does not name its cron; now "most likely the 08:15 run: not skipped, just 6 h 40 min late", with the reason (the backup cron was merged after its slot). "already waiting" is now "still in progress" (the code counts any in-progress older scheduled run). "about two hours after the first post" is now "the first LinkedIn post" (the X post went out at 08:30 local, 3 h 07 min before PR #31). "What surprised me" said "I built a fix that depends on the bug it works around": only the 00:30 cron does; the 03:30 cron on time waits 4 h 45 min and works, so it now says "half of the fix". "a cost I nearly missed" (not in any record; PR #31 states the stale hashes at merge time) is now "one side effect". "that topic has none yet" (merged judge and format-check work exists near that topic) is now "waits until the work behind it is merged", the calendar's own rule. Trimmed to 1,497 words of body (validate has no article error; `wc -w` on the whole file is 1,556 because it counts the front matter).
Kept as the author's opinion: "The stale commit was the serious one". Heading "I called it a skipped run, and I was wrong" kept: issue #32, written by the author, counts the 16 Nov run as late.
Open for the author: numbers stop at 20 Nov (W47 report, LinkedIn export and the 21 Nov DEV post are not in); the ledger entry `l2p-wait-for-slot` says "the 6 h job limit" while the code skips above 5.5 h (the article says 5.5 h).
