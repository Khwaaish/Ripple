import pytest
from engine.models import Edge, Node, SupplyNetwork


def test_valid_node_defaults():
    n = Node("n", "store", 10, 2, critical=True)
    assert n.criticality_weight == 3

@pytest.mark.parametrize("kwargs", [{"capacity": 0}, {"load": -1}, {"buffer_hours": -1}, {"id": " "}, {"type": "factory"}, {"criticality_weight": 0}])
def test_invalid_node(kwargs):
    args = dict(id="n", type="store", capacity=10, load=2)
    args.update(kwargs)
    with pytest.raises(ValueError): Node(**args)

def test_invalid_share():
    with pytest.raises(ValueError): Edge("a", "b", 1.1, 0, 1)

def test_invalid_reliability():
    with pytest.raises(ValueError): Edge("a", "b", .5, 0, 1, 1.1)

def test_missing_edge_node():
    network = SupplyNetwork()
    network.add_node(Node("a", "supplier", 10, 1))
    with pytest.raises(ValueError, match="missing node"):
        network.add_edge(Edge("a", "b", 1, 0, 2))

def test_duplicate_nodes():
    network = SupplyNetwork()
    network.add_node(Node("a", "supplier", 10, 1))
    with pytest.raises(ValueError, match="Duplicate"):
        network.add_node(Node("a", "store", 10, 1))

def test_duplicate_edges_and_cycles():
    network = SupplyNetwork()
    for n in [Node("a", "supplier", 10, 1), Node("b", "store", 10, 1)]: network.add_node(n)
    network.add_edge(Edge("a", "b", 1, 0, 2))
    with pytest.raises(ValueError, match="Duplicate"): network.add_edge(Edge("a", "b", 1, 0, 2))
    with pytest.raises(ValueError, match="acyclic"): network.add_edge(Edge("b", "a", 1, 0, 2))

def test_roundtrip():
    network = SupplyNetwork()
    network.add_node(Node("a", "supplier", 10, 1))
    network.add_node(Node("b", "store", 10, 1))
    network.add_edge(Edge("a", "b", .5, 1, 2))
    restored = SupplyNetwork.from_dict(network.to_dict())
    assert restored.to_dict() == network.to_dict()
