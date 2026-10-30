# Device Log Summarizer

A small, dependency-light Python CLI that reads device telemetry from a CSV, aggregates it
per device, filters out devices that run too hot, exports clean JSON, and plots a chart.

- **Python 3.9+**, standard library only for the CLI (`csv`, `json`, `argparse`)
- `matplotlib` is needed only for the chart
- 13 unit tests, no extra test dependencies (`unittest`)

> **Note on data:** No input file was provided with the assignment, so `data/device_telemetry.csv`
> is **synthetic sample data** I created (6 devices, 72 rows) to build and test the tool.
> `data/device_telemetry_dirty.csv` is a small made-up file with deliberately bad rows to show
> error handling. To use real data, replace `data/device_telemetry.csv` (same columns:
> `device_id`, `status`, `temperature`) and rerun the two commands under Usage.

## Project structure

```
device-log-summarizer/
├── sanitize.py                  # Section 1: clean_sensor_readings()
├── summarizer.py                # Section 2: CLI (read -> aggregate -> filter -> export)
├── plot_chart.py                # Section 3: bar chart from the JSON output
├── data/
│   ├── device_telemetry.csv         # synthetic sample input (72 rows, 6 devices)
│   └── device_telemetry_dirty.csv   # synthetic file with bad rows, to show robustness
├── output/
│   ├── summary.json                 # sample output
│   └── temperature_chart.png        # sample chart
├── tests/                       # unit tests
├── PROMPT_LOG.md                # how AI was used
└── requirements.txt
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
# 1. Summarize (defaults: data/device_telemetry.csv -> output/summary.json)
python summarizer.py
python summarizer.py path/to/file.csv -o out.json --threshold 75 --verbose

# 2. Plot
python plot_chart.py                      # output/summary.json -> output/temperature_chart.png

# 3. Tests
python -m unittest discover -s tests -v
```

| Option | Meaning |
|---|---|
| `input` | CSV path (default `data/device_telemetry.csv`) |
| `-o, --output` | JSON output path (default `output/summary.json`) |
| `-t, --threshold` | Exclude devices with average temp **above** this (default `80.0`) |
| `-v, --verbose` | List every skipped row with its line number and reason |

## Sample output (from the synthetic data)

```
Device Summary (avg temperature <= 80 C)
+--------+---------+--------------+--------+
| Device | Records | Avg Temp (C) | Errors |
+--------+---------+--------------+--------+
| DEV_A  |      12 |        60.53 |      3 |
| DEV_B  |      12 |        69.75 |      2 |
| DEV_C  |      12 |        54.08 |      1 |
| DEV_D  |      12 |        79.99 |      2 |
| DEV_F  |      12 |        45.07 |      1 |
+--------+---------+--------------+--------+

Rows read: 72 | skipped: 0 | devices kept: 5 | excluded (too hot): 1
  excluded DEV_E: avg 86.41 C
```

![chart](output/temperature_chart.png)

## Section 1 - `clean_sensor_readings`

Takes a list of mixed values and returns a list of floats: values that cannot be converted,
`None`, and negative numbers are dropped, and anything above 500.0 is capped at 500.0.
Empty or fully invalid input returns an empty list instead of raising an error.

## Section 2 - Design decisions

- **Bad rows never crash the run.** A row is skipped (and reported) if `device_id` is blank,
  `status` is not ACTIVE/WARNING/ERROR, or `temperature` is not a finite number.
  Whitespace and status case are normalized (`" error "` -> `ERROR`).
- **Fatal problems give a clear message and exit code 1:** missing file, empty file, missing
  columns, undecodable file, no valid rows, unwritable output.
- **Threshold:** devices are removed only when the average is strictly **above** 80.0; exactly
  80.0 is kept (covered by a test).
- **Negative temperatures are kept** in Section 2 - the spec only treats negatives as error
  flags in Section 1, and real temperatures can be below zero.
- **Averages** are rounded to 2 decimals. Device IDs are case-sensitive (`DEV_a` != `DEV_A`).
- The JSON includes metadata (threshold, rows read/skipped) and an `excluded_devices` list so
  the filtering is auditable.

## Section 3 - Chart

`plot_chart.py` uses the headless `Agg` backend so it works on servers and CI. It adds a title,
axis labels with units, value labels, a dashed threshold line, and y-axis headroom, and rotates
tick labels when there are many devices. See `PROMPT_LOG.md` for the AI workflow and the bugs I fixed.

## Possible improvements

Streaming for very large files (the current version holds records in memory), a `--format csv`
export, and case-insensitive device ID matching if the data source requires it.
