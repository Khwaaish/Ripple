from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any, Literal
import copy

import networkx as nx

NodeType = Literal["supplier", "warehouse", "store"]
NODE_TYPES = {"supplier", "warehouse", "store"}


def _number(name: str, value: float, *, minimum: float = 0.0, strict: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value <= minimum if strict else value < minimum:
        op = "greater than" if strict else "at least"
        raise ValueError(f"{name} must be {op} {minimum}")


@dataclass
class Node:
    """A supply-chain facility and its normal throughput characteristics."""
    id: str
    type: NodeType
    capacity: float
    load: float
    buffer_hours: float = 0.0
    critical: bool = False
    criticality_weight: float | None = None
    recovery_hours: float = 0.0
    unit_cost: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Node id cannot be empty")
        if self.type not in NODE_TYPES:
            raise ValueError(f"Invalid node type {self.type!r}; expected supplier, warehouse, or store")
        _number("capacity", self.capacity, strict=True)
        _number("load", self.load)
        _number("buffer_hours", self.buffer_hours)
        _number("recovery_hours", self.recovery_hours)
        if not isinstance(self.critical, bool):
            raise ValueError("critical must be a boolean")
        if self.criticality_weight is None:
            self.criticality_weight = 3.0 if self.critical else 1.0
        _number("criticality_weight", self.criticality_weight, strict=True)
        if self.unit_cost is not None:
            _number("unit_cost", self.unit_cost)


@dataclass
class Edge:
    """Directed supply connection; share describes destination demand allocation."""
    src: str
    dst: str
    share: float
    delay_h: float
    capacity: float
    reliability: float = 1.0
    is_alt: bool = False

    def __post_init__(self) -> None:
        if not self.src or not self.dst:
            raise ValueError("Edge source and destination IDs cannot be empty")
        if self.src == self.dst:
            raise ValueError("Self-loop edges are not allowed")
        _number("share", self.share)
        if self.share > 1:
            raise ValueError("share must be between 0 and 1")
        _number("delay_h", self.delay_h)
        _number("capacity", self.capacity)
        _number("reliability", self.reliability)
        if self.reliability > 1:
            raise ValueError("reliability must be between 0 and 1")
        if not isinstance(self.is_alt, bool):
            raise ValueError("is_alt must be a boolean")


@dataclass
class SupplyNetwork:
    """Validated directed acyclic supply network backed by a NetworkX graph."""
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    _graph: nx.DiGraph = field(default_factory=nx.DiGraph, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        initial_nodes, initial_edges = list(self.nodes.values()), list(self.edges)
        self.nodes, self.edges = {}, []
        self._graph = nx.DiGraph()
        for node in initial_nodes:
            self.add_node(node)
        for edge in initial_edges:
            self.add_edge(edge)
        self.validate()

    @property
    def graph(self) -> nx.DiGraph:
        """Return a defensive copy of the internal graph."""
        return self._graph.copy()

    def add_node(self, node: Node) -> None:
        if node.id in self.nodes:
            raise ValueError(f"Duplicate node ID: {node.id}")
        self.nodes[node.id] = node
        self._graph.add_node(node.id, node=node)

    def remove_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            raise ValueError(f"Unknown node: {node_id}")
        self._graph.remove_node(node_id)
        del self.nodes[node_id]
        self.edges = [e for e in self.edges if e.src != node_id and e.dst != node_id]

    def add_edge(self, edge: Edge) -> None:
        if edge.src not in self.nodes or edge.dst not in self.nodes:
            missing = [n for n in (edge.src, edge.dst) if n not in self.nodes]
            raise ValueError(f"Edge references missing node(s): {', '.join(missing)}")
        if self._graph.has_edge(edge.src, edge.dst):
            raise ValueError(f"Duplicate edge: {edge.src} -> {edge.dst}")
        self._graph.add_edge(edge.src, edge.dst, edge=edge)
        if not nx.is_directed_acyclic_graph(self._graph):
            self._graph.remove_edge(edge.src, edge.dst)
            raise ValueError("Supply network must be acyclic")
        self.edges.append(edge)

    def remove_edge(self, src: str, dst: str) -> None:
        if not self._graph.has_edge(src, dst):
            raise ValueError(f"Unknown edge: {src} -> {dst}")
        self._graph.remove_edge(src, dst)
        self.edges = [e for e in self.edges if (e.src, e.dst) != (src, dst)]

    def validate(self) -> None:
        if not nx.is_directed_acyclic_graph(self._graph):
            raise ValueError("Supply network must be acyclic")
        for edge in self.edges:
            if edge.src not in self.nodes or edge.dst not in self.nodes:
                raise ValueError(f"Edge references missing node: {edge.src} -> {edge.dst}")

    def copy(self) -> "SupplyNetwork":
        """Return a fully independent network copy."""
        return copy.deepcopy(self)

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": [asdict(n) for n in self.nodes.values()], "edges": [asdict(e) for e in self.edges]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SupplyNetwork":
        try:
            nodes = [Node(**item) for item in data["nodes"]]
            edges = [Edge(**item) for item in data["edges"]]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Invalid network data: {exc}") from exc
        network = cls()
        for node in nodes:
            network.add_node(node)
        for edge in edges:
            network.add_edge(edge)
        return network
