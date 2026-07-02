# Data formats

The analysis scripts read plain CSV files. Two formats come straight from the
[DataCollector extension](../extension) (raw keystroke and raw mouse events);
the mobile format is a table of pre-extracted feature vectors.

Tiny examples live in [`data/samples/`](../data/samples). A larger synthetic
dataset can be generated with `python data/generate_demo_data.py` - it writes
the exact folder layout the `run_*` scripts expect. **All of this is
synthetic**: the human participant data from the thesis can never be published
for ethics reasons (thesis Section 5.5).

## Folder layout expected by the scripts

```
data/demo/
├── keystroke/
│   ├── train/  user00_keystroke.csv, user01_keystroke.csv, ...
│   └── test/   user00_keystroke.csv, ...
├── mouse/
│   ├── train/  user00_mouse.csv, ...
│   └── test/   user00_mouse.csv, ...
└── mobile/
    ├── train.csv
    └── test.csv
```

The label for each user is taken from the filename prefix before the first
underscore (`user03_keystroke.csv` -> `user03`). The train/test split follows
the thesis: the first ~80% of each user's recording is used for training and
the last ~20% for testing, kept in chronological order so the accumulative
evaluation reflects a real, continuous session.

## Raw keystroke CSV

One row per keystroke, with a header row. Columns (thesis Table 6.1):

| Column   | Meaning                                                             |
|----------|--------------------------------------------------------------------|
| KEYVALUE | the character produced (`a`, `A`, ` `, ...)                        |
| KEYDOWN  | timestamp when the key went down, in milliseconds                  |
| KEYUP    | timestamp when the key was released, in milliseconds               |
| KEYCODE  | physical key, browser `event.code` (`KeyA`, `Space`, `ShiftLeft`) |
| CTRL     | `"true"` / `"false"` - was Ctrl held                              |
| ALT      | `"true"` / `"false"` - was Alt held                              |
| SHIFT    | `"true"` / `"false"` - was Shift held                            |
| CAPS     | `"true"` / `"false"` / `"nal"` (non-letter key)                  |

Only KEYCODE, KEYDOWN, KEYUP, SHIFT and CAPS are used by the analysis.

```
KEYVALUE,KEYDOWN,KEYUP,KEYCODE,CTRL,ALT,SHIFT,CAPS
U,1000000,1000134,KeyU,false,false,false,false
O,1000180,1000288,KeyO,false,false,false,false
I,1000367,1000501,KeyI,false,false,false,false
```

## Raw mouse CSV

One row per mouse event, with a header row. Columns (thesis Table 7.1):

| Column    | Meaning                                            |
|-----------|----------------------------------------------------|
| TYPE      | action type (see below)                            |
| X         | pointer X coordinate                               |
| Y         | pointer Y coordinate                               |
| TIMESTAMP | event time in milliseconds                         |

`TYPE` values: `0` move, `1`/`2` left down/up, `3`/`4` right down/up,
`5` wheel press, `6`/`7` wheel up/down, `8` unexpected. The analysis uses only
the point-and-click actions (`0`, `1`, `2`).

```
TYPE,X,Y,TIMESTAMP
0,509,299,2000025
0,525,310,2000060
1,657,408,2000420
2,657,408,2000480
```

## Mobile feature CSV

Already-extracted feature vectors, **no header**: 32 feature columns followed
by the user label in the last column (thesis Section 9.2.1 - timing, key
values, touch coordinates and motion-sensor readings per digraph). This is the
format produced by [`tools/decode_kim_kang_dataset.py`](../tools/decode_kim_kang_dataset.py).

```
0.8801,0.6846,1.0209, ... ,0.4021,user00
0.9401,0.6863,0.8777, ... ,0.3394,user00
```
