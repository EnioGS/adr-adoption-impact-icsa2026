# Installation and Setup Guide

This is a small and quick step-by-step guide on how to use the script [datasets/metrics/assemble_metrics_csv_parts.py](datasets/metrics/assemble_metrics_csv_parts.py) to assemble the multiple parts of the dataset into one single file.

While it is perfectly possible to open each individual CSV file manually, it might be convenient to have all the data inside one single file.

## Assembling the Data

The assembly script uses only standard Python libraries and does not require any additional package installations.

To assemble the default metric datasets (ADR metrics and repository metrics), navigate to the `datasets/metrics/` directory and run:

**Linux/macOS:**
```bash
cd datasets/metrics/
python assemble_metrics_csv_parts.py
```

**Windows:**
```cmd
cd datasets\metrics\
python assemble_metrics_csv_parts.py
```

This will create two assembled files:
- `adr_metrics_monthly_assembled.csv`
- `repo_metrics_monthly_assembled.csv`

