"""Shared helpers used by all four experiment pipelines.

Everything here is deliberately small and dependency-light: class weighting,
the accumulative (multi-sample) evaluation from thesis Eq. 6.1 / 7.43, and the
figure/report output that every experiment produces in the same shape.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

# XGBoost settings shared by every experiment. The per-experiment scripts only
# override the four tuned values (learning_rate, n_estimators, max_depth,
# min_child_weight); see thesis Tables 6.5, 7.4, 8.1 and 9.1.
#
# The thesis experiments ran with tree_method='gpu_hist' on an RTX 4090.
# 'hist' is the modern CPU equivalent and gives the same algorithm; pass
# device='cuda' to XGBClassifier if you have a GPU.
XGB_BASE_PARAMS = {
    "objective": "multi:softprob",
    "eval_metric": "mlogloss",
    "tree_method": "hist",
}


def inverse_frequency_weights(labels):
    """Per-class weight = n_samples / (class_count * n_classes).

    Used as sample weights when fitting XGBoost so that users who typed or
    clicked less do not get drowned out by heavy users (the raw dataset is
    quite imbalanced, see thesis Fig. 6.2 and 7.5).
    """
    labels = np.asarray(labels)
    counts = pd.Series(labels).value_counts()
    n_classes = len(counts)
    return {label: len(labels) / (count * n_classes) for label, count in counts.items()}


def sample_weights(labels):
    """Expand the per-class weights to one weight per sample."""
    per_class = inverse_frequency_weights(labels)
    return np.array([per_class[label] for label in labels])


def group_by_user(probabilities, labels):
    """Reorder prediction rows so each user's samples form one contiguous block.

    Within a block the original (chronological) order is preserved. The
    accumulative evaluation below slides a window over consecutive samples of
    the same user, which is what a website would see: a stream of actions all
    coming from the one visitor it is trying to identify.
    """
    probabilities = np.asarray(probabilities)
    labels = np.asarray(labels)
    blocks = {}
    for row, label in zip(probabilities, labels):
        blocks.setdefault(label, []).append(row)
    ordered_probs, ordered_labels = [], []
    for label in sorted(blocks):
        ordered_probs.extend(blocks[label])
        ordered_labels.extend([label] * len(blocks[label]))
    return np.array(ordered_probs), np.array(ordered_labels)


def accumulated_predictions(probabilities, labels, window):
    """Combine `window` consecutive same-user samples into one prediction.

    This is the accumulative method of thesis Eq. 6.1: the per-class
    probability vectors of the samples in the window are summed (equivalent
    to averaging, as far as the argmax is concerned) and the class with the
    highest total wins. Returns (y_true, y_pred) index arrays.

    `probabilities`/`labels` must already be grouped per user - see
    group_by_user().
    """
    y_true, y_pred = [], []
    for start in range(len(labels) - window + 1):
        # Same user at both ends of the window means the whole window belongs
        # to that user, because the samples are grouped into per-user blocks.
        if labels[start] != labels[start + window - 1]:
            continue
        combined = probabilities[start : start + window].sum(axis=0)
        y_pred.append(int(np.argmax(combined)))
        y_true.append(labels[start])
    return np.array(y_true), np.array(y_pred)


def score_row(y_true, y_pred):
    """The four metrics reported throughout the thesis (macro-averaged)."""
    return {
        "f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "precision": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "accuracy": accuracy_score(y_true, y_pred),
    }


def accumulative_report(probabilities, labels, out_dir, max_window=30,
                        class_names=None, prefix=""):
    """Score window sizes 1..max_window and write the standard outputs.

    Produces the "performance vs number of samples" table (thesis Tables 6.8,
    7.8, 9.3), the metric curves figure, and confusion matrices for window
    sizes 1, 5, 10, ... Returns the scores as a DataFrame.
    """
    os.makedirs(out_dir, exist_ok=True)
    probabilities, labels = group_by_user(probabilities, labels)

    rows = []
    for window in range(1, max_window + 1):
        y_true, y_pred = accumulated_predictions(probabilities, labels, window)
        rows.append({"samples": window, **score_row(y_true, y_pred)})

        if window == 1:
            report = classification_report(y_true, y_pred, output_dict=True,
                                           zero_division=0)
            pd.DataFrame(report).T.to_csv(
                os.path.join(out_dir, f"{prefix}classification_report.csv"))
        if window == 1 or window % 5 == 0:
            save_confusion_matrix(
                y_true, y_pred, class_names,
                os.path.join(out_dir, f"{prefix}confusion_{window}_samples.png"))

    scores = pd.DataFrame(rows)
    scores.to_csv(os.path.join(out_dir, f"{prefix}scores_by_window.csv"), index=False)
    save_metric_curves(scores, os.path.join(out_dir, f"{prefix}scores_by_window.png"))
    return scores


def save_confusion_matrix(y_true, y_pred, class_names, path):
    """Raw-count and row-normalised confusion matrices, side by side files."""
    for normalize, suffix in [(None, ""), ("true", "_normalised")]:
        cm = confusion_matrix(y_true, y_pred, normalize=normalize)
        if normalize:
            cm = np.round(cm, 3)
        fig, ax = plt.subplots(figsize=(10.24, 8))
        display = ConfusionMatrixDisplay(cm, display_labels=class_names)
        display.plot(cmap=plt.cm.Blues, include_values=normalize is not None, ax=ax)
        base, ext = os.path.splitext(path)
        fig.savefig(base + suffix + ext)
        plt.close(fig)


def save_metric_curves(scores, path):
    """Line plot of the four metrics against the accumulation window size."""
    fig, ax = plt.subplots(figsize=(10.24, 8))
    for metric in ["f1", "precision", "recall", "accuracy"]:
        ax.plot(scores["samples"], scores[metric] * 100, label=metric)
    ax.set_xlabel("Consecutive samples per identification")
    ax.set_ylabel("Score (%)")
    ax.set_yticks(range(0, 101, 5))
    ax.legend()
    ax.grid(True)
    fig.savefig(path)
    plt.close(fig)


def save_feature_importance(model, feature_names, path):
    """Horizontal bar chart of XGBoost feature importances, sorted."""
    scores = model.feature_importances_
    order = np.argsort(scores)
    fig, ax = plt.subplots(figsize=(10.24, max(8, len(scores) * 0.2)))
    ax.barh([f"{feature_names[i]} ({i})" for i in order], scores[order])
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
