# Seeded faults

Each fault was introduced by the agent (Claude Sonnet 5.5, Claude Code) on my instruction, in its own commit. The fix is the next commit. Output below is real, copied from the run.

## Fault 1: a forbidden column added to `feature_columns`

**Change**: `src/features.py` line 89.

```diff
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN or c == "casual"]
```

**Red test** (`make test`):

```
E   AssertionError: forbidden columns in feature set: {'casual'}
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: forbidden columns in feature set: {'casual'}
1 failed, 15 passed in 13.51s
make: *** [Makefile:16: test] Error 1
```

**Hook stderr** (excerpt, the hook ran `tests/test_leakage.py` right after the edit):

```
PostToolUse:Edit hook reported a problem
Leakage tests failed after editing .../src/features.py:
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: forbidden columns in feature set: {'casual'}
1 failed, 7 passed in 4.90s
```

**Turns to fix**: 1. The agent reverted the line and ran `make test` (16 passed).

## Fault 2: `.shift(1)` deleted from `cnt_roll_7`

**Change**: `src/features.py` line 76.

```diff
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
```

**Red test** (`make test`):

```
E     comparison failed
E     Obtained: 4389.0
E     Expected: 4414.857142857143 ± 0.00441486
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
1 failed, 15 passed in 13.40s
make: *** [Makefile:16: test] Error 1
```

**Hook stderr** (excerpt, the hook ran `tests/test_leakage.py` right after the edit):

```
PostToolUse:Edit hook reported a problem
Leakage tests failed after editing .../src/features.py:
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
1 failed, 7 passed in 4.92s
```

**Turns to fix**: 1. The agent restored `.shift(1)` and ran `make test` (16 passed).

## Fault 3: the `raise` removed from `encode_weather`

**Change**: `src/features.py`, inside `encode_weather`.

```diff
     unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
```

**First result, no test caught it.** With the `raise` removed, all 16 existing tests passed and the hook printed nothing. No test in the starter calls `encode_weather` or checks its error. An unseen weather label would turn into a NaN and `dropna()` would delete the row without a warning.

**So I added a test** (`test_encode_weather_rejects_unknown_label` in `tests/test_leakage.py`, committed separately). It is in `test_leakage.py` because that is the file the hook runs.

**Red test** (`pytest tests/test_leakage.py`, with the fault still in place):

```
E       Failed: DID NOT RAISE ValueError
FAILED tests/test_leakage.py::test_encode_weather_rejects_unknown_label
1 failed, 8 passed in 5.52s
```

**Hook**: silent on the original edit (no test existed). After the test was added, I ran the hook script by hand on the same state and it exited 2 with `Leakage tests failed after editing src/features.py:`, so a fresh seed of this fault now triggers it.

**Turns to fix**: 1. The agent restored the `if unknown: raise ...` block and ran `make test` (17 passed, one more than before because of the new test).

## Fault 4: a Bash `cp` into `data/raw/`, which the hook cannot see

**Attempt**: I asked the agent to copy `data/raw/bike_daily.csv` to `/tmp`, change the `temp` value on the 2011-01-03 row with `sed`, and `cp` the modified file back over the original, using Bash and not the Edit or Write tools. The agent ran it as one chained command.

**What happened**: Claude Code did not run the command. It was denied twice, with the reason "permission denied · rule from shared project settings". The agent stopped and did not look for another way. `data/raw/bike_daily.csv` was unchanged afterward (SHA-256 still begins `a6bed1577f6e4de5`, and no `/tmp` copy was created).

The PostToolUse hook was not involved. It only watches Edit and Write on `src/` files, so it would have stayed silent even if the copy had run. The only data rules in `.claude/settings.json` are the denies on `Write(./data/raw/**)` and `Edit(./data/raw/**)`. It looks like this Claude Code version also applies them to a Bash command that writes into that folder. I did not test other command shapes to find a way around the block.

**What would catch it**:

1. **The permission rule that blocked it.** This is what stopped it here, but it only works on patterns the permission layer recognises. A write that is not matched would pass, and the hook would still not notice.
2. **A hash check in `make data`.** `make data` currently skips the download when the file exists and only checks the column names and that there are at least 700 rows. A changed `temp` value would pass. Comparing the file's SHA-256 against `a6bed1577f6e4de5…` would catch any change, however the file was written. This is the catcher I would choose, because it does not depend on recognising the command that did the writing. I have not implemented it.
3. A PreToolUse hook on Bash or a Stop hook that checks the hash would also work, but they are more setup for the same result.
