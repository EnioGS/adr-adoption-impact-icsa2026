import argparse
from pathlib import Path


MAX_MB_DEFAULT = 10


def split_csv_by_size(input_path: Path, max_mb: int = MAX_MB_DEFAULT) -> None:
    """Split a CSV file into chunks of approximately max_mb megabytes.

    Each output file:
    - Is placed next to the input file.
    - Has the same header row as the original file.
    - Is named <stem>_partNN<suffix>, e.g., adr_metrics_monthly_part01.csv.
    """
    max_bytes = max_mb * 1024 * 1024
    input_path = input_path.resolve()
    parent = input_path.parent

    with input_path.open("r", encoding="utf-8", newline="") as fin:
        header = fin.readline()
        if not header:
            return

        part_idx = 1
        out = None
        bytes_in_part = 0

        def open_new_part(index: int):
            nonlocal out, bytes_in_part
            if out is not None:
                out.close()
            suffix = input_path.suffix
            stem = input_path.stem
            out_name = f"{stem}_part{index:02d}{suffix}"
            out_path = parent / out_name
            out = out_path.open("w", encoding="utf-8", newline="")
            out.write(header)
            bytes_in_part = len(header.encode("utf-8"))
            return out

        out = open_new_part(part_idx)

        for line in fin:
            line_bytes = len(line.encode("utf-8"))
            if bytes_in_part + line_bytes > max_bytes and bytes_in_part > len(
                header.encode("utf-8")
            ):
                part_idx += 1
                out = open_new_part(part_idx)
            out.write(line)
            bytes_in_part += line_bytes

        if out is not None:
            out.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split large metrics CSV files into ~10MB chunks."
    )
    parser.add_argument(
        "--max-mb",
        type=int,
        default=MAX_MB_DEFAULT,
        help="Target maximum size per chunk in megabytes (default: 10).",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="CSV files to split. If omitted, splits the two main metrics CSVs.",
    )
    args = parser.parse_args()

    if args.files:
        targets = [Path(p) for p in args.files]
    else:
        repo_root = Path(__file__).resolve().parents[3]
        metrics_dir = repo_root / "supplementary_material" / "datasets" / "metrics"
        targets = [
            metrics_dir / "adr_metrics_monthly.csv",
            metrics_dir / "repo_metrics_monthly.csv",
        ]

    for path in targets:
        if not path.exists():
            continue
        split_csv_by_size(path, max_mb=args.max_mb)


if __name__ == "__main__":
    main()


