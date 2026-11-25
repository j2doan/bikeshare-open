"""Guard rails on the ingest contract and the trained model's behaviour."""
import pandas as pd
import pytest
from sklearn.metrics import r2_score

from src.config import LAG_WARMUP, TARGET
from src.features import build_features, feature_columns, reindex_to_calendar
from src.ingest import load_raw
from src.train import MODELS, temporal_split


@pytest.fixture(scope="module")
def raw():
    return load_raw().sort_values("dteday").reset_index(drop=True)


@pytest.fixture(scope="module")
def feats(raw):
    return build_features(raw)


def test_calendar_is_complete_before_lagging(raw):
    """The reindexed frame must have no gaps, or the lags are wrong."""
    grid = reindex_to_calendar(raw)
    assert set(grid.dteday.diff().dropna().dt.days.unique()) == {1}


def test_only_expected_rows_are_dropped(raw, feats):
    """Rows may only vanish for the lag warm-up or downstream of a genuinely
    absent day -- never because an encoder produced a silent NaN.

    Accounting: the first LAG_WARMUP days have no complete history. Each
    absent calendar day m costs the LAG_WARMUP rows after it (cnt_lag_1 is
    NaN on m+1, cnt_roll_7 is NaN on m+1..m+7, cnt_lag_7 on m+7; their
    union is 7 rows). Day m itself was never in `raw`, so it is not a loss.
    The bound is exact for the current feature set; add a longer lag and
    LAG_WARMUP in src/config.py must grow with it.
    """
    full = pd.date_range(raw.dteday.min(), raw.dteday.max(), freq="D")
    missing_days = len(full) - len(raw)
    allowed_loss = LAG_WARMUP + LAG_WARMUP * missing_days
    lost = len(raw) - len(feats)
    assert lost <= allowed_loss, f"lost {lost} rows; expected at most {allowed_loss}"


def test_beats_the_mean_baseline(feats):
    """A model that cannot beat predicting the training mean is not a result."""
    cols = feature_columns(feats)
    train, _, test = temporal_split(feats)
    ridge = MODELS["ridge"]
    ridge.fit(train[cols], train[TARGET])
    assert r2_score(test[TARGET], ridge.predict(test[cols])) > 0.4


def test_persistence_baseline_is_reported():
    """The baseline that matters for a lag-driven model is 'yesterday again'.
    It must be in the comparison, whatever its score."""
    assert "baseline_persistence" in MODELS


def test_every_raw_column_is_classified(raw):
    """A new column in the raw CSV must be classified in src/config.py
    (forbidden, a feature source, or ignored) before the pipeline runs."""
    from src.config import CLASSIFIED

    unclassified = set(raw.columns) - CLASSIFIED
    assert not unclassified, f"unclassified raw columns: {sorted(unclassified)}"
    # The check itself must be able to fail.
    assert set(raw.assign(mystery_col=0).columns) - CLASSIFIED == {"mystery_col"}


def test_relative_target_inverts_each_transform():
    """The wrapper must add the base back (or undo the log) exactly. A model
    that always predicts 'no change' (0 / 1 / log 5) must return the base
    (or 5) for every row."""
    import numpy as np
    from sklearn.dummy import DummyRegressor

    from src.train import RelativeTarget

    X = pd.DataFrame({"cnt_roll_7": [1000.0, 2000.0, 4000.0]})
    y = pd.Series([1100.0, 1900.0, 4200.0])
    cases = [
        ("diff", 0.0, [1000.0, 2000.0, 4000.0]),
        ("ratio", 1.0, [1000.0, 2000.0, 4000.0]),
        ("log", float(np.log(5.0)), [5.0, 5.0, 5.0]),
    ]
    for mode, const, expected in cases:
        model = RelativeTarget(DummyRegressor(strategy="constant", constant=const),
                               base="cnt_roll_7", mode=mode)
        model.fit(X, y)
        assert model.predict(X) == pytest.approx(expected), mode
