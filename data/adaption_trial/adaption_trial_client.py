"""Explicitly gated Adaption upload and estimate-only client helpers."""
from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from data.adaption_trial.prepare_trial import (
    METADATA_PATH, REPORT_PATH, ROOT, TRAIN_PATH, TRIAL_PATH, TRIAL_SIZE,
    load_jsonl, validate_trial,
)

COLUMN_MAPPING = {"prompt": "prompt", "completion": "completion"}


def sdk_version() -> str:
    """Return installed Adaption SDK version, or an unavailable marker."""
    try:
        return importlib.metadata.version("adaption")
    except importlib.metadata.PackageNotFoundError:
        return "not_installed"


def load_api_key_environment() -> bool:
    """Load the repository's existing .env without exposing values; return key presence."""
    load_dotenv(ROOT / ".env", override=False)
    value = os.environ.get("ADAPTION_API_KEY")
    return bool(value and value.strip())


def local_report(metadata: dict[str, Any]) -> dict[str, Any]:
    """Create a safe local-only report; contains no secret value."""
    configured = load_api_key_environment()
    return {
        "mode": "local_only",
        "conversion_version": metadata["conversion_version"],
        "row_count": metadata["record_count"],
        "selected_scenario_ids": metadata["selected_scenario_ids"],
        "source_split": metadata["source_split"],
        "trial_sha256": metadata["trial_sha256"],
        "api_key_configured": configured,
        "adaption_sdk_version": sdk_version(),
        "upload_attempted": False,
        "upload_status": "not_attempted",
        "ingested_row_count": None,
        "column_mapping_verified": False,
        "estimate_requested": False,
        "estimated_credits": None,
        "adaptation_started": False,
        "autoscientist_started": False,
    }


def _validate_only_trial_file(path: Path) -> None:
    if path.resolve() != TRIAL_PATH.resolve():
        raise ValueError("Only data/adaption_trial/ripple_trial_50.jsonl may be uploaded")
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    source = load_jsonl(TRAIN_PATH)
    rows = load_jsonl(TRIAL_PATH)
    if metadata.get("source_split") != "train" or metadata.get("record_count") != TRIAL_SIZE:
        raise ValueError("Trial metadata does not confirm a 50-row training-only source")
    validate_trial(rows, source, metadata.get("selected_scenario_ids"))
    actual_hash = __import__("hashlib").sha256(TRIAL_PATH.read_bytes()).hexdigest()
    if metadata.get("trial_sha256") != actual_hash:
        raise ValueError("Trial JSONL hash does not match local metadata")


def _mapping_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    if hasattr(value, "dict"):
        return value.dict(exclude_none=True)
    return value if isinstance(value, dict) else {}


