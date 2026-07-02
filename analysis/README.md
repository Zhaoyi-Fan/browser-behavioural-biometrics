# Analysis pipelines

Four self-contained experiments, one per thesis chapter. Each loads CSV data,
trains an XGBoost identifier, and reports how accuracy grows as more
consecutive actions are observed (the *accumulative* method).

| Script             | Thesis chapter | What it identifies from            |
|--------------------|----------------|------------------------------------|
| `run_keystroke.py` | 6              | free-text typing rhythm (4-graphs) |
| `run_mouse.py`     | 7              | point-and-click mouse motion       |
| `run_fusion.py`    | 8              | keystroke + mouse, late-fused      |
| `run_mobile.py`    | 9              | mobile touch + motion sensors      |

Shared code:

- `common.py` - sample weighting, the accumulative evaluation (thesis
  Eq. 6.1), and the standard figures/reports.
- `keystroke_features.py` - segmentation and 4-graph feature extraction.
- `mouse_features.py` - point-and-click segmentation, noise cleaning and the
  50 geometric/kinematic features.

## Setup

```bash
pip install -r requirements.txt
```

XGBoost runs on CPU by default (`tree_method="hist"` in `common.py`). The
thesis ran on GPU; if you have one, pass `device="cuda"` to the classifiers.

## Run it on the synthetic demo data

```bash
python ../data/generate_demo_data.py          # writes ../data/demo/

python run_keystroke.py --data-dir ../data/demo/keystroke --out-dir results/keystroke
python run_mouse.py     --data-dir ../data/demo/mouse     --out-dir results/mouse
python run_fusion.py    --data-dir ../data/demo           --out-dir results/fusion
python run_mobile.py    --train ../data/demo/mobile/train.csv \
                        --test  ../data/demo/mobile/test.csv \
                        --out-dir results/mobile
```

The demo data is random and only exercises the code end to end - its numbers
are meaningless. To reproduce the thesis results you need real behavioural
recordings in the [documented format](../docs/data-format.md); the human data
used in the thesis cannot be shared (ethics, thesis Section 5.5).

## Outputs

Each run writes to its `--out-dir`:

- `*_scores_by_window.csv` and `.png` - the four metrics against the number of
  accumulated samples (thesis Tables 6.8 / 7.8 / 9.3).
- `*_confusion_<n>_samples.png` - confusion matrices at 1, 5, 10, ... samples.
- `*_feature_importance.png` - XGBoost gain per feature.

## Reproducing the tuned models

Hyper-parameters are the tuned values from the thesis (Tables 6.5, 7.4, 8.1,
9.1), set as `TUNED_PARAMS` at the top of each `run_*` script. The original
grid search over `learning_rate x n_estimators x max_depth x min_child_weight`
is not re-run here; change `TUNED_PARAMS` if you want to re-tune.
