"""Generate small synthetic datasets in the DataCollector raw format.

The real experiments used human participant data that, for ethics reasons, can
never be published (thesis Section 5.5). This script fabricates a handful of
"users", each with a slightly different typing rhythm / mouse style, purely so
the pipelines can be run end to end and so the CSV layout is documented by
example. The numbers are made up - they are not real behaviour and should not
be read as results.

    python generate_demo_data.py

writes into data/demo/{keystroke,mouse,mobile}/.
"""

import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(HERE, "demo")

N_USERS = 6
KEYS = ["KeyA", "KeyN", "KeyE", "KeyO", "KeyU", "KeyH", "KeyT", "KeyS",
        "Space", "KeyI", "KeyR", "KeyL"]


def _user_style(seed):
    """A per-user random generator plus a few personal timing/motion traits."""
    rng = random.Random(seed)
    return rng, {
        "hold": rng.uniform(70, 130),        # mean key hold time (ms)
        "gap": rng.uniform(90, 220),         # mean gap between keys (ms)
        "caps_with_shift": rng.random() < 0.5,  # Shift vs CapsLock preference
        "speed": rng.uniform(0.6, 1.8),      # mouse pixels per ms
        "curve": rng.uniform(2, 18),         # how much the path bows
    }


def write_keystroke_csv(path, rng, style, n_bursts):
    """A raw keystroke CSV: header + rows of one keystroke each."""
    header = ["KEYVALUE", "KEYDOWN", "KEYUP", "KEYCODE", "CTRL", "ALT",
              "SHIFT", "CAPS"]
    rows = []
    clock = 1_000_000
    for _ in range(n_bursts):
        burst_len = rng.randint(6, 14)
        for _ in range(burst_len):
            code = rng.choice(KEYS)
            hold = max(20, int(rng.gauss(style["hold"], 15)))
            down = clock
            up = down + hold
            is_upper = code.startswith("Key") and rng.random() < 0.15
            shift = "true" if is_upper and style["caps_with_shift"] else "false"
            caps = "true" if is_upper and not style["caps_with_shift"] else "false"
            value = code[-1] if code.startswith("Key") else " "
            rows.append([value, down, up, code, "false", "false", shift, caps])
            # Next key starts after a personal within-burst gap (<1s -> same
            # segment).
            clock = down + max(30, int(rng.gauss(style["gap"], 40)))
        # Long pause between bursts so they land in separate segments.
        clock += rng.randint(1500, 4000)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def write_mouse_csv(path, rng, style, n_clicks):
    """A raw mouse CSV: header + move/down/up rows forming point-and-clicks."""
    rows = [["TYPE", "X", "Y", "TIMESTAMP"]]
    clock = 2_000_000
    x, y = rng.randint(200, 800), rng.randint(200, 600)
    for _ in range(n_clicks):
        target_x = x + rng.randint(-300, 300)
        target_y = y + rng.randint(-200, 200)
        steps = rng.randint(8, 16)
        for s in range(1, steps + 1):
            frac = s / steps
            # Straight interpolation plus a per-user sideways bow.
            bow = style["curve"] * (frac - frac * frac)
            px = int(x + (target_x - x) * frac + rng.gauss(0, 1))
            py = int(y + (target_y - y) * frac + bow + rng.gauss(0, 1))
            dt = max(8, int(30 / style["speed"] + rng.gauss(0, 4)))
            clock += dt
            rows.append([0, px, py, clock])
        # Left press then release at the target.
        clock += rng.randint(10, 60)
        rows.append([1, target_x, target_y, clock])
        clock += rng.randint(40, 150)  # click hold < 400 ms
        rows.append([2, target_x, target_y, clock])
        x, y = target_x, target_y
        clock += rng.randint(300, 1200)

    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def _mobile_user_centre(user):
    """A fixed 32-D cluster centre for a user, shared by train and test.

    Seeding on the user id (not on the split) is what makes the two splits
    describe the same people - otherwise the model would train on one set of
    clusters and be tested on unrelated ones.
    """
    rng = random.Random(f"mobile-{user}")
    return [rng.uniform(0, 1) for _ in range(32)]


def write_mobile_csv(path, users, noise_seed, n_per_user):
    """Pre-extracted mobile feature rows: 32 features + user label.

    Each user is a Gaussian blob around their fixed centre; only the sampling
    noise differs between the train and test files.
    """
    rng = random.Random(noise_seed)
    rows = []
    for user in users:
        centre = _mobile_user_centre(user)
        for _ in range(n_per_user):
            rows.append([round(c + rng.gauss(0, 0.08), 4) for c in centre]
                        + [user])
    rng.shuffle(rows)
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def main():
    for modality in ("keystroke", "mouse"):
        for split in ("train", "test"):
            os.makedirs(os.path.join(DEMO, modality, split), exist_ok=True)
    os.makedirs(os.path.join(DEMO, "mobile"), exist_ok=True)

    for u in range(N_USERS):
        user = f"user{u:02d}"
        rng, style = _user_style(seed=u)
        write_keystroke_csv(
            os.path.join(DEMO, "keystroke", "train", f"{user}_keystroke.csv"),
            rng, style, n_bursts=120)
        write_keystroke_csv(
            os.path.join(DEMO, "keystroke", "test", f"{user}_keystroke.csv"),
            rng, style, n_bursts=40)
        write_mouse_csv(
            os.path.join(DEMO, "mouse", "train", f"{user}_mouse.csv"),
            rng, style, n_clicks=200)
        write_mouse_csv(
            os.path.join(DEMO, "mouse", "test", f"{user}_mouse.csv"),
            rng, style, n_clicks=70)

    users = [f"user{u:02d}" for u in range(N_USERS)]
    write_mobile_csv(os.path.join(DEMO, "mobile", "train.csv"), users,
                     noise_seed=100, n_per_user=300)
    write_mobile_csv(os.path.join(DEMO, "mobile", "test.csv"), users,
                     noise_seed=200, n_per_user=100)

    print(f"demo data written under {DEMO}")


if __name__ == "__main__":
    main()
