"""Run exactly five training-split inference smoke tests on a Colab GPU."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from data.adaption_trial.prepare_trial import load_jsonl
from model.inference import AdaptionGemmaPredictor, InferenceResult, MODEL_LABEL

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRAIN_PATH = ROOT / "data" / "train.jsonl"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "evaluation" / "colab_smoke"
SMOKE_COUNT = 5
MIN_FREE_GPU_GIB = 12.0


def select_smoke_scenarios(rows: list[dict[str, Any]], count: int = SMOKE_COUNT) -> list[dict[str, Any]]:
    """Greedily select varied train records using metadata only, never labels."""
    if count != SMOKE_COUNT:
        raise ValueError("The smoke-test batch is fixed at exactly five scenarios")
    if any(row.get("split") != "train" for row in rows):
        raise ValueError("Smoke inference accepts training-split records only")
    if len({row.get("scenario_id") for row in rows}) != len(rows):
        raise ValueError("Training input contains duplicate or missing scenario IDs")
    if len(rows) < SMOKE_COUNT:
        raise ValueError("Training input must contain at least five scenarios")

    def features(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
        node_count = len(row["network"]["nodes"])
        failed_count = len(row["failed_nodes"])
        return (
            ("failure_type", str(row["failure_type"])),
            ("difficulty", str(row["difficulty"])),
            ("network_size", "6-8" if node_count <= 8 else "9-10" if node_count <= 10 else "11-12"),
            ("failure_count", "multiple" if failed_count > 1 else "single"),
        )

    candidates = sorted(rows, key=lambda row: str(row["scenario_id"]))
    selected: list[dict[str, Any]] = []
    represented: dict[str, set[str]] = {}
    while len(selected) < SMOKE_COUNT:
        def score(row: dict[str, Any]) -> tuple[int, str]:
            unseen = sum(value not in represented.setdefault(key, set()) for key, value in features(row))
            return unseen, str(row["scenario_id"])
        best = max(candidates, key=score)
        selected.append(best)
        for key, value in features(best):
            represented.setdefault(key, set()).add(value)
        candidates.remove(best)
    return selected


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")


def _preflight_gpu() -> dict[str, Any]:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("PyTorch is not installed in this Colab runtime; select a GPU runtime first.") from exc
    if not torch.cuda.is_available():
        raise RuntimeError("No CUDA GPU is available. In Colab select Runtime > Change runtime type > GPU.")
    properties = torch.cuda.get_device_properties(0)
    free_bytes, total_bytes = torch.cuda.mem_get_info(0)
    free_gib = free_bytes / 1024**3
    if free_gib < MIN_FREE_GPU_GIB:
        raise RuntimeError(
            f"GPU has {free_gib:.1f} GiB free; at least {MIN_FREE_GPU_GIB:.0f} GiB is required "
            "for the unquantized Gemma 3 4B checkpoint smoke test. No model weights were loaded."
        )
    return {
        "device_name": properties.name,
        "gpu_total_memory_gib": round(total_bytes / 1024**3, 2),
        "gpu_free_memory_gib_before_load": round(free_gib, 2),
        "cuda_version": torch.version.cuda,
        "torch_version": torch.__version__,
    }


def run_smoke_test(
    checkpoint_path: Path,
    train_path: Path = DEFAULT_TRAIN_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    base_model_id: str | None = None,
    max_new_tokens: int = 512,
) -> dict[str, Any]:
    """Load the actual adapter and run exactly five training-only scenarios."""
    if train_path.name.lower() in {"test.jsonl", "heldout.jsonl", "held_out.jsonl"}:
        raise ValueError("Held-out test files are not eligible for smoke inference")
    rows = load_jsonl(train_path)
    scenarios = select_smoke_scenarios(rows)
    gpu = _preflight_gpu()
    predictor = AdaptionGemmaPredictor.from_checkpoint(
        checkpoint_path,
        base_model_id=base_model_id,
        max_new_tokens=max_new_tokens,
    )
    if not predictor.adapter_applied:
        raise RuntimeError("Adapter was not confirmed loaded; no smoke inference was run.")

    results: list[InferenceResult] = []
    for row in scenarios:
        result = predictor.predict_scenario(
            row["network"],
            row["failed_nodes"],
            scenario_id=row["scenario_id"],
            failure_type=row["failure_type"],
            failure_description=row["failure_description"],
        )
        results.append(result)
        print(json.dumps({
            "scenario_id": result.scenario_id,
            "usable": result.usable,
            "json_valid": result.json_valid,
            "field_completeness": result.field_completeness,
            "node_references_valid": result.node_references_valid,
            "inference_duration_seconds": round(result.inference_duration_seconds, 3),
            "errors": result.errors,
        }, sort_keys=True))

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_rows = [result.to_dict() for result in results]
    parsed_rows = [{
        "scenario_id": result.scenario_id,
        "parsed_prediction": result.parsed_prediction,
        "json_valid": result.json_valid,
        "field_completeness": result.field_completeness,
        "node_references_valid": result.node_references_valid,
        "usable": result.usable,
        "errors": result.errors,
    } for result in results]
    _write_jsonl(output_dir / "raw_model_outputs.jsonl", raw_rows)
    _write_jsonl(output_dir / "parsed_predictions.jsonl", parsed_rows)
    report = {
        "smoke_test_only": True,
        "performance_evaluation": False,
        "source_split": "train",
        "scenarios_requested": SMOKE_COUNT,
        "scenarios_run": len(results),
        "usable_outputs": sum(result.usable for result in results),
        "json_valid_outputs": sum(result.json_valid for result in results),
        "complete_outputs": sum(result.field_completeness for result in results),
        "node_reference_valid_outputs": sum(result.node_references_valid for result in results),
        "model_identity": predictor.model_identity,
        "base_model_id": predictor.base_model_id,
        "checkpoint_identity": predictor.checkpoint_identity,
        "adapter_applied": predictor.adapter_applied,
        "gpu": gpu,
        "selected_scenarios": [{
            "scenario_id": row["scenario_id"],
            "failure_type": row["failure_type"],
            "difficulty": row["difficulty"],
            "node_count": len(row["network"]["nodes"]),
            "failed_node_count": len(row["failed_nodes"]),
        } for row in scenarios],
        "output_files": ["raw_model_outputs.jsonl", "parsed_predictions.jsonl"],
        "warnings": ["Training-split smoke tests are infrastructure checks, not unbiased model evaluation."],
    }
    report_path = output_dir / "smoke_test_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"smoke_test_report": str(report_path), "usable_outputs": report["usable_outputs"]}, sort_keys=True))
    return report


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True, help="Extracted adapter directory")
    parser.add_argument("--train-data", type=Path, default=DEFAULT_TRAIN_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-model-id", default=None,
                        help="Optional override; normally read from adapter_config.json")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    args = parser.parse_args()
    try:
        run_smoke_test(args.checkpoint, args.train_data, args.output_dir,
                       base_model_id=args.base_model_id, max_new_tokens=args.max_new_tokens)
    except Exception as exc:
        print(f"Smoke test stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    _main()
