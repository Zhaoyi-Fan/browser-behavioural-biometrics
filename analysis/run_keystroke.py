"""Keystroke-dynamics identification experiment (thesis Chapter 6).

Trains an XGBoost classifier on 4-graph keystroke features and reports how
identification accuracy grows as more consecutive keystrokes are observed.

Expected layout (see docs/data-format.md):

    <data-dir>/
        train/  user00_keystroke.csv, user01_keystroke.csv, ...
        test/   user00_keystroke.csv, user01_keystroke.csv, ...

Each user's raw CSV is segmented and turned into 4-graph samples; the model is
fit on the train split (with inverse-frequency sample weights) and evaluated on
the test split with the accumulative method.

Usage:
    python run_keystroke.py --data-dir ../data/demo/keystroke --out-dir results/keystroke
"""

import argparse
import glob
import os

import numpy as np
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

import common
import keystroke_features as kf

# Tuned hyper-parameters from thesis Table 6.5.
TUNED_PARAMS = {"learning_rate": 0.3, "n_estimators": 600,
                "max_depth": 5, "min_child_weight": 5}


def load_split(split_dir, n):
    """Build (features, labels) for every *_keystroke.csv in a split folder.

    The label is the filename prefix before the first underscore, e.g.
    "user03_keystroke.csv" -> "user03".
    """
    features, labels = [], []
    for path in sorted(glob.glob(os.path.join(split_dir, "*_keystroke.csv"))):
        user = os.path.basename(path).split("_")[0]
        samples = kf.extract_user_samples(path, n)
        features.extend(samples)
        labels.extend([user] * len(samples))
    return np.array(features, dtype=float), np.array(labels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True,
                        help="folder containing train/ and test/ subfolders")
    parser.add_argument("--out-dir", default="results/keystroke")
    parser.add_argument("--ngraph", type=int, default=4,
                        help="keystrokes per sample (thesis uses 4)")
    parser.add_argument("--max-window", type=int, default=30)
    args = parser.parse_args()

    x_train, y_train_raw = load_split(os.path.join(args.data_dir, "train"), args.ngraph)
    x_test, y_test_raw = load_split(os.path.join(args.data_dir, "test"), args.ngraph)
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
        class_names=encoder.classes_, prefix="keystroke_")
    common.save_feature_importance(
        model, kf.feature_names(args.ngraph),
        os.path.join(args.out_dir, "keystroke_feature_importance.png"))

    print(scores.to_string(index=False))
    single = scores.iloc[0]["f1"]
    best = scores.iloc[-1]["f1"]
    print(f"\nF1: {single:.3f} (1 sample) -> {best:.3f} "
          f"({args.max_window} samples)")


if __name__ == "__main__":
    main()
