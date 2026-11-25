# Audit of a teammate's repo

**Repo audited**: https://github.com/vcho116055/DSC180A-Methodology-6, commit `40b3750`.

**How it was run**: the starter's `leakage-auditor` subagent (Claude Sonnet 5.5, Claude Code) reviewed everything the teammate changed since the starter commit, plus `REPORT.md` and the committed metrics. I told it to read only. It did not run any of their code, so anything that needs execution is marked unverified.

## Auditor output (verbatim)

The only edits to the auditor's text are the removed indentation and one local folder path, replaced with `[local path omitted]`.

Two findings, both about reporting. Checks 1 to 4 pass. I read the code and committed metrics only and ran nothing.

**Finding 1: Check 5, baselines missing next to the Exercise 4 scores.**
- **Where:**
  - REPORT.md lines 56-64 (the validation table) has no mean or persistence row.
  - REPORT.md lines 80-86 (the test table) has persistence but no mean baseline.
  - reports/metrics_diff_cnt_roll_7.json holds only `ridge_diff_cnt_roll_7` and `hgb_diff_cnt_roll_7`, with no baseline keys.
- **Why it matters:**
  - **Where the baselines come from:** `fit_and_score` in src/train.py runs only the models it is passed. In `--target-transform` mode that is just the two `RelativeTarget` models. Persistence (valid R2 0.4507, test 0.5099) appears in the Exercise 4 write-up only because someone copied it in by hand. The mean baseline (valid -0.6894, test -1.7717) is not copied in at all.
  - **Effect on the verdict:** the "defensible" verdict on the 0.7139 validation score and the 0.6331 test score is made without the mean baseline next to those scores.
  - **Rule broken:** the project rule is to report both baselines alongside every model.
- **Minimal fix:** in src/train.py, when `models` is passed, merge `baseline_mean` and `baseline_persistence` from `MODELS` into the dict. Then add both rows to the two Exercise 4 tables in REPORT.md.

**Finding 2: an explanation in REPORT.md lines 24-27 is wrong, but no reported number is.**
- **The claim:** the report says the longer warm-up "only removes January 2011 rows" from training, and that this is why the mean baseline moved from -0.93 to -0.69.
- **What the code does:** src/features.py line 78 uses `rolling(28)` on a calendar-reindexed series. The missing day 2011-03-10 is a NaN, so the next 28 days also have a NaN in their window and are dropped.
- **Row accounting:** 728 raw rows minus 672 kept rows is 56 lost, which equals 28 warm-up rows plus 28 rows after the gap. The train set loses 42 rows (348 to 306), about 21 in January and about 21 in March and April. The `test_only_expected_rows_are_dropped` bound (`LAG_WARMUP + LAG_WARMUP * missing_days` = 56) matches this exactly, so no rows are lost silently.
- **Fix:** reword the sentence to say the dropped rows include March and April 2011. The metrics stay as they are.

**Unverified (needs execution):**
- The ablation figures, ridge 0.6462 and hgb 0.1929 "on identical training rows". They are not in any committed metrics file.
- The post-hoc error breakdowns in Exercise 5: the median errors, the 43% closer-day share, the 427-ride bias, and the 57% of test days above 6,043 rides.

**Checks that pass:**
- **Leakage:** no feature contains `cnt` at time t. `casual` and `registered` are excluded through `FORBIDDEN`, and `RelativeTarget` uses only the shifted `cnt_roll_7` as its base.
- **Temporal ordering:** every rolling feature calls `.shift(1)` first. The split is by date. The `StandardScaler` sits inside the pipeline and is fit on train only. The transform was chosen on validation and the test set was scored once.
- **Calendar gaps:** `reindex_to_calendar` runs before any lag is built.

Files are under [local path omitted]. The ones to open are src/train.py, src/features.py, REPORT.md and reports/metrics_diff_cnt_roll_7.json.

I did not check the .claude, agent or docs changes beyond the diff, because none of them can change a metric.

## My verdict

**Neither finding changes a number the teammate reported.** The audit found no leakage, no split problem, and no silent row loss.

**Finding 1 matters most.** I agree with it. The Exercise 4 verdict of "defensible" is stated without the mean baseline beside the scores, which breaks the rule that both baselines go next to every model. It would not flip their conclusion, because the mean baseline is far below every model they report, but a reader cannot see that from their tables.

**Finding 2 is a wording error.** I agree with it too. The longer warm-up also drops rows after the missing 2011-03-10, so the training set loses March and April days as well as January. Their explanation for why the mean baseline moved is incomplete, but the numbers are right.

**What I could not check.** The auditor did not run their code, so the ablation figures and the error breakdowns in the teammate's report are unverified. I checked the two findings above against their `REPORT.md`, `src/features.py` and `reports/metrics_diff_cnt_roll_7.json`.
