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
