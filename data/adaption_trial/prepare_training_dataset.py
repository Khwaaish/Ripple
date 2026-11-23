"""Validate and convert the complete engine-labeled train split for Adaption."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from data.validate_dataset import read_jsonl, validate_record
from .prepare_trial import ROOT, TRAIN_PATH, convert_record

DATASET_NAME = "ripple_cascade_training_v1_2000"
UPLOAD_PATH = ROOT / "data" / "adaption_trial" / f"{DATASET_NAME}.jsonl"
UPLOAD_REPORT_PATH = ROOT / "data" / "adaption_trial" / f"{DATASET_NAME}_upload_report.json"
EXPECTED_ROWS = 2000
UPLOAD_COLUMNS = ("prompt", "completion")


def _duplicate_count(values: list[str]) -> int:
    return sum(count - 1 for count in Counter(values).values() if count > 1)


def prepare_training_dataset() -> dict[str, Any]:
    """Audit only train.jsonl, serialize its examples, and verify exact upload rows."""
    rows, read_errors = read_jsonl(TRAIN_PATH)
    if len(rows) != EXPECTED_ROWS or read_errors:
        raise ValueError("Training source must contain exactly 2,000 valid JSONL records")
    if any(row.get("split") != "train" for row in rows):
        raise ValueError("Training source contains a non-training record")

    engine_errors: list[str] = []
    scenario_fingerprints: list[str] = []
    record_fingerprints: list[str] = []
    scenario_ids: list[str] = []
    for row in rows:
        scenario_id, _, fingerprint = validate_record(row, "train", engine_errors)
        scenario_ids.append(scenario_id)
        scenario_fingerprints.append(fingerprint)
        canonical_record = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
        record_fingerprints.append(hashlib.sha256(canonical_record.encode("utf-8")).hexdigest())
    if engine_errors:
        raise ValueError("Training source failed deterministic engine/schema validation")
    if _duplicate_count(scenario_ids) or _duplicate_count(record_fingerprints) or _duplicate_count(scenario_fingerprints):
        raise ValueError("Training source contains duplicate IDs, records, or network/failure scenarios")

    converted = [convert_record(row) for row in rows]
    if any(set(row) != set(UPLOAD_COLUMNS) for row in converted):
        raise ValueError("Converted rows must contain exactly prompt and completion fields")
    if any(not isinstance(row[column], str) or not row[column].strip()
           for row in converted for column in UPLOAD_COLUMNS):
        raise ValueError("Converted rows contain empty prompt or completion values")
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
                      for row in converted)
    payload_bytes = payload.encode("utf-8")
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()

    # Avoid silently replacing an existing local artifact with different content.
    if UPLOAD_PATH.exists() and UPLOAD_PATH.read_bytes() != payload_bytes:
        raise ValueError("A different training upload artifact already exists; it was left untouched")
    if not UPLOAD_PATH.exists():
        UPLOAD_PATH.write_bytes(payload_bytes)

    # Re-read the exact bytes that will be uploaded and validate the two-column shape.
    uploaded_rows, upload_errors = read_jsonl(UPLOAD_PATH)
    if upload_errors or len(uploaded_rows) != EXPECTED_ROWS:
        raise ValueError("Prepared upload artifact failed JSONL row-count verification")
    if any(set(row) != set(UPLOAD_COLUMNS)
           or any(not isinstance(row.get(column), str) or not row[column].strip() for column in UPLOAD_COLUMNS)
           for row in uploaded_rows):
        raise ValueError("Prepared upload artifact contains an invalid prompt/completion row")
    if _duplicate_count([json.dumps(row, sort_keys=True, separators=(",", ":")) for row in uploaded_rows]):
        raise ValueError("Prepared upload artifact contains duplicate prompt/completion records")

    source_hash = hashlib.sha256(TRAIN_PATH.read_bytes()).hexdigest()
    return {
        "dataset_name": DATASET_NAME,
        "source_file": str(TRAIN_PATH.relative_to(ROOT)).replace("\\", "/"),
        "source_split": "train",
        "source_record_count": len(rows),
        "source_sha256": source_hash,
        "upload_file": str(UPLOAD_PATH.relative_to(ROOT)).replace("\\", "/"),
        "upload_record_count": len(uploaded_rows),
        "upload_sha256": payload_hash,
        "upload_columns": list(UPLOAD_COLUMNS),
        "duplicate_source_ids": 0,
        "duplicate_source_records": 0,
        "duplicate_network_failure_scenarios": 0,
        "duplicate_upload_records": 0,
        "engine_validation_errors": 0,
        "upload_status": "prepared",
    }


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upload", action="store_true", help="Upload the validated raw dataset (does not adapt or train)")
    args = parser.parse_args()
    report = prepare_training_dataset()
    if args.upload:
        from .adaption_trial_client import upload_training_dataset

        report = upload_training_dataset(report)
    UPLOAD_REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    public_report = {key: value for key, value in report.items() if key != "dataset_id"}
    print(json.dumps(public_report, indent=2, sort_keys=True))


if __name__ == "__main__":
    _main()
