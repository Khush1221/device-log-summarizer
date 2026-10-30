# PROMPT_LOG.md - AI Usage Log

## How I used AI

- **Section 1 (sanitizer):** Written by me without AI. After writing it, I ran the unit tests
  to check it.
- **Section 2 (CSV summarizer CLI):** Built with help from an AI assistant (Claude). I asked it
  to create the CLI from the assessment PDF, then reviewed the code, ran it on the sample data,
  on a CSV with bad rows, and with a missing file, and read the design decisions in the README
  so I can explain them.
- **Section 3 (chart):** AI-generated script, reviewed and fixed (details below).

## 1. Initial prompt

My request to the AI was to analyze all the details from the PDF (the Device Log
Summarizer: sanitizer, CSV summarizer with JSON export, and a matplotlib chart script
reading `output/summary.json`), including a README and tests and explain it .

For the chart specifically, the intended request was:

> Write a Python script that loads `output/summary.json` (structure:
> `{"devices": [{"device_id": ..., "avg_temperature": ...}]}`) and creates a bar chart
> comparing average temperature per device using matplotlib.

## 2. Bug in the AI's first attempt

The first draft of the chart script ended with `plt.bar(...)` and `plt.show()`. When run in a
terminal it produced no image file, and the chart had no title and no axis labels, so the
script was unusable as a deliverable. In the final script the bars also show 1-decimal labels
at first, where DEV_D read `80.0` while its real average is `79.99`, which looked like it hit
the threshold; I changed the labels to 2 decimals to match the terminal table.

## 3. Fix

The fix was to use the headless `Agg` backend, save the figure with
`savefig("output/temperature_chart.png", dpi=150)`, and add a title, axis labels with units,
value labels on the bars, a threshold line, `tight_layout()`, and a clear error message when
the JSON file is missing or empty.
