"""Plan-only by default; launch one explicit Adaptive Data trial with --run-adaptation."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.adaption_trial.adaptation_quality import compare_adapted_rows, original_quality_report, write_examples
from data.adaption_trial.adaption_trial_client import load_api_key_environment, sdk_version
from data.adaption_trial.prepare_trial import (
    COMPLETION_KEYS, METADATA_PATH, REPORT_PATH, ROOT as PROJECT_ROOT, TRAIN_PATH, TRIAL_PATH,
    TRIAL_SIZE, load_jsonl, validate_trial,
)
from data.adaption_trial.adaptation_quality import _json_target
from data.adaption_trial.prepare_trial import select_trial_records

TRIAL_DIR = Path(__file__).resolve().parent
RUN_METADATA_PATH = TRIAL_DIR / "adaptation_run_metadata.json"
QUALITY_REPORT_PATH = TRIAL_DIR / "adaptation_quality_report.json"
EXAMPLES_PATH = TRIAL_DIR / "adaptation_examples.md"
ADAPTED_PATH = TRIAL_DIR / "adapted_trial_50.jsonl"
RECIPE_SPECIFICATION = {"recipes": {"deduplication": True, "prompt_rephrase": False, "reasoning_traces": False}}
COLUMN_MAPPING = {"prompt": "prompt", "completion": "completion"}
TRAINING_TYPE = "instruction_dataset"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _stable_idempotency_key(dataset_id: str, trial_sha256: str) -> str:
    return "ripple-batch4-" + hashlib.sha256(f"{dataset_id}:{trial_sha256}".encode()).hexdigest()[:32]


def validate_local_trial() -> dict[str, Any]:
    """Check trial, source IDs, target JSON/schema, hashes, and training-only provenance."""
    trial_meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    saved_report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    dataset_id = os.environ.get("ADAPTION_DATASET_ID") or saved_report.get("dataset_id")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("Configure the existing Adaption dataset ID in local .env; dataset IDs are not stored in source")
    dataset_id = dataset_id.strip()
    source_rows = load_jsonl(TRAIN_PATH)
    trial_rows = load_jsonl(TRIAL_PATH)
    ids = trial_meta.get("selected_scenario_ids")
    if trial_meta.get("source_file") != "data/train.jsonl" or trial_meta.get("source_split") != "train":
        raise ValueError("Trial metadata does not identify the training split")
    if len(trial_rows) != TRIAL_SIZE or trial_meta.get("record_count") != TRIAL_SIZE:
        raise ValueError("Expected exactly 50 local trial rows")
    if not isinstance(ids, list) or len(ids) != TRIAL_SIZE or len(set(ids)) != TRIAL_SIZE:
        raise ValueError("Trial metadata must list 50 unique source scenario IDs")
    if any(row.get("split") != "train" for row in source_rows):
        raise ValueError("Configured source file contains a non-training row")
    reproduced_ids = [row["scenario_id"] for row in select_trial_records(
        source_rows, count=TRIAL_SIZE, seed=trial_meta["selection_seed"])]
    if ids != reproduced_ids:
        raise ValueError("Selected IDs are not reproducible from the training source and saved seed")
    validate_trial(trial_rows, source_rows, ids)
    trial_hash = _hash(TRIAL_PATH)
    if trial_hash != trial_meta.get("trial_sha256"):
        raise ValueError("Trial file hash differs from trial_metadata.json")
    if saved_report.get("trial_sha256") != trial_hash:
        raise ValueError("Trial file hash differs from safe_trial_report.json")
    if saved_report.get("dataset_id") != dataset_id:
        raise ValueError("Saved Adaption report does not identify the authorized dataset ID")
    if saved_report.get("source_split") != "train" or saved_report.get("ingested_row_count") != TRIAL_SIZE:
        raise ValueError("Saved Adaption report does not verify the 50-row training-only ingestion")
    if saved_report.get("column_mapping") != COLUMN_MAPPING or not saved_report.get("column_mapping_verified"):
        raise ValueError("Saved Adaption report does not verify prompt/completion mapping")

    target_errors: list[str] = []
    for index, (row, scenario_id) in enumerate(zip(trial_rows, ids)):
        if set(row) != {"prompt", "completion"}:
            target_errors.append(f"row {index} is not exactly prompt/completion")
            continue
        target, error = _json_target(row["completion"])
        if error:
            target_errors.append(f"{scenario_id}: {error}")
            continue
        if set(target) != set(COMPLETION_KEYS):
            target_errors.append(f"{scenario_id}: completion schema mismatch")
            continue
        if target["severity"] not in {"low", "medium", "high", "critical"}:
            target_errors.append(f"{scenario_id}: invalid severity")
        if not isinstance(target["ranked_mitigation_interventions"], list):
            target_errors.append(f"{scenario_id}: intervention ranking is not a list")
    if target_errors:
        raise ValueError("Invalid trial targets: " + "; ".join(target_errors[:5]))

    return {
        "trial_rows": trial_rows,
        "source_rows": source_rows,
        "trial_metadata": trial_meta,
        "scenario_ids": ids,
        "dataset_id": dataset_id,
        "trial_sha256": trial_hash,
        "train_sha256_before": _hash(TRAIN_PATH),
        "local_quality": original_quality_report(trial_rows),
        "saved_estimate_credits": saved_report.get("estimated_credits"),
        "saved_estimate_minutes": saved_report.get("estimated_minutes"),
        "saved_ingestion_status": saved_report.get("ingestion_status"),
    }


def _previous_run_attempted() -> bool:
    if not RUN_METADATA_PATH.exists():
        return False
    try:
        previous = json.loads(RUN_METADATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Malformed run metadata is a hard stop for a paid operation.
        return True
    return bool(previous.get("paid_operation_attempted"))


def collect_plan(client: Any | None, local: dict[str, Any], *, api_key_configured: bool) -> dict[str, Any]:
    """Build a current plan and fresh quote; this never starts an adaptation."""
    dataset_id = local["dataset_id"]
    idem_key = _stable_idempotency_key(dataset_id, local["trial_sha256"])
    plan: dict[str, Any] = {
        "dataset_id": dataset_id,
        "row_count": TRIAL_SIZE,
        "operation": "Adaptive Data optimization via datasets.adapt (not AutoScientist/model training)",
        "column_mapping": COLUMN_MAPPING,
        "training_type": TRAINING_TYPE,
        "recipe_specification": RECIPE_SPECIFICATION,
        "job_specification": {"max_rows": TRIAL_SIZE, "idempotency_key": idem_key},
        "previous_confirmed_estimate_credits": local.get("saved_estimate_credits"),
        "current_estimated_credits": None,
        "estimated_minutes": None,
        "current_ingestion_status": None,
        "current_row_count": None,
        "remote_run_id": None,
        "estimate_confirmed": False,
        "quote_changed": None,
        "run_allowed": False,
        "plan_only": True,
        "paid_operation_attempted": False,
        "api_key_configured": api_key_configured,
        "adaption_sdk_version": sdk_version(),
        "trial_sha256": local["trial_sha256"],
        "train_sha256_before": local["train_sha256_before"],
        "held_out_test_accessed": False,
        "held_out_test_uploaded": False,
        "adaptation_started": False,
        "autoscientist_started": False,
        "actual_credits_spent": None,
        "actual_credit_usage_status": "no paid operation launched",
    }
    if _previous_run_attempted():
        plan["run_allowed"] = False
        plan["preflight_status"] = "previous_paid_attempt_recorded; automatic/duplicate run blocked"
        return plan
    if not api_key_configured or client is None:
        plan["preflight_status"] = "blocked_no_api_key"
        return plan

    status = client.datasets.get_status(dataset_id)
    plan["current_ingestion_status"] = getattr(status, "status", None)
    plan["current_row_count"] = getattr(status, "row_count", None)
    if plan["current_row_count"] != TRIAL_SIZE or plan["current_ingestion_status"] not in {"succeeded", "ready"}:
        plan["preflight_status"] = "blocked_dataset_not_ready_or_row_count_changed"
        return plan

    dataset = client.datasets.get(dataset_id)
    plan["remote_run_id"] = getattr(dataset, "run_id", None)

    quote = client.datasets.adapt(
        dataset_id,
        column_mapping=COLUMN_MAPPING,
        recipe_specification=RECIPE_SPECIFICATION,
        job_specification={"max_rows": TRIAL_SIZE},
        training_type=TRAINING_TYPE,
        estimate=True,
    )
    plan["estimate_confirmed"] = bool(getattr(quote, "estimate", False))
    plan["current_estimated_credits"] = getattr(quote, "estimated_credits_consumed", None)
    plan["estimated_minutes"] = getattr(quote, "estimated_minutes", None)
    if not plan["estimate_confirmed"]:
        plan["preflight_status"] = "blocked_estimate_response_not_confirmed"
        return plan
    old_quote = local.get("saved_estimate_credits")
    plan["quote_changed"] = plan["current_estimated_credits"] != plan["previous_confirmed_estimate_credits"]
    plan["previous_saved_quote_credits"] = old_quote
    if plan["quote_changed"]:
        plan["preflight_status"] = "quote_changed_stop_for_manual_review"
        return plan
    if plan["remote_run_id"]:
        plan["preflight_status"] = "estimate_confirmed_but_existing_run_id_requires_manual_review"
        return plan
    plan["preflight_status"] = "ready_for_manual_explicit_flag"
    plan["run_allowed"] = True
    return plan


def write_plan_artifacts(plan: dict[str, Any], local: dict[str, Any]) -> None:
    """Write plan and not-run quality artifacts without fabricating adapted output."""
    existing_attempt = _previous_run_attempted()
    metadata = {
        "dataset_id": local["dataset_id"],
        "operation": plan["operation"],
        "adaption_sdk_version": plan["adaption_sdk_version"],
        "trial_file": "data/adaption_trial/ripple_trial_50.jsonl",
        "trial_sha256": local["trial_sha256"],
        "source_file": "data/train.jsonl",
        "source_split": "train",
        "train_sha256_before": local["train_sha256_before"],
        "selected_scenario_ids": local["scenario_ids"],
        "row_count": TRIAL_SIZE,
        "current_ingestion_status": plan.get("current_ingestion_status"),
        "current_row_count": plan.get("current_row_count"),
        "remote_run_id_present": bool(plan.get("remote_run_id")),
        "previous_confirmed_estimate_credits": local.get("saved_estimate_credits"),
        "current_estimated_credits": plan.get("current_estimated_credits"),
        "estimated_minutes": plan.get("estimated_minutes"),
        "request_configuration": {
            "column_mapping": COLUMN_MAPPING,
            "training_type": TRAINING_TYPE,
            "recipe_specification": RECIPE_SPECIFICATION,
            "job_specification": plan["job_specification"],
            "estimate_only": True,
        },
        "preflight_status": plan.get("preflight_status"),
        "plan_only": True,
        "paid_operation_attempted": existing_attempt,
        "adaptation_started": existing_attempt,
        "autoscientist_started": False,
        "actual_credits_spent": None,
        "held_out_test_accessed": False,
        "held_out_test_uploaded": False,
    }
    _write_json(RUN_METADATA_PATH, metadata)
    quality = local["local_quality"]
    quality.update({
        "dataset_id": local["dataset_id"],
        "plan_only": True,
        "run_started": False,
        "preflight_status": plan.get("preflight_status"),
        "current_ingestion_status": plan.get("current_ingestion_status"),
        "current_row_count": plan.get("current_row_count"),
        "estimated_credits": plan.get("current_estimated_credits"),
        "estimated_minutes": plan.get("estimated_minutes"),
        "factual_target_comparison": "not run; no adapted output exists",
        "held_out_test_accessed": False,
    })
    _write_json(QUALITY_REPORT_PATH, quality)
    write_examples(EXAMPLES_PATH, local["trial_rows"], None, None)


def launch_once(client: Any, plan: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    """Launch exactly one paid request, with SDK retries disabled and a persisted guard."""
    if not plan.get("run_allowed") or not plan.get("estimate_confirmed"):
        raise RuntimeError("Preflight did not authorize launch; no paid operation was submitted")
    if plan.get("current_estimated_credits") != plan.get("previous_confirmed_estimate_credits"):
        raise RuntimeError("Fresh estimate differs from the locally saved, previously confirmed estimate")
    if _previous_run_attempted():
        raise RuntimeError("A paid operation was already attempted; automatic second runs are blocked")

    now = datetime.now(timezone.utc).isoformat()
    metadata = json.loads(RUN_METADATA_PATH.read_text(encoding="utf-8"))
    metadata.update({"plan_only": False, "paid_operation_attempted": True,
                     "paid_operation_attempted_at_utc": now, "run_status": "launch_request_submitted_once"})
    _write_json(RUN_METADATA_PATH, metadata)
    # One call only. The SDK client is configured with max_retries=0.
    response = client.datasets.adapt(
        plan["dataset_id"],
        column_mapping=COLUMN_MAPPING,
        recipe_specification=RECIPE_SPECIFICATION,
        job_specification=plan["job_specification"],
        training_type=TRAINING_TYPE,
        estimate=False,
    )
    metadata["run_id"] = getattr(response, "run_id", None)
    metadata["response_estimated_credits_consumed"] = getattr(response, "estimated_credits_consumed", None)
    metadata["response_estimated_minutes"] = getattr(response, "estimated_minutes", None)
    metadata["run_status"] = "submitted"
    metadata["adaptation_started"] = True
    _write_json(RUN_METADATA_PATH, metadata)

    status = client.datasets.wait_for_completion(plan["dataset_id"], timeout=3600)
    metadata["completion_status"] = getattr(status, "status", None)
    metadata["completed_row_count"] = getattr(status, "row_count", None)
    if getattr(status, "status", None) not in {"succeeded", "ready"}:
        metadata["run_status"] = "completed_with_non_success_status"
        _write_json(RUN_METADATA_PATH, metadata)
        return metadata

    downloaded = client.datasets.download(plan["dataset_id"], file_format="jsonl")
    payload = downloaded.read()
    if not isinstance(payload, bytes):
        raise TypeError("SDK JSONL download response did not return bytes")
    ADAPTED_PATH.write_bytes(payload)
    adapted_rows = []
    for line_number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            row = {"_malformed_jsonl_line": line_number, "_raw": line}
        if isinstance(row, dict):
            adapted_rows.append(row)
        else:
            adapted_rows.append({"_malformed_jsonl_line": line_number, "_raw": row})
    comparison = compare_adapted_rows(local["trial_rows"], adapted_rows, local["scenario_ids"])
    comparison["download_file"] = "data/adaption_trial/adapted_trial_50.jsonl"
    comparison["adaptation_run_id"] = metadata["run_id"]
    comparison["actual_credits_spent"] = None
    comparison["actual_credit_usage_status"] = (
        "The installed SDK response schema exposes estimated_credits_consumed but no actual credits-spent field; "
        "verify actual usage in the Adaption account billing/usage view."
    )
    _write_json(QUALITY_REPORT_PATH, comparison)
    write_examples(EXAMPLES_PATH, local["trial_rows"], adapted_rows, comparison)
    metadata["adapted_file"] = "data/adaption_trial/adapted_trial_50.jsonl"
    metadata["quality_report"] = "data/adaption_trial/adaptation_quality_report.json"
    metadata["run_status"] = "completed_and_downloaded"
    metadata["actual_credits_spent"] = None
    metadata["actual_credit_usage_status"] = comparison["actual_credit_usage_status"]
    metadata["held_out_test_accessed"] = False
    metadata["autoscientist_started"] = False
    metadata["train_sha256_after"] = _hash(TRAIN_PATH)
    metadata["source_train_unchanged"] = metadata["train_sha256_before"] == metadata["train_sha256_after"]
    _write_json(RUN_METADATA_PATH, metadata)
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-adaptation", action="store_true",
                        help="Submit exactly one paid Adaptive Data operation after preflight; never trains a model")
    args = parser.parse_args(argv)
    local = validate_local_trial()
    api_key_configured = load_api_key_environment()
    client = None
    try:
        if api_key_configured:
            from adaption import Adaption
            client = Adaption(max_retries=0)
        plan = collect_plan(client, local, api_key_configured=api_key_configured)
        plan["plan_only"] = not args.run_adaptation
        write_plan_artifacts(plan, local)
        print(json.dumps({"execution_plan": {
            "dataset_id": plan["dataset_id"],
            "row_count": plan["row_count"],
            "operation": plan["operation"],
            "estimated_credits": plan["current_estimated_credits"],
            "estimated_runtime_minutes": plan["estimated_minutes"],
            "ingestion_status": plan["current_ingestion_status"],
            "preflight_status": plan["preflight_status"],
            "run_flag_supplied": args.run_adaptation,
            "adaptation_started": False,
            "autoscientist_started": False,
        }}, indent=2))
        if not args.run_adaptation:
            return 0
        if not plan.get("run_allowed"):
            print("Paid operation not submitted: current preflight did not pass.")
            return 2
        print("Submitting one Adaptive Data request because --run-adaptation was explicitly supplied.")
        result = launch_once(client, plan, local)
        print(json.dumps({"run_status": result.get("run_status"), "run_id": result.get("run_id"),
                          "completion_status": result.get("completion_status"),
                          "adapted_file": result.get("adapted_file"),
                          "actual_credits_spent": result.get("actual_credits_spent"),
                          "autoscientist_started": False}, indent=2))
        return 0
    except Exception as exc:
        # Never emit raw SDK exceptions; they can include request details.
        print(json.dumps({"preflight_or_run_error_type": type(exc).__name__,
                          "adaptation_started": False if not args.run_adaptation else None,
                          "autoscientist_started": False}, indent=2))
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
