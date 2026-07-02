"""Point-and-click segmentation and feature extraction (thesis Chapter 7).

Raw input: one CSV per user from the DataCollector extension, four columns
(see docs/data-format.md):

    TYPE, X, Y, TIMESTAMP

TYPE encodes the action: 0 move, 1/2 left down/up, 3/4 right down/up,
5 wheel press, 6/7 wheel up/down, 8 unexpected. TIMESTAMP is in milliseconds.

A "point-and-click" is a run of moves that ends in a left press+release. Each
one becomes a single sample described by 50 geometric / kinematic features;
two of them (see EXCLUDED_FEATURES) are dropped before training because they
depend on the device's sampling rate rather than on the user's behaviour.
"""

import csv
import math

import numpy as np

# Segment time budget: a point-and-click is not allowed to span longer than
# this (older moves are inactivity, not part of the aiming motion).
MAX_SEGMENT_MS = 3000

# A held left button longer than this is a drag, not a click - discard.
MAX_CLICK_HOLD_MS = 400

# Minimum number of move points for a usable segment.
MIN_MOVE_POINTS = 6

# Feature indices dropped before training: mean inter-point time and mean
# curved distance per point. Both track the hardware/software sampling rate,
# so they behave like a device fingerprint rather than a behavioural trait
# (thesis Section 7.3.5). Names: 'time_per_point', 'scurl_per_point'.
EXCLUDED_FEATURES = [2, 5]

FEATURE_NAMES = [
    "points", "click_gap", "scurl_per_point", "backward_count",
    "time", "time_per_point", "scurl_over_sstrai", "width_max", "width_min",
    "width_mean", "width_std", "v_straight", "v_curl",
    "acc_mean", "acc_std", "angle_mean", "angle_std",
    "area_over_sstrai", "area_over_scurl", "click_duration", "click_distance",
    "scurl", "sstrai", "acc_max", "acc_min",
    "angle_min", "angle_max",
    "acc_pp_mean", "acc_pp_std", "acc_pp_min", "acc_pp_max",
    "vcorr_pp_mean", "vcorr_pp_std", "vcorr_pp_min", "vcorr_pp_max",
    "acorr_pp_mean", "acorr_pp_std", "acorr_pp_min", "acorr_pp_max",
    "v_seg_mean", "v_seg_std", "v_seg_min", "v_seg_max",
    "width_over_sstrai", "width_over_scurl", "width_over_time",
    "backward_relative", "backward_both",
    "sin", "cos",
]


def _distance(p, q):
    return math.hypot(p[1] - q[1], p[2] - q[2])


def load_events(csv_path):
    """Read the raw mouse CSV as integer [type, x, y, timestamp] rows."""
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    events = []
    for row in rows:
        if row[0] == "TYPE":
            continue
        events.append([int(v) for v in row])
    return events


def point_and_click_segments(events):
    """Split the event stream into move-then-left-click segments.

    We walk the stream keeping a running buffer of every move/left-down/left-up
    event. A left-up (type 2) closes the buffer: if exactly one left-down has
    occurred since the last close, the buffer is a clean "moves then a single
    click" and is emitted as a segment; otherwise (no press, or several presses
    with no release) it is discarded. Either way the buffer resets afterwards.
    """
    segments = []
    buffer = []
    press_count = 0
    for event in events:
        action = event[0]
        if action not in (0, 1, 2):
            continue
        buffer.append(event)
        if action == 1:  # left button pressed
            press_count += 1
        elif action == 2:  # left button released
            if press_count == 1:
                segments.append(buffer)
            buffer = []
            press_count = 0
    return segments


def _collapse_stationary(points):
    """Merge consecutive points at the same coordinate into one.

    When the pointer pauses, several events share an (x, y); we keep the first
    and set its timestamp to the average of the run, so a pause becomes a
    single point rather than inflating the point count.
    """
    collapsed = [points[0]]
    j = 1
    while j < len(points):
        if _distance(collapsed[-1], points[j]) != 0:
            collapsed.append(points[j])
            j += 1
            continue
        # Look ahead for the next point that actually moves.
        k = j
        while k < len(points) and _distance(collapsed[-1], points[k]) == 0:
            k += 1
        last_same = min(k, len(points)) - 1
        merged_ts = (collapsed[-1][3] + points[last_same][3]) / 2
        collapsed[-1] = [collapsed[-1][0], collapsed[-1][1],
                         collapsed[-1][2], merged_ts]
        j = k
    return collapsed


