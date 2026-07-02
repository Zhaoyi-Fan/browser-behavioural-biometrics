"""Convert the Kim and Kang mobile keystroke dataset into feature CSVs.

The mobile experiment (thesis Chapter 9) uses the public dataset from:

    H. Kim and J. Kang, "Two-factor authentication with mobile keystroke
    dynamics" (2020).

The dataset ships as NumPy .npy files - data files paired with separate label
files - where each user's samples are zero-padded to a fixed length. This
script pairs each data file with its label file, drops the all-zero padding
rows, appends the user label as the last column, and writes one CSV per pair
plus a combined CSV. The output is exactly the format run_mobile.py expects.

The dataset is not redistributed here; download it from the authors and point
--src at the folder of .npy files.

    python decode_kim_kang_dataset.py --src path/to/npy --out path/to/csv
"""

import argparse
import os

import numpy as np
import pandas as pd

# Which data .npy pairs with which label .npy, by file index. This mapping was
# recovered by matching row counts between the data and label files (the
# dataset does not document it explicitly).
DATA_LABEL_PAIRS = [(1, 7), (2, 8), (3, 5), (4, 6)]


def is_padding(row):
    """A padding row is entirely zeros (all users are padded to one length)."""
    return np.unique(row)[0] == 0 and len(np.unique(row)) == 1


def decode_pair(src_dir, data_index, label_index):
    """Load one data/label pair and return real (non-padding) labelled rows."""
    data = np.load(os.path.join(src_dir, f"mmc{data_index}.npy"),
                   allow_pickle=True).astype(float)
    labels = np.load(os.path.join(src_dir, f"mmc{label_index}.npy"),
                     allow_pickle=True).astype(int)

    rows = []
    for user_samples, user_label in zip(data, labels):
        for sample in user_samples:
            if not is_padding(sample):
                rows.append(sample.tolist() + [user_label[0]])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, help="folder of .npy files")
    parser.add_argument("--out", required=True, help="folder for CSV output")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    combined = []
    for data_index, label_index in DATA_LABEL_PAIRS:
        rows = decode_pair(args.src, data_index, label_index)
        combined.extend(rows)
        out_path = os.path.join(args.out, f"mmc{data_index}{label_index}.csv")
        pd.DataFrame(rows).to_csv(out_path, header=False, index=False)
        print(f"{out_path}: {len(rows)} samples")

    all_path = os.path.join(args.out, "mmc_all.csv")
    pd.DataFrame(combined).to_csv(all_path, header=False, index=False)
    print(f"{all_path}: {len(combined)} samples total")


if __name__ == "__main__":
    main()
