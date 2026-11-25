"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train
"""
import argparse
import json

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import METRICS, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


class RelativeTarget(BaseEstimator, RegressorMixin):
    """Fit a model on a target made relative to a column known at prediction
    time, then convert predictions back to rides.

    diff:  z = cnt - base        predict z + base
    ratio: z = cnt / base        predict z * base
    log:   z = log(cnt)          predict exp(z); base is unused
    `base` must be an already-shifted column (cnt_lag_7, cnt_roll_7)."""

    def __init__(self, model, base="cnt_roll_7", mode="diff"):
        self.model = model
        self.base = base
        self.mode = mode

    def _base(self, X):
        return X[self.base].to_numpy(dtype=float)

    def fit(self, X, y):
        y = np.asarray(y, dtype=float)
        z = {"diff": lambda: y - self._base(X),
             "ratio": lambda: y / self._base(X),
             "log": lambda: np.log(y)}[self.mode]()
        self.model_ = clone(self.model).fit(X, z)
        return self

    def predict(self, X):
        z = self.model_.predict(X)
        return {"diff": lambda: z + self._base(X),
                "ratio": lambda: z * self._base(X),
                "log": lambda: np.exp(z)}[self.mode]()


# Exercise 4: name -> (base column, mode). Only the booster is transformed.
TRANSFORMS = {
    "diff_roll7": ("cnt_roll_7", "diff"),
    "ratio_roll7": ("cnt_roll_7", "ratio"),
    "diff_lag7": ("cnt_lag_7", "diff"),
    "log": (None, "log"),
}


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def fit_and_score() -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    for name, model in MODELS.items():
        model.fit(train[cols], train[TARGET])
        results[name] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in [("valid", valid), ("test", test)]
        }
    return results


def fit_and_score_transforms(names: list[str], with_test: bool = False) -> dict:
    """Exercise 4. Every run carries both baselines, ridge and the untransformed
    hgb next to each transformed hgb. Validation only unless with_test is set,
    so the test set is never looked at while choosing a transform."""
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)
    parts = [("valid", valid)] + ([("test", test)] if with_test else [])

    models = dict(MODELS)
    for name in names:
        base, mode = TRANSFORMS[name]
        models[f"hgb_{name}"] = RelativeTarget(MODELS["hgb"], base=base, mode=mode)

    results = {"n_train": len(train), "n_valid": len(valid)}
    if with_test:
        results["n_test"] = len(test)
    for name, model in models.items():
        model = clone(model).fit(train[cols], train[TARGET])
        results[name] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in parts
        }
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-transform", choices=["all", *TRANSFORMS],
                    help="Exercise 4: validation-only comparison; default run is untouched")
    ap.add_argument("--test", action="store_true",
                    help="also score test; use once, on the single chosen transform")
    args = ap.parse_args()
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    if args.target_transform:
        if args.test and args.target_transform == "all":
            ap.error("--test is for one chosen transform, not 'all'")
        names = list(TRANSFORMS) if args.target_transform == "all" else [args.target_transform]
        res = fit_and_score_transforms(names, with_test=args.test)
        out = METRICS.with_name(f"exercise4_{args.target_transform}{'_test' if args.test else ''}.json")
        out.write_text(json.dumps(res, indent=2))
    else:
        res = fit_and_score()
        METRICS.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