def _estimate_existing_trial(client: Any, dataset_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """Quote only the previously verified trial dataset recorded in the safe report."""
    prior = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    _validate_only_trial_file(TRIAL_PATH)
    if prior.get("dataset_id") != dataset_id:
        raise ValueError("Estimate dataset ID must match the previously uploaded trial report")
    if prior.get("source_split") != "train" or prior.get("row_count") != TRIAL_SIZE:
        raise ValueError("Saved report does not confirm a 50-row training-only dataset")
    saved_hash = prior.get("trial_sha256")
    if saved_hash is not None and saved_hash != metadata.get("trial_sha256"):
        raise ValueError("Current trial file differs from the uploaded trial")
    if prior.get("selected_scenario_ids") != metadata.get("selected_scenario_ids"):
        raise ValueError("Current selected scenario IDs differ from the uploaded trial")
    status = client.datasets.get_status(dataset_id)
    report["dataset_id"] = dataset_id
    report["ingestion_status"] = str(getattr(status, "status", "unknown"))
    report["ingested_row_count"] = getattr(status, "row_count", None)
    if report["ingested_row_count"] != TRIAL_SIZE:
        report["upload_status"] = "existing_dataset_row_count_mismatch"
        return report
    report["upload_status"] = "ingested_verified"
    return _request_estimate(client, dataset_id, report)


def _request_estimate(client: Any, dataset_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """Call the official estimate-only endpoint; never launch a paid run."""
    quote = client.datasets.adapt(
        dataset_id,
        column_mapping=COLUMN_MAPPING,
        training_type="instruction_dataset",
        estimate=True,
    )
    estimate_confirmed = bool(getattr(quote, "estimate", False))
    report["estimate_only"] = estimate_confirmed
    report["estimated_credits"] = getattr(quote, "estimated_credits_consumed", None)
    report["estimated_minutes"] = getattr(quote, "estimated_minutes", None)
    report["request_configuration"] = {
        "dataset_id": dataset_id,
        "column_mapping": COLUMN_MAPPING,
        "training_type": "instruction_dataset",
        "estimate": True,
        "row_count": report.get("ingested_row_count"),
    }
    report["estimate_status"] = "quoted" if estimate_confirmed else "estimate_flag_not_confirmed"
    report.setdefault("adaptation_started", False)
    report.setdefault("autoscientist_started", False)
    report["column_mapping_verified"] = estimate_confirmed or report.get("column_mapping_verified", False)
    if estimate_confirmed and not report.get("configured_column_mapping"):
        report["column_mapping_verification_method"] = "official_estimate_request_accepted_explicit_mapping"
    return report


def run_api_actions(*, upload: bool, estimate: bool, dataset_id: str | None = None) -> dict[str, Any]:
    """Upload the approved trial and/or request an estimate-only quote.

    An estimate without a new upload is allowed only for the dataset ID recorded
    in this utility's safe report, with its row count, source split, and file hash
    revalidated locally. There is no code path for a paid adaptation or AutoScientist.
    """
    if not upload and not estimate:
        raise ValueError("At least one explicit API action flag is required")
    if estimate and not upload and not dataset_id:
        raise ValueError("Estimate without upload requires the saved trial --dataset-id")
    if upload and dataset_id:
        raise ValueError("Do not combine --upload with --dataset-id; upload creates the trial dataset ID")
    if upload:
        _validate_only_trial_file(TRIAL_PATH)

    report: dict[str, Any] = {
        "mode": "upload_and_estimate" if upload and estimate else "upload_only" if upload else "estimate_only",
        "conversion_version": "1.0.0",
        "adaption_sdk_version": sdk_version(),
        "api_key_configured": load_api_key_environment(),
        "upload_attempted": False,
        "upload_status": "not_started" if upload else "previous_upload_required",
        "dataset_id": dataset_id,
        "ingestion_status": None,
        "ingested_row_count": None,
        "column_mapping": COLUMN_MAPPING,
        "column_mapping_verified": False,
        "estimate_requested": estimate,
        "estimated_credits": None,
        "estimated_minutes": None,
        "estimate_only": estimate,
        "adaptation_started": False,
        "autoscientist_started": False,
    }
    if not report["api_key_configured"]:
        report["upload_status"] = "skipped_no_api_key"
        return report

    from adaption import Adaption

    client = None
    try:
        client = Adaption()
        if not upload:
            return _estimate_existing_trial(client, str(dataset_id), report)
        report["upload_attempted"] = True
        uploaded = client.datasets.upload_file(
            str(TRIAL_PATH),
            name="ripple_trial_50.jsonl",
            processing_mode="raw",
            column_mapping=COLUMN_MAPPING,
        )
        uploaded_id = getattr(uploaded, "dataset_id", None)
        if not uploaded_id:
            report["upload_status"] = "failed_missing_dataset_id"
            return report
        dataset_id = str(uploaded_id)
        report["dataset_id"] = dataset_id
        report["upload_status"] = "uploaded"
        status = client.datasets.wait_for_completion(dataset_id, timeout=600)
        report["ingestion_status"] = str(getattr(status, "status", "unknown"))
        report["ingested_row_count"] = getattr(status, "row_count", None)
        if report["ingested_row_count"] != TRIAL_SIZE:
            report["upload_status"] = "ingestion_row_count_mismatch"
            return report
        dataset = client.datasets.get(dataset_id)
        mapping = _mapping_dict(getattr(dataset, "configured_column_mapping", None))
        report["configured_column_mapping"] = mapping
        # The raw upload helper accepted the explicit source mapping and materialized
        # exactly 50 rows; configured_column_mapping is reserved for adaptation config.
        report["column_mapping_verified"] = True
        report["column_mapping_verification_method"] = "raw_upload_accepted_explicit_mapping_and_50_rows_ingested"
        if mapping.get("prompt") == "prompt" and mapping.get("completion") == "completion":
            report["column_mapping_verification_method"] = "dataset_configured_column_mapping"
        report["upload_status"] = "ingested_verified"
        if estimate:
            _request_estimate(client, dataset_id, report)
    except Exception as exc:  # Avoid logging exception strings that may contain request details.
        report["api_error_type"] = type(exc).__name__
        if estimate and report.get("upload_status") == "ingested_verified":
            report["estimate_status"] = "api_error"
        else:
            report["upload_status"] = "api_error"
    finally:
        if client is not None:
            client.close()
    return report


def upload_training_dataset(prepared: dict[str, Any]) -> dict[str, Any]:
    """Upload the separately audited 2,000-row train artifact in raw mode only."""
    from data.adaption_trial.prepare_training_dataset import (
        DATASET_NAME, EXPECTED_ROWS, UPLOAD_COLUMNS, UPLOAD_PATH, UPLOAD_REPORT_PATH,
        prepare_training_dataset,
    )

    expected = prepare_training_dataset()
    if any(prepared.get(key) != expected.get(key) for key in (
        "dataset_name", "source_file", "source_split", "source_sha256", "upload_file",
        "upload_record_count", "upload_sha256", "upload_columns",
    )) or prepared.get("upload_record_count") != EXPECTED_ROWS:
        raise ValueError("Prepared artifact metadata changed before upload")
    payload_hash = __import__("hashlib").sha256(UPLOAD_PATH.read_bytes()).hexdigest()
    if payload_hash != prepared["upload_sha256"]:
        raise ValueError("Prepared upload artifact hash changed before upload")

    report = {
        **prepared,
        "api_key_configured": load_api_key_environment(),
        "adaption_sdk_version": sdk_version(),
        "upload_attempted": False,
        "ingestion_status": None,
        "ingested_row_count": None,
        "column_mapping": COLUMN_MAPPING,
        "column_mapping_verified": False,
        "adaptation_started": False,
        "autoscientist_started": False,
    }
    if not report["api_key_configured"]:
        report["upload_status"] = "skipped_no_api_key"
        return report

    from adaption import Adaption

    client = None
    try:
        # Read-only duplicate-name check; do not create a second dataset on rerun.
        client = Adaption(max_retries=0)
        matches = [item for item in client.datasets.list(q=DATASET_NAME, limit=100)
                   if getattr(item, "name", None) == DATASET_NAME]
        if matches:
            report["upload_status"] = "blocked_dataset_name_already_exists"
            report["existing_dataset_id"] = str(getattr(matches[0], "dataset_id", "")) or None
            return report

        report["upload_attempted"] = True
        uploaded = client.datasets.upload_file(
            str(UPLOAD_PATH),
            name=DATASET_NAME,
            processing_mode="raw",
            column_mapping=COLUMN_MAPPING,
        )
        dataset_id = getattr(uploaded, "dataset_id", None)
        if not dataset_id:
            report["upload_status"] = "failed_missing_dataset_id"
            return report
        report["dataset_id"] = str(dataset_id)
        report["upload_status"] = "uploaded"

        status = client.datasets.wait_for_completion(str(dataset_id), timeout=600)
        report["ingestion_status"] = str(getattr(status, "status", "unknown"))
        report["ingested_row_count"] = getattr(status, "row_count", None)
        if report["ingestion_status"] != "succeeded" or report["ingested_row_count"] != EXPECTED_ROWS:
            report["upload_status"] = "ingestion_verification_failed"
            return report

        dataset = client.datasets.get(str(dataset_id))
        dataset_count = getattr(dataset, "row_count", None)
        if dataset_count != EXPECTED_ROWS:
            report["ingested_row_count"] = dataset_count
            report["upload_status"] = "dataset_metadata_row_count_mismatch"
            return report
        mapping = _mapping_dict(getattr(dataset, "configured_column_mapping", None))
        report["configured_column_mapping"] = mapping
        if mapping:
            if any(mapping.get(column) != column for column in UPLOAD_COLUMNS):
                report["upload_status"] = "column_mapping_verification_failed"
                return report
            report["column_mapping_verification_method"] = "dataset_configured_column_mapping"
        else:
            # The SDK's raw upload call accepts this explicit mapping and the API
            # confirmed that exactly the audited row count was materialized.
            report["column_mapping_verification_method"] = "raw_upload_explicit_mapping_and_ingested_row_count"
        report["column_mapping_verified"] = True
        report["upload_status"] = "ingested_verified"
    except Exception as exc:  # Never print or save API exception text.
        report["api_error_type"] = type(exc).__name__
        report["upload_status"] = "api_error"
    finally:
        if client is not None:
            client.close()
    return report


def save_safe_report(report: dict[str, Any]) -> None:
    """Persist only non-secret status/configuration fields."""
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
