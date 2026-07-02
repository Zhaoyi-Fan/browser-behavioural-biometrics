"""Keystroke segmentation and n-graph feature extraction (thesis Chapter 6).

Raw input: one CSV per user, produced by the DataCollector extension. Columns
(see docs/data-format.md):

    KEYVALUE, KEYDOWN, KEYUP, KEYCODE, CTRL, ALT, SHIFT, CAPS

KEYDOWN/KEYUP are millisecond timestamps; KEYCODE is the physical key
("KeyA", "Space", ...); the last four columns record modifier state as the
strings "true"/"false" ("nal" in CAPS for non-letter keys).
"""

import csv
from itertools import combinations

# A keystroke whose down->down gap to the previous one is below this belongs
# to the same typing burst. Araujo et al. found >98% of latencies between
# consecutive keys are under one second (thesis Section 6.3.1).
SEGMENT_GAP_MS = 1000

# Keys held longer than this are treated as noise (stuck keys, long-press
# repeats) and end the current segment.
MAX_HOLD_MS = 10000

# Navigation keys interrupt the typing rhythm and media keys only exist on
# some keyboards - they say more about the device than about the user
# (thesis Section 6.2), so they are filtered out.
IGNORED_KEYS = ("ArrowRight", "ArrowLeft", "ArrowDown", "ArrowUp", "keycode")

# Raw CSV column positions.
COL_DOWN, COL_UP, COL_CODE, COL_SHIFT, COL_CAPS = 1, 2, 3, 6, 7


def load_raw_keystrokes(csv_path):
    """Read a raw keystroke CSV, skipping the header row."""
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return rows[1:]


def is_valid_keystroke(row):
    """Keep a keystroke only if its timing is sane and the key is usable."""
    hold = int(row[COL_UP]) - int(row[COL_DOWN])
    if hold <= 0 or hold >= MAX_HOLD_MS:
        return False
    code = row[COL_CODE]
    if code == "" or code in IGNORED_KEYS or "Volume" in code:
        return False
    return True


def split_into_segments(rows):
    """Group keystrokes into typing bursts.

    Consecutive valid keystrokes stay in one segment while their down->down
    gap is under SEGMENT_GAP_MS; a longer pause closes the segment. Note that
    the closing keystroke starts the next segment (an invalid keystroke is
    simply skipped without closing anything) - this mirrors the behaviour of
    the original thesis code so that extracted samples match the published
    experiments.
    """
    segments = []
    current = []
    for row in rows:
        if not current:
            current.append(row)
            continue
        if not is_valid_keystroke(row):
            continue
        gap = int(row[COL_DOWN]) - int(current[-1][COL_DOWN])
        if gap < SEGMENT_GAP_MS:
            current.append(row)
        else:
            segments.append(current)
            current = [row]
    return segments


def flag(value):
    """Modifier columns hold the strings 'true'/'false'/'nal' -> 1/0."""
    return 1 if value == "true" else 0


def ngraph_features(segment, n=4):
    """Slide an n-keystroke window over one segment and build feature rows.

    Each window (an "n-graph") yields, for n=4, 36 features
    (thesis Section 6.3.2):

      - n hold times          (key down -> same key up)
      - C(n,2) DD times       (down -> down, every ordered pair)
      - C(n,2) UU times       (up -> up)
      - C(n,2) DU times       (down -> up)
      - C(n,2) UD times       (up -> down; can be negative when keys overlap)
      - n CapsLock flags + n Shift flags
        (how a user produces capitals turned out to be one of the most
        discriminative features, thesis Fig. 6.5)

    Windows whose keydown timestamps are not strictly increasing (clock
    hiccups in the raw data) are skipped.
    """
    features = []
    pairs = list(combinations(range(n), 2))
    for start in range(len(segment) - n + 1):
        window = segment[start : start + n]
        downs = [int(k[COL_DOWN]) for k in window]
        ups = [int(k[COL_UP]) for k in window]
        if any(downs[j + 1] - downs[j] <= 0 for j in range(n - 1)):
            continue

        holds = [ups[j] - downs[j] for j in range(n)]
        dd = [downs[b] - downs[a] for a, b in pairs]
        uu = [ups[b] - ups[a] for a, b in pairs]
        du = [ups[b] - downs[a] for a, b in pairs]
        ud = [downs[b] - ups[a] for a, b in pairs]
        caps = [flag(k[COL_CAPS]) for k in window]
        shifts = [flag(k[COL_SHIFT]) for k in window]

        features.append(holds + dd + uu + du + ud + caps + shifts)
    return features


def feature_names(n=4):
    """Column names matching the ngraph_features() layout."""
    pairs = list(combinations(range(n), 2))
    names = [f"hold_{j}" for j in range(n)]
    for kind in ("dd", "uu", "du", "ud"):
        names += [f"{kind}_{a}{b}" for a, b in pairs]
    names += [f"caps_{j}" for j in range(n)]
    names += [f"shift_{j}" for j in range(n)]
    return names


def extract_user_samples(csv_path, n=4):
    """Full pipeline for one user's raw CSV: load -> segment -> n-graphs."""
    segments = split_into_segments(load_raw_keystrokes(csv_path))
    samples = []
    for segment in segments:
        samples.extend(ngraph_features(segment, n))
    return samples
