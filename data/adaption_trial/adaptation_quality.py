"""Offline comparison helpers for original and adapted instruction examples."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import re
from typing import Any

from data.adaption_trial.prepare_trial import COMPLETION_KEYS, INSTRUCTION

PROMPT_FIELDS = ("original_prompt", "prompt", "enhanced_prompt")
SOURCE_COMPLETION_FIELDS = ("original_completion", "completion", "response", "answer")
ADAPTED_COMPLETION_FIELDS = ("enhanced_completion", "completion", "response", "answer")
CASCADE_FIELDS = ("direct_impacts", "second_order_impacts", "third_order_impacts", "further_impacts")
STRATEGIES = {"none", "reroute", "backup_supplier", "prioritize"}


def _first_string(row: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _json_target(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, str):
        return None, "completion is not a string"
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return None, "completion is malformed JSON"
    if not isinstance(parsed, dict):
        return None, "completion JSON is not an object"
    return parsed, None


def _scenario_nodes(prompt: str) -> set[str]:
    marker, schema_marker = "Scenario input (JSON):\n", "\n\nOutput JSON schema:"
    if marker not in prompt:
        return set()
    payload = prompt.split(marker, 1)[1].split(schema_marker, 1)[0]
    try:
        value = json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        return set()
    return {str(node.get("id")) for node in value.get("nodes", []) if isinstance(node, dict) and node.get("id")}


def _original_index(original_rows: list[dict[str, Any]]) -> tuple[dict[str, list[int]], dict[tuple[str, str], list[int]]]:
    by_prompt: dict[str, list[int]] = defaultdict(list)
    by_pair: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(original_rows):
        prompt = row.get("prompt")
        completion = row.get("completion")
        if isinstance(prompt, str):
            by_prompt[prompt].append(index)
            if isinstance(completion, str):
                by_pair[(prompt, completion)].append(index)
    return by_prompt, by_pair


def _match_row(row: dict[str, Any], by_prompt: dict[str, list[int]],
               by_pair: dict[tuple[str, str], list[int]]) -> tuple[int | None, str]:
    """Match by exact original prompt or exact prompt/completion pair; never fuzzy-match."""
    ambiguous_prompt = False
    for field in PROMPT_FIELDS:
        prompt = row.get(field)
        if isinstance(prompt, str) and prompt in by_prompt:
            matches = by_prompt[prompt]
            if len(matches) == 1:
                return matches[0], "exact_prompt"
            ambiguous_prompt = True
    for prompt_field in PROMPT_FIELDS:
        prompt = row.get(prompt_field)
        if not isinstance(prompt, str):
            continue
        for completion_field in SOURCE_COMPLETION_FIELDS:
            completion = row.get(completion_field)
            if isinstance(completion, str) and (prompt, completion) in by_pair:
                matches = by_pair[(prompt, completion)]
                return (matches[0], "exact_prompt_completion_pair") if len(matches) == 1 else (None, "ambiguous_pair")
    if ambiguous_prompt:
        return None, "ambiguous_prompt"
    return None, "unmatched_no_stable_original_prompt"


def compare_adapted_rows(original_rows: list[dict[str, Any]], adapted_rows: list[dict[str, Any]],
                         scenario_ids: list[str] | None = None) -> dict[str, Any]:
    """Compare dataset row counts, schema, JSON targets, and factual labels.

    Matching uses exact original prompts or exact original prompt/completion pairs.
    It deliberately avoids fuzzy or order-only matching when the platform removes
    the original fields.
    """
    by_prompt, by_pair = _original_index(original_rows)
    original_prompt_counts = Counter(row.get("prompt") for row in original_rows)
    original_pair_counts = Counter((row.get("prompt"), row.get("completion")) for row in original_rows)
    adapted_pair_counts = Counter(
        (_first_string(row, PROMPT_FIELDS), _first_string(row, ADAPTED_COMPLETION_FIELDS))
        for row in adapted_rows
    )
    matches: dict[int, int] = {}
    matched_methods: dict[int, str] = {}
    match_methods: Counter[str] = Counter()
    unmatched_rows: list[int] = []
    ambiguous_rows: list[int] = []
    changed_rows: list[dict[str, Any]] = []
    malformed: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    valid_json = 0
    schema_valid = 0
    prompt_nonempty = 0
    prompt_consistent = 0
    original_prompt_set = {row.get("prompt") for row in original_rows}

    for out_index, row in enumerate(adapted_rows):
        adapted_prompt = _first_string(row, PROMPT_FIELDS)
        adapted_completion = _first_string(row, ADAPTED_COMPLETION_FIELDS)
        target, parse_error = _json_target(adapted_completion)
        if parse_error:
            malformed.append({"adapted_row": out_index, "reason": parse_error})
        else:
            valid_json += 1
            if set(target) == set(COMPLETION_KEYS):
                schema_valid += 1
        if adapted_prompt:
            prompt_nonempty += 1
            if adapted_prompt in original_prompt_set:
                prompt_consistent += 1
        source_index, method = _match_row(row, by_prompt, by_pair)
        match_methods[method] += 1
        if source_index is None:
            (ambiguous_rows if method.startswith("ambiguous") else unmatched_rows).append(out_index)
            continue
        matches[out_index] = source_index
        matched_methods[out_index] = method
        source_target, _ = _json_target(original_rows[source_index].get("completion"))
        if parse_error:
            continue
        differences = {key: {"original": source_target.get(key), "adapted": target.get(key)}
                       for key in set(source_target or {}) | set(target)
                       if (source_target or {}).get(key) != target.get(key)}
        scenario_id = scenario_ids[source_index] if scenario_ids and source_index < len(scenario_ids) else None
        if differences:
            changed_rows.append({"adapted_row": out_index, "source_row": source_index,
                                 "scenario_id": scenario_id, "changed_fields": differences})
        prompt_for_nodes = original_rows[source_index].get("prompt", "")
        valid_nodes = _scenario_nodes(prompt_for_nodes)
        violations: list[str] = []
        for key in CASCADE_FIELDS + ("impacted_nodes",):
            value = target.get(key)
            if isinstance(value, list):
                unknown = sorted(str(item) for item in value if str(item) not in valid_nodes)
                if unknown:
                    violations.append(f"{key} includes unknown node IDs: {unknown}")
            elif key in target:
                violations.append(f"{key} must be a node ID list")
        bottleneck = target.get("predicted_bottleneck")
        if bottleneck is not None and str(bottleneck) not in valid_nodes:
            violations.append(f"predicted_bottleneck is unknown: {bottleneck}")
        ranking = target.get("ranked_mitigation_interventions")
        if not isinstance(ranking, list) or any(x not in STRATEGIES for x in ranking) or len(ranking) != len(set(ranking)):
            violations.append("ranked_mitigation_interventions has unsupported or duplicate strategies")
        severity = target.get("severity")
        if severity not in {"low", "medium", "high", "critical"}:
            violations.append(f"unsupported severity value: {severity}")
        if set(target) - set(COMPLETION_KEYS):
            violations.append(f"unsupported completion fields: {sorted(set(target) - set(COMPLETION_KEYS))}")
        if violations:
            unsupported.append({"adapted_row": out_index, "source_row": source_index, "claims": violations})

    matched_original_indices = set(matches.values())
    matched_records = [{"adapted_row": out_index, "source_row": source_index,
                        "scenario_id": scenario_ids[source_index] if scenario_ids and source_index < len(scenario_ids) else None,
                        "method": matched_methods[out_index]}
                       for out_index, source_index in sorted(matches.items())]
    missing_original = sorted(set(range(len(original_rows))) - matched_original_indices)
    duplicate_adapted = sum(n - 1 for n in adapted_pair_counts.values() if n > 1)
    duplicate_original = sum(n - 1 for n in original_pair_counts.values() if n > 1)
    extra_count = len(unmatched_rows) + len(ambiguous_rows)
    changed_fields_count = Counter(field for row in changed_rows for field in row["changed_fields"])
    exact_target_rows = sum(1 for out_index, source_index in matches.items()
                            if source_index < len(original_rows)
                            and out_index < len(adapted_rows)
                            and _json_target(original_rows[source_index].get("completion"))[0]
                            == _json_target(_first_string(adapted_rows[out_index], ADAPTED_COMPLETION_FIELDS))[0])
    total_adapted = len(adapted_rows)
    return {
        "status": "compared",
        "dataset_statistics": {
            "original_rows": len(original_rows), "adapted_rows": total_adapted,
            "original_duplicate_prompt_completion_rows": duplicate_original,
            "adapted_duplicate_prompt_completion_rows": duplicate_adapted,
            "missing_records": len(missing_original), "missing_source_row_indices": missing_original,
            "extra_or_unmatched_records": extra_count, "unmatched_adapted_row_indices": unmatched_rows,
            "ambiguous_adapted_row_indices": ambiguous_rows,
            "json_validity_rate": round(valid_json / total_adapted, 6) if total_adapted else 0.0,
        },
        "quality_checks": {
            "prompt_nonempty_rate": round(prompt_nonempty / total_adapted, 6) if total_adapted else 0.0,
            "prompt_exactly_unchanged_rate": round(prompt_consistent / total_adapted, 6) if total_adapted else 0.0,
            "prompt_consistency": len(original_prompt_set) <= 1 or all(
                isinstance(row.get("prompt"), str) and row["prompt"].startswith(INSTRUCTION) for row in original_rows),
            "target_schema_compliance_rate": round(schema_valid / valid_json, 6) if valid_json else 0.0,
            "factual_target_preservation_rate": round(exact_target_rows / len(matches), 6) if matches else 0.0,
            "changed_target_row_count": len(changed_rows),
            "changed_target_field_counts": dict(changed_fields_count),
            "malformed_outputs": malformed,
            "unsupported_claims": unsupported,
            "matching_method_counts": dict(match_methods),
            "matched_records": matched_records,
            "matching_limitation": None if not unmatched_rows and not ambiguous_rows else
                "Some rows did not preserve a unique exact original prompt or prompt/completion pair; no fuzzy matching was attempted.",
        },
        "changed_targets": changed_rows,
    }


def original_quality_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute local baseline quality without implying an adaptation occurred."""
    prompts = [row.get("prompt") for row in rows]
    valid = 0
    schema = 0
    for row in rows:
        target, error = _json_target(row.get("completion"))
        if error is None:
            valid += 1
            if set(target) == set(COMPLETION_KEYS):
                schema += 1
    pairs = Counter((row.get("prompt"), row.get("completion")) for row in rows)
    return {
        "status": "adaptation_not_run",
        "dataset_statistics": {
            "original_rows": len(rows), "adapted_rows": None,
            "original_duplicate_prompt_completion_rows": sum(n - 1 for n in pairs.values() if n > 1),
            "adapted_duplicate_prompt_completion_rows": None,
            "missing_records": None, "extra_records": None,
            "json_validity_rate": round(valid / len(rows), 6) if rows else 0.0,
        },
        "quality_checks": {
            "prompt_nonempty_rate": round(sum(isinstance(x, str) and bool(x.strip()) for x in prompts) / len(rows), 6) if rows else 0.0,
            "prompt_consistency": bool(rows) and all(isinstance(x, str) and x.startswith(INSTRUCTION) for x in prompts),
            "target_schema_compliance_rate": round(schema / valid, 6) if valid else 0.0,
            "adapted_prompt_clarity": "not evaluated; no adaptation run",
            "factual_target_preservation": "not evaluated; no adapted output",
            "malformed_outputs": [], "unsupported_claims": [],
        },
        "changed_target_row_count": None,
        "changed_targets": [],
        "note": "Adaptation has not been launched; adapted-row comparisons are intentionally not fabricated.",
    }


