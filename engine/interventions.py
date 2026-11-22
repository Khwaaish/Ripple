from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

from .models import SupplyNetwork
from .simulate import SimulationResult, simulate


@dataclass
class InterventionComparison:
    """Comparable results and deterministic recommendation reasoning."""
    scenarios: dict[str, dict[str, Any]]
    recommended_strategy: str
    ranking: list[str]
    recommendation_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compare_interventions(network: SupplyNetwork, failed_nodes: list[str]) -> InterventionComparison:
    """Run baseline and all supported mitigation strategies."""
    results: dict[str, SimulationResult] = {
        strategy: simulate(network, failed_nodes, intervention=strategy)
        for strategy in ("none", "reroute", "backup_supplier", "prioritize")
    }
    baseline = results["none"].impact_score
    scenarios: dict[str, dict[str, Any]] = {}
    for name, result in results.items():
        scenarios[name] = {
            "impact_score": result.impact_score,
            "nodes_disrupted": result.all_impacted_nodes,
            "critical_shortages": result.critical_shortage_nodes,
            "overloaded_nodes": result.overloaded_nodes,
            "estimated_recovery_time_h": result.recovery_estimate_h,
            "intervention_cost": result.intervention_cost,
            "relative_impact_vs_baseline": round(result.impact_score / baseline, 6) if baseline else (0.0 if result.impact_score == 0 else None),
            "reasoning": result.reasoning,
            "node_impacts": result.node_impacts,
        }
    ranking = sorted(results, key=lambda name: (results[name].impact_score, results[name].recovery_estimate_h,
                                                 results[name].intervention_cost, name))
    winner = ranking[0]
    return InterventionComparison(scenarios, winner, ranking,
        f"Selected {winner}: lowest weighted impact, then recovery time, then intervention cost.")
