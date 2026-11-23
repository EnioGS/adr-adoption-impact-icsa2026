import csv
from pathlib import Path
from typing import Optional

import sqlite3


def _get_repo_root() -> Path:
    """Return the repository root assuming this file lives under
    supplementary_material/scripts/adr_processing/.
    """
    return Path(__file__).resolve().parents[3]


def _build_status_mapping() -> dict:
    """Return mapping from raw status labels to normalized categories.

    The mapping mirrors the documentation in
    supplementary_material/docs/status_mapping/status_mapping.md.
    """
    mapping = {
        # proposed
        "proposed": "proposed",
        "draft": "proposed",
        "suggested": "proposed",
        "pending": "proposed",
        "in progress": "proposed",
        "under review": "proposed",
        "awaiting approval": "proposed",
        "undecided": "proposed",
        # accepted
        "accepted": "accepted",
        "approved": "accepted",
        "finalized": "accepted",
        "confirmed": "accepted",
        "ratified": "accepted",
        "endorsed": "accepted",
        # deprecated
        "deprecated": "deprecated",
        "obsolete": "deprecated",
        "archived": "deprecated",
        "abandoned": "deprecated",
        "retired": "deprecated",
        "phased out": "deprecated",
        # rejected
        "rejected": "rejected",
        "declined": "rejected",
        "not approved": "rejected",
        "dismissed": "rejected",
        "disapproved": "rejected",
        # superseded
        "superseded": "superseded",
        "replaced": "superseded",
        "updated": "superseded",
        "overridden": "superseded",
        "substituted": "superseded",
        # implemented
        "implemented": "implemented",
        "executed": "implemented",
        "deployed": "implemented",
        "realized": "implemented",
        "put into practice": "implemented",
        # under revision
        "under revision": "under revision",
        "being updated": "under revision",
        "modifying": "under revision",
        "revising": "under revision",
        "amending": "under revision",
        # withdrawn
        "withdrawn": "withdrawn",
        "retracted": "withdrawn",
        "pulled back": "withdrawn",
        "rescinded": "withdrawn",
        "revoked": "withdrawn",
    }
    return mapping


def normalize_status(raw: Optional[str], mapping: dict) -> Optional[str]:
    """Normalize a raw ADR status label to one of the predefined categories.

    Returns None if the label is empty or no mapping exists.
    """
    if raw is None:
        return None
    label = raw.strip().lower()
    if not label:
        return None
    return mapping.get(label)


def export_adr_status_events() -> None:
    repo_root = _get_repo_root()
    db_path = repo_root / "data" / "main_dataset.db"
    output_dir = repo_root / "supplementary_material" / "datasets" / "adr_status"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "adr_status_events.csv"

    status_mapping = _build_status_mapping()

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        query = """
            SELECT
                project_name,
                adr_id,
                adr_name,
                hash,
                points_to_adr_id,
                timestamp,
                year,
                month,
                adr_file_change_type,
                is_oldest,
                adr_old_status,
                adr_current_status
            FROM adr_tracking_info
        """
        cursor.execute(query)

        with output_path.open(mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "project_name",
                    "adr_id",
                    "adr_name",
                    "hash",
                    "points_to_adr_id",
                    "timestamp",
                    "year",
                    "month",
                    "adr_file_change_type",
                    "is_oldest",
                    "adr_old_status",
                    "adr_current_status",
                    "adr_old_status_normalized",
                    "adr_current_status_normalized",
                ]
            )

            for (
                project_name,
                adr_id,
                adr_name,
                hash_value,
                points_to_adr_id,
                timestamp,
                year,
                month,
                adr_file_change_type,
                is_oldest,
                adr_old_status,
                adr_current_status,
            ) in cursor:
                old_norm = normalize_status(adr_old_status, status_mapping)
                current_norm = normalize_status(adr_current_status, status_mapping)
                writer.writerow(
                    [
                        project_name,
                        adr_id,
                        adr_name,
                        hash_value,
                        points_to_adr_id,
                        timestamp,
                        year,
                        month,
                        adr_file_change_type,
                        is_oldest,
                        adr_old_status,
                        adr_current_status,
                        old_norm,
                        current_norm,
                    ]
                )
    finally:
        conn.close()


if __name__ == "__main__":
    export_adr_status_events()


