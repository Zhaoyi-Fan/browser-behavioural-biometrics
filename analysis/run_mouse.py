"""Mouse-dynamics identification experiment (thesis Chapter 7).

Trains an XGBoost classifier on point-and-click features and reports how
identification accuracy grows as more consecutive mouse actions are observed.

Expected layout (see docs/data-format.md):

    <data-dir>/
        train/  user00_mouse.csv, user01_mouse.csv, ...
        test/   user00_mouse.csv, user01_mouse.csv, ...

Usage:
    python run_mouse.py --data-dir ../data/demo/mouse --out-dir results/mouse
"""

import argparse
import glob
import os

import numpy as np
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

import common
import mouse_features as mf

# Tuned hyper-parameters from thesis Table 7.4.
TUNED_PARAMS = {"learning_rate": 0.3, "n_estimators": 600,
                "max_depth": 5, "min_child_weight": 3}


def load_split(split_dir, iqr_ratio):
    """Build (features, labels) for every *_mouse.csv in a split folder,
    dropping the two device-dependent columns (EXCLUDED_FEATURES)."""
    features, labels = [], []
    for path in sorted(glob.glob(os.path.join(split_dir, "*_mouse.csv"))):
        user = os.path.basename(path).split("_")[0]
        for sample in mf.extract_user_samples(path, iqr_ratio):
            features.append(sample)
            labels.append(user)
    x = np.array(features, dtype=float)
    if len(x):
        x = np.delete(x, mf.EXCLUDED_FEATURES, axis=1)
    return x, np.array(labels)


def kept_feature_names():
    return [n for i, n in enumerate(mf.FEATURE_NAMES)
            if i not in mf.EXCLUDED_FEATURES]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True,
                        help="folder containing train/ and test/ subfolders")
    parser.add_argument("--out-dir", default="results/mouse")
    parser.add_argument("--iqr-ratio", type=int, default=3,
                        help="noise-trim threshold in IQRs (thesis uses 3)")
    parser.add_argument("--max-window", type=int, default=30)
    args = parser.parse_args()

    x_train, y_train_raw = load_split(os.path.join(args.data_dir, "train"), args.iqr_ratio)
    x_test, y_test_raw = load_split(os.path.join(args.data_dir, "test"), args.iqr_ratio)
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
        class_names=encoder.classes_, prefix="mouse_")
    common.save_feature_importance(
        model, kept_feature_names(),
        os.path.join(args.out_dir, "mouse_feature_importance.png"))

    print(scores.to_string(index=False))
    print(f"\nF1: {scores.iloc[0]['f1']:.3f} (1 action) -> "
          f"{scores.iloc[-1]['f1']:.3f} ({args.max_window} actions)")


if __name__ == "__main__":
    main()
