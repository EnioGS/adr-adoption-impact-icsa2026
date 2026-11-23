import csv
import sqlite3
from pathlib import Path
from typing import Iterable, Sequence


def _get_repo_root() -> Path:
    """Return the repository root assuming this file lives under
    supplementary_material/scripts/adr_processing/.
    """
    return Path(__file__).resolve().parents[3]


def _stream_table_rows(
    conn: sqlite3.Connection, table_name: str
) -> Iterable[Sequence]:
    """Yield rows for a given table without loading everything into memory."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    while True:
        rows = cursor.fetchmany(1000)
        if not rows:
            break
        for row in rows:
            yield row


def _export_table_to_csv(
    conn: sqlite3.Connection, table_name: str, output_path: Path
) -> None:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [row[1] for row in cursor.fetchall()]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)

        for row in _stream_table_rows(conn, table_name):
            writer.writerow(row)


def export_metrics_datasets(include_long: bool = False) -> None:
    """Export ADR- and repository-level monthly metric tables to CSV.

    By default, this writes:
    - supplementary_material/datasets/metrics/adr_metrics_monthly.csv
    - supplementary_material/datasets/metrics/repo_metrics_monthly.csv

    If include_long is True, it also exports the long-format metrics table as:
    - supplementary_material/datasets/metrics/metrics_long.csv
    """
    repo_root = _get_repo_root()
    db_path = repo_root / "data" / "main_dataset.db"
    output_dir = repo_root / "supplementary_material" / "datasets" / "metrics"

    conn = sqlite3.connect(db_path)
    try:
        _export_table_to_csv(
            conn,
            "adr_metrics",
            output_dir / "adr_metrics_monthly.csv",
        )
        _export_table_to_csv(
            conn,
            "repo_metrics",
            output_dir / "repo_metrics_monthly.csv",
        )

        if include_long:
            _export_table_to_csv(
                conn,
                "metrics",
                output_dir / "metrics_long.csv",
            )
    finally:
        conn.close()


if __name__ == "__main__":
    # Default: only the two wide monthly tables.
    export_metrics_datasets(include_long=False)


