# Browser user identification via behavioural biometrics

Code and tools from my PhD thesis, *Browser user privacy — identifying users
via browser interactions* (Royal Holloway, University of London, 2023).

The work asks a simple privacy question: **using only the standard APIs every
browser exposes to any web page — no permission prompt, no plugin — how well
can a website work out *which individual human* is at the keyboard?** The
answer, across keyboard, mouse and mobile touch, is: surprisingly well, and it
gets better the longer you interact.

> The behavioural data used in the thesis came from human participants and, for
> ethics reasons, can never be published. This repository contains the
> **software** — feature extraction, models, the collection tool — plus a
> synthetic data generator so everything runs end to end. The numbers below are
> from the thesis; you cannot reproduce them without your own recordings.

## The idea

When you use a web page, JavaScript on that page can listen to `KeyboardEvent`,
`MouseEvent` and (on mobile) `DeviceMotion` / `DeviceOrientation` events. These
were designed to make pages interactive, but they also expose *how* you type
and move — your rhythm and motor habits. Prior work had shown these behavioural
biometrics can **authenticate** a known user (a yes/no check, usually in a lab
with a fixed task). This thesis instead does **identification** — picking one
person out of many — from data gathered in a completely uncontrolled, everyday
browsing setting, through ordinary browser APIs. To my knowledge that
combination (identification + uncontrolled + browser-API-collected) had not
been demonstrated before.

The threat that follows: a site could build a behavioural profile of a visitor
and then recognise them later **even in private/incognito mode and while logged
out** — defeating the anonymity users think those give them (thesis
Chapter 10).

## What's here

| Folder                            | Contents                                                                 |
|-----------------------------------|--------------------------------------------------------------------------|
| [`analysis/`](analysis)           | The four identification pipelines (keystroke, mouse, fusion, mobile).    |
| [`extension/`](extension)         | The Chrome extension used to collect the data (research prototype).      |
| [`mobile-webpage/`](mobile-webpage) | A web page showing mobile sensors are readable from the browser alone.  |
| [`tools/`](tools)                 | Utility to decode the public Kim & Kang mobile dataset into CSVs.        |
| [`data/`](data)                   | Synthetic demo-data generator + tiny sample files documenting the format. |
| [`docs/`](docs)                   | [Data format reference](docs/data-format.md).                            |

## Method in one paragraph

Raw events are segmented into natural units — a *typing burst* for keystrokes,
a *point-and-click* for the mouse — and each unit is turned into a fixed feature
vector: n-graph key timings plus Shift/CapsLock habits for typing (thesis
Section 6.3.2), and 48 geometric/kinematic features (speed, curvature, angles,
overshoot, ...) for the mouse (Section 7.3.2). An **XGBoost** multi-class model
is trained per modality with inverse-frequency sample weights. At test time,
the per-sample class probabilities of consecutive same-user actions are summed
(the *accumulative* method, Eq. 6.1) — which is why accuracy climbs steadily as
the site observes more of your activity.

## Headline results (from the thesis)

Metric is macro F1 for the identification task; "uncontrolled" data was
collected from 20 participants over 4–6 weeks of ordinary browsing.

| Experiment                          | 1 sample | ~10 samples | Notes                                  |
|-------------------------------------|:--------:|:-----------:|----------------------------------------|
| Keystroke (Ch. 6, our data)         |   0.50   | 0.89 (@20)  | free text, 4-graph features            |
| Keystroke (Ch. 6, CMU DSL password) |    —     |    0.94     | public fixed-text dataset              |
| Mouse (Ch. 7, our data)             |   0.59   |    0.94     | point-and-click                        |
| Mouse (Ch. 7, Bogazici dataset)     |   0.45   |    0.95     | public dataset, browsing subset        |
| Keystroke + mouse fusion (Ch. 8)    |   0.73   |    0.95     | 5 clicks + 5 keystrokes                 |
| Mobile touch (Ch. 9, Kim & Kang)    |   0.60   |    0.96     | touch + motion sensors                  |

Takeaways: a **single** action already identifies a user far above chance;
roughly **ten** actions reach ~0.95; and fusing keystroke with mouse beats
either alone. On PC, the keyboard/mouse APIs were available in **every** browser
tested, in both normal and private mode, with no permission required
(thesis Chapter 10).

## Quick start

```bash
cd analysis
pip install -r requirements.txt
python ../data/generate_demo_data.py            # synthetic data, runs the code

python run_keystroke.py --data-dir ../data/demo/keystroke --out-dir results/keystroke
python run_mouse.py     --data-dir ../data/demo/mouse     --out-dir results/mouse
python run_fusion.py    --data-dir ../data/demo           --out-dir results/fusion
python run_mobile.py    --train ../data/demo/mobile/train.csv \
                        --test  ../data/demo/mobile/test.csv --out-dir results/mobile
```

See [`analysis/README.md`](analysis/README.md) for details and
[`docs/data-format.md`](docs/data-format.md) to bring your own data.

## Ethics

The data collection was approved by the RHUL Information Security Group ethics
process, with written informed consent from every participant (thesis
Appendices A and B). The collection tool records everything typed, including
passwords, so participants could pause it at any time by logging out. The
resulting dataset was never released. **Anyone reusing this code to collect data
must obtain their own ethics approval and informed consent.** It is shared to
support privacy research and defensive work, not tracking.

## Thesis

Zhaoyi Fan, *Browser user privacy — identifying users via browser
interactions*, PhD thesis, Royal Holloway, University of London, 2023.
<https://pure.royalholloway.ac.uk/en/publications/browser-user-privacy-identifying-users-via-browser-interactions/>

## License

[MIT](LICENSE).
