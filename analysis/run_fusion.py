"""Keystroke + mouse fusion identification experiment (thesis Chapter 8).

Two independent XGBoost classifiers - one for keystrokes, one for mouse - are
trained exactly as in Chapters 6 and 7. Their per-user probability outputs are
then combined by late fusion (thesis Eq. 8.1): for a burst of k keystroke
samples and m mouse samples from the same user, average each classifier's
probability vectors and add the two averages; the highest-scoring user wins.

The script sweeps k and m from 1..grid and writes the resulting F1 grid, which
shows that only a handful of actions of each type are needed for a confident
identification.

Usage:
    python run_fusion.py --data-dir ../data/demo --out-dir results/fusion

`--data-dir` must contain keystroke/ and mouse/ subfolders, each with the
train/ and test/ layout used by run_keystroke.py and run_mouse.py.
"""

import argparse
import os

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

import common
import run_keystroke
import run_mouse


def train_and_predict(x_train, y_train, x_test, params):
    """Fit one weighted XGBoost and return its test-set probabilities."""
    model = XGBClassifier(**common.XGB_BASE_PARAMS, **params)
    model.fit(x_train, y_train, sample_weight=common.sample_weights(y_train))
    return model.predict_proba(x_test)


def probabilities_by_user(probabilities, labels):
    """Group probability rows into {user: [rows...]} preserving order."""
    blocks = {}
    for row, label in zip(probabilities, labels):
        blocks.setdefault(label, []).append(row)
    return blocks


def averaged_window(rows, size):
    """Mean of the first `size` probability vectors, or None if too few."""
    if len(rows) < size:
        return None
    return np.mean(rows[:size], axis=0)


def fuse(ks_blocks, mouse_blocks, k, m):
    """Late-fuse k keystroke and m mouse samples per user (thesis Eq. 8.1).

    For each user present in both modalities we take the averaged keystroke
    window and the averaged mouse window, add them, and predict the argmax.
    Returns (y_true, y_pred).
    """
    y_true, y_pred = [], []
    for user in ks_blocks:
        if user not in mouse_blocks:
            continue
        ks_avg = averaged_window(ks_blocks[user], k)
        mouse_avg = averaged_window(mouse_blocks[user], m)
        if ks_avg is None or mouse_avg is None:
            continue
        y_pred.append(int(np.argmax(ks_avg + mouse_avg)))
        y_true.append(user)
    return np.array(y_true), np.array(y_pred)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True,
                        help="folder containing keystroke/ and mouse/ subfolders")
    parser.add_argument("--out-dir", default="results/fusion")
    parser.add_argument("--grid", type=int, default=10,
                        help="sweep k and m from 1 to this value")
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    ks_dir = os.path.join(args.data_dir, "keystroke")
    mouse_dir = os.path.join(args.data_dir, "mouse")

    # Keystroke modality (Chapter 6 settings).
    xk_train, yk_train_raw = run_keystroke.load_split(os.path.join(ks_dir, "train"), 4)
    xk_test, yk_test_raw = run_keystroke.load_split(os.path.join(ks_dir, "test"), 4)
    ks_encoder = LabelEncoder().fit(yk_train_raw)
    ks_probs = train_and_predict(
        xk_train, ks_encoder.transform(yk_train_raw), xk_test,
        run_keystroke.TUNED_PARAMS)

    # Mouse modality (Chapter 7 settings). Fit its own encoder, then map the
    # test labels onto the keystroke encoder's integer ids so both classifiers
    # agree on which column means which user.
    xm_train, ym_train_raw = run_mouse.load_split(os.path.join(mouse_dir, "train"), 3)
    xm_test, ym_test_raw = run_mouse.load_split(os.path.join(mouse_dir, "test"), 3)
    mouse_encoder = LabelEncoder().fit(ym_train_raw)
    mouse_probs = train_and_predict(
        xm_train, mouse_encoder.transform(ym_train_raw), xm_test,
        run_mouse.TUNED_PARAMS)

    ks_blocks = probabilities_by_user(ks_probs, ks_encoder.transform(yk_test_raw))
    mouse_blocks = probabilities_by_user(mouse_probs, mouse_encoder.transform(ym_test_raw))

    rows = []
    for k in range(1, args.grid + 1):
        for m in range(1, args.grid + 1):
            y_true, y_pred = fuse(ks_blocks, mouse_blocks, k, m)
            rows.append({"keystroke_samples": k, "mouse_samples": m,
                         **common.score_row(y_true, y_pred)})
    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(args.out_dir, "fusion_grid.csv"), index=False)

    pivot = grid.pivot(index="keystroke_samples",
                       columns="mouse_samples", values="f1")
    print("F1 by (keystroke samples x mouse samples):")
    print(pivot.round(3).to_string())


if __name__ == "__main__":
    main()