def write_examples(path: Any, original_rows: list[dict[str, Any]], adapted_rows: list[dict[str, Any]] | None,
                   comparison: dict[str, Any] | None) -> None:
    """Write example comparisons, or a clear not-run status without fake output."""
    if not adapted_rows or not comparison:
        path.write_text(
            "# Adaptation examples\n\nNo adaptation has been run, so there are no adapted examples to compare. "
            "This file intentionally contains no fabricated adapted output.\n",
            encoding="utf-8",
        )
        return
    lines = ["# Adaptation examples", "", "Examples are matched only through exact original prompt or prompt/completion values.", ""]
    by_prompt, by_pair = _original_index(original_rows)
    shown = 0
    for index, row in enumerate(adapted_rows):
        source_index, _ = _match_row(row, by_prompt, by_pair)
        if source_index is None:
            continue
        original = original_rows[source_index]
        adapted_prompt = _first_string(row, ("enhanced_prompt", "prompt", "original_prompt")) or ""
        adapted_completion = _first_string(row, ADAPTED_COMPLETION_FIELDS) or ""
        original_prompt = original["prompt"]
        original_completion = original["completion"]
        same = json.loads(original_completion) == _json_target(adapted_completion)[0] if _json_target(adapted_completion)[0] else False
        judgment = "neutral (unchanged target)" if same and original_prompt == adapted_prompt else "requires review (target or prompt changed)"
        lines.extend([f"## Example {shown + 1} — {judgment}", "", "### Original prompt", "", "```text", original_prompt, "```", "",
                      "### Adapted prompt", "", "```text", adapted_prompt, "```", "", "### Original completion", "", "```json", original_completion, "```", "",
                      "### Adapted completion", "", "```text", adapted_completion, "```", ""])
        shown += 1
        if shown >= 3:
            break
    if shown == 0:
        lines.append("No adapted row could be matched safely; no example pairing was guessed.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
