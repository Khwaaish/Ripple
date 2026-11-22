"""Seeded, varied supply-chain scenario generation."""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any

from .models import Edge, Node, SupplyNetwork


@dataclass
class Scenario:
    """Generated network and a valid disruption set."""
    seed: int
    network: SupplyNetwork
    failed_nodes: list[str]
    failure_type: str
    failure_description: str
    difficulty: str

    def to_metadata(self, scenario_id: str, split: str) -> dict[str, Any]:
        return {
            "scenario_id": scenario_id,
            "seed": self.seed,
            "split": split,
            "difficulty": self.difficulty,
            "network": self.network.to_dict(),
            "failed_nodes": self.failed_nodes,
            "failure_type": self.failure_type,
            "failure_description": self.failure_description,
        }


def generate_scenario(seed: int, split: str = "train") -> Scenario:
    """Generate one reproducible network and a meaningful, valid failure set."""
    if split not in {"train", "test"}:
        raise ValueError("split must be 'train' or 'test'")
    rng = random.Random(seed)
    total = rng.randint(6, 12)
    supplier_count = rng.randint(2, min(3, total - 4))
    warehouse_count = rng.randint(2, min(4, total - supplier_count - 2))
    store_count = total - supplier_count - warehouse_count
    suppliers = [f"SUP{i + 1}" for i in range(supplier_count)]
    warehouses = [f"WH{i + 1}" for i in range(warehouse_count)]
    stores = [f"ST{i + 1}" for i in range(store_count)]
    topology = rng.choice(("hub", "regional", "mesh", "ladder"))

    nodes: list[Node] = []
    for node_id in suppliers:
        load = rng.randint(18, 55)
        nodes.append(Node(node_id, "supplier", round(load * rng.uniform(1.08, 1.8), 3), load,
                          rng.choice((0, 3, 6)), rng.random() < .15,
                          recovery_hours=rng.randint(12, 72), unit_cost=round(rng.uniform(1, 5), 2)))
    for node_id in warehouses:
        load = rng.randint(22, 65)
        nodes.append(Node(node_id, "warehouse", round(load * rng.uniform(1.02, 1.45), 3), load,
                          rng.choice((2, 4, 8, 12)), rng.random() < .18,
                          recovery_hours=rng.randint(8, 48), unit_cost=round(rng.uniform(1, 4), 2)))
    for node_id in stores:
        load = rng.randint(8, 36)
        critical = rng.random() < .28
        nodes.append(Node(node_id, "store", round(load * rng.uniform(1.05, 1.8), 3), load,
                          rng.choice((1, 3, 6, 12, 24)), critical,
                          recovery_hours=rng.randint(3, 24), unit_cost=round(rng.uniform(.5, 3), 2)))

    edges: list[Edge] = []
    supplier_edges: dict[str, list[str]] = {w: [] for w in warehouses}
    for wi, warehouse in enumerate(warehouses):
        if topology == "hub":
            primary = [suppliers[0]]
            if rng.random() < .72:
                primary.append(rng.choice(suppliers[1:]))
        elif topology == "regional":
            primary = [suppliers[wi % len(suppliers)]]
            if rng.random() < .55:
                primary.append(suppliers[(wi + 1) % len(suppliers)])
        elif topology == "ladder":
            primary = [suppliers[wi % len(suppliers)]]
            if rng.random() < .82:
                primary.append(suppliers[(wi + 1) % len(suppliers)])
        else:
            primary = [s for s in suppliers if rng.random() < .68]
            if not primary:
                primary = [rng.choice(suppliers)]
        supplier_edges[warehouse] = list(dict.fromkeys(primary))
        _append_share_edges(edges, primary, warehouse, nodes, rng, alternate=True)

    warehouse_edges: dict[str, list[str]] = {s: [] for s in stores}
    for si, store in enumerate(stores):
        if topology == "hub":
            selected = [warehouses[si % len(warehouses)]]
            if rng.random() < .6:
                selected.append(rng.choice([w for w in warehouses if w not in selected]))
        elif topology == "regional":
            selected = [warehouses[si % len(warehouses)]]
            if rng.random() < .42:
                selected.append(warehouses[(si + 1) % len(warehouses)])
        elif topology == "ladder":
            selected = [warehouses[si % len(warehouses)]]
            if rng.random() < .68:
                selected.append(warehouses[(si + 1) % len(warehouses)])
        else:
            selected = [w for w in warehouses if rng.random() < .58]
            if not selected:
                selected = [rng.choice(warehouses)]
        selected = list(dict.fromkeys(selected))
        warehouse_edges[store] = selected
        _append_share_edges(edges, selected, store, nodes, rng, alternate=True)

    network = SupplyNetwork({node.id: node for node in nodes}, edges)
    # Most disruptions start upstream; store failures are included as localized demand-side events.
    active_suppliers = [s for s in suppliers if any(e.src == s for e in edges)]
    active_warehouses = [w for w in warehouses if any(e.src == w for e in edges)]
    active_upstream = active_suppliers + active_warehouses
    mode = rng.random()
    if mode < .18 and len(active_upstream) >= 2:
        failed = sorted(rng.sample(active_upstream, 2))
        failure_type = "multiple"
    elif mode < .48 and active_suppliers:
        failed = [rng.choice(active_suppliers)]
        failure_type = "supplier"
    elif mode < .90 and active_warehouses:
        failed = [rng.choice(active_warehouses)]
        failure_type = "warehouse"
    elif mode < .94:
        failed = [rng.choice(stores)]
        failure_type = "store"
    else:
        failed = [rng.choice(active_upstream)]
        failure_type = "supplier" if failed[0] in suppliers else "warehouse"

    edge_count = len(edges)
    complexity = total + edge_count // 2 + (2 if len(failed) > 1 else 0)
    difficulty = "easy" if complexity <= 13 and len(failed) == 1 else "hard" if complexity >= 19 else "medium"
    desc_types = {"supplier": "supplier", "warehouse": "warehouse", "store": "store", "multiple": "simultaneous upstream facilities"}
    description = f"Failure of {', '.join(failed)} ({desc_types[failure_type]}) in a {topology} {total}-node network."
    if not any(e.src in failed for e in edges) and failure_type != "store":
        raise RuntimeError(f"Generated upstream failure has no dependent edges (seed {seed})")
    return Scenario(seed, network, failed, failure_type, description, difficulty)


def _append_share_edges(edges: list[Edge], sources: list[str], dst: str,
                        nodes: list[Node], rng: random.Random, *, alternate: bool) -> None:
    """Add inbound edges whose shares sum to one and whose limits are finite."""
    destination = next(n for n in nodes if n.id == dst)
    weights = [rng.uniform(.35, 1.0) for _ in sources]
    total = sum(weights)
    shares = [w / total for w in weights]
    for index, (src, share) in enumerate(zip(sources, shares)):
        nominal = destination.load * share
        cap = max(.1, round(nominal * rng.uniform(.72, 1.35), 3))
        edges.append(Edge(src, dst, round(share, 6), rng.randint(1, 12), cap,
                          round(rng.uniform(.88, 1.0), 4), alternate and index > 0))
