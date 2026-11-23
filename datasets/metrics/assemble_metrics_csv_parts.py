import argparse
from pathlib import Path
from typing import List


def assemble_one(base_name: str) -> None:
    """Assemble CSV parts named <base_name>_partNN.csv into a single file.

    The output file is named <base_name>_assembled.csv and is written in the
    same directory as the parts. The header row from the first part is kept,
    and headers from subsequent parts are skipped.
    """
    metrics_dir = Path(__file__).resolve().parent
    pattern = f"{base_name}_part*.csv"
    parts: List[Path] = sorted(
        metrics_dir.glob(pattern),
        key=lambda p: int(p.stem.split("part")[-1]),
    )

    if not parts:
        return

    output_path = metrics_dir / f"{base_name}_assembled.csv"

    with output_path.open("w", encoding="utf-8", newline="") as fout:
        for idx, part in enumerate(parts):
            with part.open("r", encoding="utf-8", newline="") as fin:
                for line_idx, line in enumerate(fin):
                    if idx > 0 and line_idx == 0:
                        # Skip header in subsequent parts.
                        continue
                    fout.write(line)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble metrics CSV parts named <base>_partNN.csv into a single "
            "<base>_assembled.csv file."
        )
    )
    parser.add_argument(
        "bases",
        nargs="*",
        help=(
            "Base names to assemble (without _partNN). "
            "If omitted, defaults to adr_metrics_monthly and repo_metrics_monthly."
        ),
    )
    args = parser.parse_args()

    if args.bases:
        bases = args.bases
    else:
        bases = ["adr_metrics_monthly", "repo_metrics_monthly"]

    for base in bases:
        assemble_one(base)


if __name__ == "__main__":
    main()


