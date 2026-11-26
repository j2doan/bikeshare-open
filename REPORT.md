# Bikeshare demand forecast: report

## Results

We forecast daily rides (`cnt`) for Capital Bikeshare, 2011 to 2012. Train is 2011, validation is the first half of 2012, test is the second half of 2012. In the table below, "Before" represents the starter code. "After" represents the model after adding one feature, `temp_lag_1` (yesterday's temperature). The "after" rows match `reports/metrics.json`. MAE is the average miss in rides per day.

| Model | Version | Validation R² | Validation MAE | Test R² | Test MAE |
|---|---|---|---|---|---|
| mean baseline | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| mean baseline | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| persistence baseline (yesterday's count) | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| persistence baseline (yesterday's count) | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after | 0.6951 | 746.1 | 0.6238 | 876.6 |
| gradient boosting (hgb) | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| gradient boosting (hgb) | after | 0.1936 | 1321.1 | -0.5785 | 2036.7 |

**The baselines.** They are the same before and after because they never use the features. The mean baseline always guesses the 2011 average. The persistence baseline guesses yesterday's count.

**Hgb.** "hgb" is scikit-learn's HistGradientBoostingRegressor, a tree-based model. It predicts by splitting the training days into groups and returning the average rides of the days in each group. That means it can never output more than the busiest group it learned from. This is the cause of its trouble in 2012 (see Headline finding).

**How R² is calculated.** R² is 1 minus a ratio. The top is the model's total squared miss. The bottom is the total squared miss of always guessing the average ride count of the period being scored. The square sits inside that ratio, not on R² itself, so R² is not a squared number and can go negative. 1 is perfect. 0 is no better than the flat guess. Below 0 means the model is worse than the flat guess.

## Headline finding

On the test set (second half of 2012), ranked by R², hgb is worst, persistence is in the middle, and ridge is best (hgb -0.5785, persistence 0.5099, ridge 0.6238), so hgb does worse than a flat guess of that period's average. The reason is growth. Ridership was about 65% higher in 2012 than in 2011, and hgb trained on 2011 only, so on busy 2012 days it keeps guessing 2011-sized numbers and comes in too low. Ridge fits a line, so it can follow the growth. I treat this as the main result, not a bug.

The feature `temp_lag_1` (yesterday's temperature) raised ridge's validation R² from 0.6475 to 0.6951 and lowered hgb's from 0.2185 to 0.1936, and I kept it because ridge's gain is far above the 0.01 that could be random noise.

## Exercise 4: target transformation

**Problem.** Hgb fails because it never saw 2012-sized ride counts. A transformation changes what the model is asked to predict. Instead of "how many rides tomorrow", we ask for something that looks similar in 2011 and 2012, then convert back to rides. The base is always built from days before today, so no future information leaks in.

**Why these four.** I was tasked to select a transformation that lets the tree model compete. I was not given specific ones to ivnestigate, so I took the initiative and came up with 4 (arbitrary number) transformations. I wanted each option to change the target in a different way:
- ratio to the 7-day average (`cnt_roll_7`): predict "how many times the recent average", for example 1.1, then multiply back
- difference from the 7-day average: predict "rides above or below the recent average"
- difference from the same day last week (`cnt_lag_7`): the same idea with last week's value as the base
- log of rides: a control. It shrinks the numbers but uses no recent history, so it tests whether any gain just comes from rescaling.

This is not an exhaustive search. I did not try, for example, a ratio to last week's count. I kept the list short and fixed it before I looked at any score. Every extra option I try on the same 182 validation days gives another chance that one wins by luck, and the more I try, the less the winning validation score means. Test was then scored once, for the winner only.

**Validation only (first half of 2012), with the baselines and ridge beside every model.** The ridge and untransformed hgb rows are the "after" versions, with `temp_lag_1` included.

| Model | Validation R² | Validation MAE |
|---|---|---|
| mean baseline | -0.9318 | 2002.2 |
| persistence baseline | 0.4507 | 900.6 |
| ridge | 0.6951 | 746.1 |
| hgb, no transformation | 0.1936 | 1321.1 |
| hgb, ratio to 7-day average | 0.7638 | 657.1 |
| hgb, difference from 7-day average | 0.7261 | 704.5 |
| hgb, difference from same day last week | 0.4955 | 957.9 |
| hgb, log | 0.1605 | 1334.7 |

I picked the ratio to the 7-day average. It had the best validation score, 0.0377 R² ahead of the next best. That gap is too large to ignore, so I did not pick a simpler option.

**Test, scored once, on the chosen transformation only.** Ridge and untransformed hgb are again the "after" versions.

| Model | Test R² | Test MAE |
|---|---|---|
| mean baseline | -2.1441 | 2847.7 |
| persistence baseline | 0.5099 | 840.1 |
| ridge | 0.6238 | 876.6 |
| hgb, no transformation | -0.5785 | 2036.7 |
| hgb, ratio to 7-day average | 0.6287 | 837.5 |

**Verdict: defensible, with a caveat.**
- It uses only days before today.
- It fixes the weakness from the Headline finding. Hgb no longer has to guess a ride count it never saw. It guesses a ratio near 1, which looks the same in both years, and multiplies by the recent average.
- The log option did not help (0.1605), so the gain comes from using recent demand as the base, not from rescaling.
- I chose among four on one validation window, and the test result shows the cost. Hgb's lead over ridge shrank from 0.0687 on validation to 0.0049 on test. On MAE, hgb (837.5) only just beats persistence (840.1).

The transformation runs only through `python -m src.train --target-transform NAME`. `reports/metrics.json` stays the untransformed result.

## Exercise 5: ridge vs persistence

Ridge is worth deploying. On the test set it scores R^2 0.6238 against 0.5099 for persistence (guessing that each day's rides will equal the day before), and on validation 0.6951 against 0.4507. That means ridge leaves about 23% less of the day-to-day variation unexplained (1 minus R^2 is 0.376 against 0.490). I picked ridge because it better predicts for what I care most: sudden change. If today is sunny and tomorrow is sunny, I would care less because it is a normal occurrence. If tomorrow suddenly started raining, then that would be of interest. "Yesterday" in these cases would be the wrong guide, and those scenarios are when I most need a good forecast. Persistence cannot see that change, while ridge takes the day's weather as an input and can respond to it. I did not test this on weather-change days separately, so it is my reasoning and not a measured result. The cost is in average miss (MAE). Ridge is slightly worse on test (876.6 rides against 840.1) after being better on validation (746.1 against 900.6). That gap is about 4% and reversed between validation and test, so I do not treat it as settled. I accept it because a missed rain day costs more than a small error on a calm one. Ridge also needs a weather forecast to work, and it was trained on 2011 only, so its edge should be rechecked as ridership grows.

## Attribution

Model: Claude Sonnet 5.5 (size not disclosed by Anthropic), run through Claude Code. I first planned to use a local qwen3.5:27b, but it took about 10 minutes per simple prompt. I switched with my professor's permission: https://piazza.com/class/muao8hx5aj77t/post/197

**Files or functions the agent generated:**
- `temp_lag_1` in `src/features.py`
- `RelativeTarget`, `fit_and_score_transforms` and the `--target-transform` flag in `src/train.py`
- the column lists in `src/config.py`
- new tests in `tests/test_leakage.py` and `tests/test_contract.py`
- the `seed-fault` skill
- the seeded faults and their fixes
- the audit run output
- first drafts of the `docs/` text and this report

**Decisions that were mine:**
- Add `temp_lag_1` and keep it (`docs/DECISIONS.md`, ADDED FEATURE)
- Choose the ratio to the 7-day average and call it defensible (`docs/DECISIONS.md`, SELECTED TRANSFORMATION)
- What went into `CLAUDE.md` (`docs/DECISIONS.md`, CLAUDE.md CHANGES)

**Audit run findings** (`reports/audit.jsonl`, leakage none). Two minor findings, and neither changes a number. The README says 14 tests but 18 pass, which is starter text I did not edit. The line-endings finding is a false alarm caused by WSL and Windows git disagreeing about line endings.