def _trim_by_iqr(points, iqr_ratio):
    """Cut the move path at the first over-long inter-point gap.

    Walking backwards from the click, the time gaps between points describe
    smooth motion, brief pauses or direction changes. A gap far above the
    others marks the boundary of the deliberate aiming motion, so we drop
    everything before it. The threshold is `up = Q3 + 1.5*IQR` of the gaps,
    scaled by iqr_ratio (the thesis uses 3; see Table 7.2). Very fine-grained
    captures (up < 100 ms) use a fixed 2x scale instead, matching the original
    experiments.
    """
    gaps = [points[j + 1][3] - points[j][3] for j in range(len(points) - 1)]
    if not gaps:
        return points
    q3, q1 = np.percentile(gaps, 75), np.percentile(gaps, 25)
    up = 2.5 * q3 - 1.5 * q1  # == Q3 + 1.5 * IQR

    scale = iqr_ratio
    if iqr_ratio >= 3 and up >= 100:
        scale = 2

    ordered = points[::-1]  # newest (the click) first
    for j in range(len(ordered) - 1):
        gap = ordered[j][3] - ordered[j + 1][3]
        if gap > up * scale or gap < 0:
            return ordered[: j + 1][::-1]
        if ordered[0][3] - ordered[j][3] > 2000:
            return ordered[:j][::-1]
    return points


def _signed_offset(point, start, end):
    """Signed perpendicular distance from `point` to the start->end line.

    Positive/negative sides let us measure how far the path bows away from the
    straight line between the first and last move point ("width" in Eq. 7.17).
    """
    (_, xs, ys, _), (_, xe, ye, _) = start, end
    _, x0, y0, _ = point
    base = math.hypot(xs - xe, ys - ye)
    return ((x0 - xs) * (ys - ye) - (xs - xe) * (y0 - ys)) / base


def _angle_between(v1, v2):
    """Angle (radians) between two 2D vectors, via the dot-product formula."""
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    norms = math.sqrt((v1[0] ** 2 + v1[1] ** 2) * (v2[0] ** 2 + v2[1] ** 2))
    return math.acos(dot / norms)


def _correlation(angle, change):
    """Angle-vs-(speed|acceleration) change coupling from Eq. 7.31 / 7.36.

    Combines a turn angle with a speed or acceleration change, keeping the
    sign of each so that "turned sharply while also speeding up" scores
    differently from "turned sharply while slowing down".
    """
    if angle != 0 and change != 0:
        a_term = 1 if angle > 0 else -1
        c_term = 1 if change > 0 else -1
        return (angle + a_term) * change + (change + c_term) * angle
    if angle == 0:
        return change
    return angle


