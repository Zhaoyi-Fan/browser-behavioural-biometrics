"""Mobile touch-dynamics identification experiment (thesis Chapter 9).

Unlike the keystroke/mouse chapters, the mobile study uses an existing public
dataset (Kim and Kang, 2020) whose samples already come as fixed-length feature
vectors - one per digraph, 32 features covering timing, key values, touch
coordinates and motion-sensor readings. There is nothing to segment, so this
script just loads the feature CSVs, trains XGBoost and runs the same
accumulative evaluation as the other experiments.

Input CSVs are plain "features..., user_label" rows (see docs/data-format.md).
Provide any number of CSVs for each split:

    python run_mobile.py --train sess1.csv sess2.csv sess3.csv \
                         --test sess4.csv --out-dir results/mobile
"""

import argparse
import os

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

import common

# Tuned hyper-parameters from thesis Table 9.1.
TUNED_PARAMS = {"learning_rate": 0.2, "n_estimators": 600,
                "max_depth": 6, "min_child_weight": 3}


def load_csvs(paths):
    """Stack several feature CSVs into (features, labels).

    Every row is a feature vector followed by the user label in the last
    column.
    """
    features, labels = [], []
    for path in paths:
        table = pd.read_csv(path, header=None).values
        features.extend(table[:, :-1].astype(float))
        labels.extend(table[:, -1])
    return np.array(features, dtype=float), np.array(labels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", nargs="+", required=True,
                        help="one or more training feature CSVs")
    parser.add_argument("--test", nargs="+", required=True,
                        help="one or more test feature CSVs")
    parser.add_argument("--out-dir", default="results/mobile")
    parser.add_argument("--max-window", type=int, default=30)
    args = parser.parse_args()

    x_train, y_train_raw = load_csvs(args.train)
    x_test, y_test_raw = load_csvs(args.test)
    print(f"train: {len(x_train)} samples   test: {len(x_test)} samples")

    encoder = LabelEncoder().fit(y_train_raw)
    y_train = encoder.transform(y_train_raw)
    y_test = encoder.transform(y_test_raw)

    model = XGBClassifier(**common.XGB_BASE_PARAMS, **TUNED_PARAMS)
    model.fit(x_train, y_train, sample_weight=common.sample_weights(y_train))

    probabilities = model.predict_proba(x_test)
    scores = common.accumulative_report(
        probabilities, y_test, args.out_dir,
        max_window=args.max_window,
        class_names=encoder.classes_, prefix="mobile_")

    print(scores.to_string(index=False))
    print(f"\nF1: {scores.iloc[0]['f1']:.3f} (1 sample) -> "
          f"{scores.iloc[-1]['f1']:.3f} ({args.max_window} samples)")


if __name__ == "__main__":
    main()
