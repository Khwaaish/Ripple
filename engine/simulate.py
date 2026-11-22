from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import networkx as nx

from .models import SupplyNetwork


@dataclass
class SimulationResult:
    """Calculated cascade outcomes and trace data for one scenario."""
    failed_nodes: list[str]
    directly_impacted_nodes: list[str]
    second_order_impacted_nodes: list[str]
    third_order_impacted_nodes: list[str]
    further_impacted_nodes: list[str]
    all_impacted_nodes: list[str]
    overloaded_nodes: list[str]
    critical_shortage_nodes: list[str]
    bottleneck_node: str | None
    first_predicted_stockout_time_h: float | None
    propagation_rounds: int
    impact_score: float
    severity: str
    round_snapshots: list[dict[str, Any]]
    node_impacts: dict[str, dict[str, float | bool | None]]
    recovery_estimate_h: float
    intervention: str = "none"
    intervention_cost: float = 0.0
    reasoning: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible result data."""
        return asdict(self)


def simulate(network: SupplyNetwork, failed_nodes: list[str], intervention: str = "none", *,
             max_rounds: int = 5, backup_capacity: float | None = None,
             activation_delay_h: float = 12.0, operational_cost: float = 0.0) -> SimulationResult:
    """Simulate a deterministic disruption cascade without mutating ``network``.

    A source failure removes its edge flow. Losses are propagated by rounds,
    capped by edge capacity and destination demand share. Buffer time delays
    stockout onset. ``reroute`` and ``prioritize`` use alternate incoming edges;
    ``backup_supplier`` supplies a bounded temporary amount after its delay.
    """
    if intervention not in {"none", "reroute", "backup_supplier", "prioritize"}:
        raise ValueError(f"Unknown intervention: {intervention}")
    if max_rounds < 1:
        raise ValueError("max_rounds must be at least 1")
    unknown = sorted(set(failed_nodes) - set(network.nodes))
    if unknown:
        raise ValueError(f"Unknown failed node(s): {', '.join(unknown)}")
    if activation_delay_h < 0 or operational_cost < 0:
        raise ValueError("Activation delay and operational cost must be non-negative")

    nodes = network.nodes
    failed = set(failed_nodes)
    losses: dict[str, float] = {n: 0.0 for n in nodes}
    first_arrival: dict[str, float] = {}
    impacted_round: dict[str, int] = {}
    overloaded: set[str] = set()
    snapshots: list[dict[str, Any]] = []
    reasoning: list[str] = []
    alternate_spare = {n: max(0.0, node.capacity - node.load) for n, node in nodes.items()}
    propagated = {n: 0.0 for n in nodes}

    def edge_flow(edge: Any) -> float:
        return min(nodes[edge.dst].load * edge.share, edge.capacity) * edge.reliability

    for node_id in failed:
        losses[node_id] = nodes[node_id].load
        first_arrival[node_id] = 0.0
        impacted_round[node_id] = 0

    # Fixed topological traversal, repeated in rounds to make each cascade layer explicit.
    order = list(nx.topological_sort(network.graph))
    for round_no in range(1, max_rounds + 1):
        changed = False
        round_new: list[str] = []
        for src in order:
            if src in failed and round_no > 1:
                continue
            if src not in failed and (losses[src] <= 0 or impacted_round.get(src, round_no) >= round_no):
                continue
            source_loss = nodes[src].load if src in failed else max(0.0, losses[src] - propagated[src])
            if source_loss <= 1e-9:
                continue
            ratio = 1.0 if src in failed else (source_loss / nodes[src].load if nodes[src].load else 0.0)
            outgoing = [e for e in network.edges if e.src == src]
            outgoing.sort(key=lambda e: (not nodes[e.dst].critical, e.dst) if intervention == "prioritize" else (False, e.dst))
            for edge in outgoing:
                dst = edge.dst
                if dst in failed:
                    continue
                flow_loss = min(edge_flow(edge), edge.capacity) * ratio
                if flow_loss <= 0:
                    continue
                arrival = first_arrival.get(src, 0.0) + edge.delay_h
                # A destination incurs supply loss at arrival and stocks out after its buffer.
                if intervention in {"reroute", "prioritize"}:
                    flow_loss = _cover_with_alternates(network, dst, flow_loss, losses, nodes, overloaded, reasoning, alternate_spare, impacted_round, round_new, first_arrival, arrival, round_no, prioritize=(intervention == "prioritize"))
                elif intervention == "backup_supplier":
                    cap = backup_capacity if backup_capacity is not None else nodes[sorted(failed)[0]].capacity * .6
                    if arrival >= activation_delay_h:
                        covered = min(flow_loss, cap)
                        flow_loss -= covered
                        cap -= covered
                        backup_capacity = cap
                        if covered:
                            reasoning.append(f"Temporary backup covered {covered:g} units at {dst} after {activation_delay_h:g}h")
                new_loss = min(nodes[dst].load, losses[dst] + flow_loss)
                if new_loss > losses[dst] + 1e-9:
                    losses[dst] = new_loss
                    stockout_time = arrival + nodes[dst].buffer_hours
                    first_arrival[dst] = min(first_arrival.get(dst, stockout_time), stockout_time)
                    if dst not in impacted_round:
                        impacted_round[dst] = round_no
                        round_new.append(dst)
                    changed = True
            propagated[src] = losses[src]
        snapshots.append({"round": round_no, "newly_impacted": sorted(round_new),
                          "losses": {n: round(losses[n], 6) for n in sorted(losses) if losses[n] > 0},
                          "overloaded_nodes": sorted(overloaded)})
        if not changed:
            break

    impacted = sorted(n for n, loss in losses.items() if loss > 0 and n not in failed)
    direct = sorted(n for n in impacted if impacted_round.get(n) == 1)
    second = sorted(n for n in impacted if impacted_round.get(n) == 2)
    third = sorted(n for n in impacted if impacted_round.get(n) == 3)
    further = sorted(n for n in impacted if impacted_round.get(n, 0) >= 4)
    critical = sorted(n for n in impacted if nodes[n].critical)
    total_demand = sum(n.load for n in nodes.values())
    weighted_unmet = sum(losses[n] * float(nodes[n].criticality_weight) for n in nodes if n not in failed)
    score = min(1.0, weighted_unmet / total_demand) if total_demand else 0.0
    severity = "critical" if score >= .5 else "high" if score >= .25 else "medium" if score > 0 else "low"
    bottleneck = max(impacted, key=lambda n: (losses[n] * float(nodes[n].criticality_weight), n), default=None)
    stockouts = [first_arrival[n] for n in impacted]
    recovery = max((nodes[n].recovery_hours + losses[n] for n in set(impacted) | failed), default=0.0)
    node_impacts = {n: {"lost_supply": round(losses[n], 6), "shortage": round(losses[n], 6),
                        "shortage_fraction": round(losses[n] / nodes[n].load, 6) if nodes[n].load else 0.0,
                        "stockout_time_h": first_arrival.get(n), "critical": nodes[n].critical}
                    for n in sorted(nodes)}
    if not reasoning:
        reasoning.append("No intervention supply was applied" if intervention == "none" else f"{intervention} found no eligible coverage")
    return SimulationResult(sorted(failed), direct, second, third, further, impacted,
        sorted(overloaded), critical, bottleneck, min(stockouts, default=None), len(snapshots),
        round(score, 6), severity, snapshots, node_impacts, round(recovery, 6), intervention,
        operational_cost if intervention == "backup_supplier" else 0.0, reasoning)


def _cover_with_alternates(network: SupplyNetwork, dst: str, shortage: float,
                           losses: dict[str, float], nodes: dict[str, Any], overloaded: set[str],
                           reasoning: list[str], alternate_spare: dict[str, float],
                           impacted_round: dict[str, int], round_new: list[str],
                           first_arrival: dict[str, float], arrival: float,
                           round_no: int, prioritize: bool) -> float:
    """Allocate eligible alternate flow within spare and link capacity."""
    remaining = shortage
    inbound = sorted((e for e in network.edges if e.dst == dst and e.is_alt), key=lambda e: (e.src, e.dst))
    for edge in inbound:
        source = nodes[edge.src]
        if losses[edge.src] > 0:
            continue
        spare = alternate_spare[edge.src]
        requested = min(remaining, edge.capacity, nodes[dst].load * edge.share) * edge.reliability
        if requested > spare + 1e-9:
            overloaded.add(edge.src)
            overload_loss = requested - spare
            losses[edge.src] = min(source.load, losses[edge.src] + overload_loss)
            if edge.src not in impacted_round:
                impacted_round[edge.src] = round_no
                round_new.append(edge.src)
            overload_stockout = arrival + source.buffer_hours
            first_arrival[edge.src] = min(first_arrival.get(edge.src, overload_stockout), overload_stockout)
            reasoning.append(f"Alternate {edge.src} exceeded spare capacity by {overload_loss:g} units; its downstream flow is exposed")
        eligible = min(requested, spare)
        if eligible > 0:
            remaining -= eligible
            alternate_spare[edge.src] -= eligible
            reasoning.append(f"Alternate {edge.src} covered {eligible:g} units at {dst}")
    if prioritize and nodes[dst].critical:
        reasoning.append(f"Priority policy allocated supply to critical node {dst} before non-critical destinations")
    return remaining