def _segment_features(points, click_down, click_up):
    """Compute the 50-value feature vector for one cleaned move path.

    `points` are the move points (already collapsed and trimmed), ordered from
    first to last; `click_down`/`click_up` are the left button press/release
    events. Returns None when the segment is degenerate (zero-length path,
    drag instead of click, too few points).
    """
    click_duration = click_up[3] - click_down[3]
    click_distance = _distance(click_up, click_down)
    if click_duration > MAX_CLICK_HOLD_MS:
        return None

    # Keep the path only up to the point furthest from the start: the return
    # travel after overshooting the target is not part of the aiming motion.
    start = points[0]
    offsets_from_start = [_distance(p, start) for p in points]
    points = points[: int(np.argmax(offsets_from_start)) + 1]
    if len(points) < MIN_MOVE_POINTS:
        return None

    first, last = points[0], points[-1]
    sstrai = _distance(first, last)  # straight-line start->end distance
    if sstrai == 0:  # closed loop, no net displacement -> unusable
        return None

    dx, dy = last[1] - first[1], last[2] - first[2]
    sin_dir = round(dx / sstrai, 8)
    cos_dir = round(dy / sstrai, 8)

    # Walk the path accumulating per-point speed, acceleration, turn angles,
    # signed offsets to the main line, and the swept area.
    offsets = [0.0]            # signed distance to the start->end line
    seg_speeds = []            # speed on each move step
    accelerations = []         # d(speed)/dt on each step
    turn_angles = []           # angle at each interior point (Eq. 7.12)
    swept_area = 0.0           # area between path and its projection
    curved_length = 0.0        # sum of step distances (Eq. 7.6)
    backward_relative = 0      # turns sharper than 90 deg (Eq. 7.41)
    backward_count = 0         # sign flips of projection on the main line
    backward_both = 0          # points that are both of the above
    heading_forward = True
    prev_speed = 0.0
    prev_offset = 0.0

    for a in range(len(points)):
        offset = _signed_offset(points[a], first, last)
        if a == 0:
            offsets.append(0.0)
            prev_offset = 0.0
            swept_area += 0.0
            continue

        prev, cur = points[a - 1], points[a]
        dt = cur[3] - prev[3]
        step = _distance(cur, prev)
        speed = step / dt
        seg_speeds.append(speed)
        accelerations.append((speed - prev_speed) / dt)
        prev_speed = speed
        curved_length += step

        # Trapezoidal slice of the area swept between the path and the main
        # line: average of the two signed offsets times the along-line step.
        along = math.sqrt(abs(_distance(cur, first) ** 2 - offset ** 2))
        prev_along = math.sqrt(abs(_distance(prev, first) ** 2 - prev_offset ** 2))
        swept_area += abs((prev_offset + offset) * (along - prev_along) / 2)
        offsets.append(offset)
        prev_offset = offset

        # Turn angle at this interior point and the two "backward" flags.
        if a < len(points) - 1:
            nxt = points[a + 1]
            incoming = (prev[1] - cur[1], prev[2] - cur[2])
            outgoing = (cur[1] - nxt[1], cur[2] - nxt[2])
            turn = _angle_between(incoming, outgoing)
            turn_angles.append(turn)
            if turn / math.pi > 0.5:
                backward_relative += 1

            forward_vec = (nxt[1] - cur[1], nxt[2] - cur[2])
            main_vec = (last[1] - first[1], last[2] - first[2])
            angle_to_main = _angle_between(forward_vec, main_vec)
            # Count each time the motion flips between advancing along the
            # main line and retreating against it (Eq. 7.42).
            if heading_forward and angle_to_main / math.pi > 0.5:
                backward_count += 1
                if turn / math.pi > 0.5:
                    backward_both += 1
                heading_forward = False
            elif not heading_forward and angle_to_main / math.pi < 0.5:
                backward_count += 1
                if turn / math.pi > 0.5:
                    backward_both += 1
                heading_forward = True

    total_time = last[3] - first[3]
    interior_offsets = offsets[1:]
    width_max, width_min = max(interior_offsets), min(interior_offsets)

    # Per-point speed differences (Eq. 7.26) and their coupling with turn
    # angle (Eq. 7.31 / 7.36).
    speed_changes = np.diff(seg_speeds).tolist()
    vcorr, acorr = [], []
    for j in range(len(speed_changes)):
        angle = turn_angles[j]
        vcorr.append(_correlation(angle, speed_changes[j]))
        acorr.append(_correlation(angle, accelerations[j + 1] - accelerations[j]))

    def stats(values):
        arr = np.array(values, dtype=float)
        return arr.mean(), arr.std(ddof=1), arr.min(), arr.max()

    acc_mean, acc_std, acc_min, acc_max = stats(accelerations)
    angle_mean, angle_std, angle_min, angle_max = stats(turn_angles)
    accpp_mean, accpp_std, accpp_min, accpp_max = stats(speed_changes)
    vcorr_mean, vcorr_std, vcorr_min, vcorr_max = stats(vcorr)
    acorr_mean, acorr_std, acorr_min, acorr_max = stats(acorr)
    vseg_mean, vseg_std, vseg_min, vseg_max = stats(seg_speeds)
    width_mean = float(np.mean(interior_offsets))
    width_std = float(np.std(interior_offsets, ddof=1))
    width_span = width_max - width_min if width_min < 0 else width_max

    n_points = len(points)
    return [
        n_points,
        click_down[3] - last[3],                 # gap: click after last move
        curved_length / (n_points - 1),           # scurl_per_point (excluded)
        backward_count,
        total_time,
        total_time / (n_points - 1),               # time_per_point (excluded)
        curved_length / sstrai,
        width_max, width_min, width_mean, width_std,
        sstrai / total_time,                        # straight-line speed
        curved_length / total_time,                 # curved-path speed
        acc_mean, acc_std, angle_mean, angle_std,
        swept_area / sstrai, swept_area / curved_length,
        click_duration, click_distance,
        curved_length, sstrai, acc_max, acc_min,
        angle_min, angle_max,
        accpp_mean, accpp_std, accpp_min, accpp_max,
        vcorr_mean, vcorr_std, vcorr_min, vcorr_max,
        acorr_mean, acorr_std, acorr_min, acorr_max,
        vseg_mean, vseg_std, vseg_min, vseg_max,
        width_span / sstrai, width_span / curved_length, width_span / total_time,
        backward_relative, backward_both,
        sin_dir, cos_dir,
    ]


def extract_user_samples(csv_path, iqr_ratio=3):
    """Full pipeline for one user's raw mouse CSV -> list of feature vectors."""
    events = load_events(csv_path)
    samples = []
    for segment in point_and_click_segments(events):
        # A segment is [moves..., left_down, left_up]. Everything up to the
        # button press is the aiming motion.
        press_idx = next((i for i, e in enumerate(segment) if e[0] == 1), None)
        if press_idx is None or segment[-1][0] != 2:
            continue
        moves = segment[:press_idx]
        click_down, click_up = segment[press_idx], segment[-1]
        if len(moves) < MIN_MOVE_POINTS:
            continue

        moves = _collapse_stationary(moves)
        if len(moves) < MIN_MOVE_POINTS:
            continue
        moves = _trim_by_iqr(moves, iqr_ratio)
        if len(moves) < MIN_MOVE_POINTS:
            continue

        try:
            features = _segment_features(moves, click_down, click_up)
        except (ValueError, ZeroDivisionError):
            continue
        if features is not None:
            samples.append(features)
    return samples
