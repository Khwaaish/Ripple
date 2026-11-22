from engine.models import Edge, Node, SupplyNetwork
from engine.simulate import simulate


def net(nodes, edges):
    n = SupplyNetwork()
    for node in nodes: n.add_node(node)
    for edge in edges: n.add_edge(edge)
    return n

def test_failed_supplier_without_consumers_has_zero_impact():
    n = net([Node("S", "supplier", 10, 5)], [])
    r = simulate(n, ["S"])
    assert not r.all_impacted_nodes and r.impact_score == 0

def test_direct_failure_only_affects_connected_stores():
    n = net([Node("S", "supplier", 20, 10), Node("W", "warehouse", 20, 10), Node("A", "store", 10, 8), Node("B", "store", 10, 6), Node("C", "store", 10, 4)],
            [Edge("S", "W", 1, 0, 10), Edge("W", "A", 1, 1, 8), Edge("W", "B", 1, 2, 6)])
    r = simulate(n, ["W"])
    assert r.directly_impacted_nodes == ["A", "B"]
    assert "C" not in r.all_impacted_nodes

def test_alternate_spare_capacity_covers_loss():
    n = net([Node("W1", "warehouse", 20, 10), Node("W2", "warehouse", 30, 10), Node("A", "store", 10, 8)],
            [Edge("W1", "A", .5, 1, 4), Edge("W2", "A", .5, 1, 4, is_alt=True)])
    baseline, routed = simulate(n, ["W1"]), simulate(n, ["W1"], "reroute")
    assert routed.node_impacts["A"]["shortage"] < baseline.node_impacts["A"]["shortage"]
    assert not routed.overloaded_nodes

def test_alternate_insufficient_capacity_marks_pressure_and_shortage():
    n = net([Node("W1", "warehouse", 20, 10), Node("W2", "warehouse", 12, 10), Node("A", "store", 10, 8), Node("B", "store", 10, 8)],
            [Edge("W1", "A", .5, 1, 4), Edge("W2", "A", .5, 1, 4, is_alt=True), Edge("W2", "B", 1, 1, 8)])
    r = simulate(n, ["W1"], "reroute")
    assert "W2" in r.overloaded_nodes
    assert r.node_impacts["A"]["shortage"] > 0

def test_critical_store_weighting():
    nodes = [Node("W", "warehouse", 30, 20), Node("C", "store", 10, 8, critical=True), Node("N", "store", 10, 8)]
    edges = [Edge("W", "C", 1, 1, 8), Edge("W", "N", 1, 1, 8)]
    r = simulate(net(nodes, edges), ["W"])
    assert "C" in r.critical_shortage_nodes
    assert r.node_impacts["C"]["shortage"] == r.node_impacts["N"]["shortage"]
    assert r.impact_score > .5

def test_edge_capacity_caps_loss():
    n = net([Node("W", "warehouse", 50, 40), Node("A", "store", 20, 10)], [Edge("W", "A", 1, 0, 3)])
    assert simulate(n, ["W"]).node_impacts["A"]["shortage"] == 3

def test_buffer_delays_predicted_stockout():
    n = net([Node("W", "warehouse", 30, 20), Node("A", "store", 10, 8, buffer_hours=4)], [Edge("W", "A", 1, 2, 8)])
    r = simulate(n, ["W"])
    assert r.all_impacted_nodes == ["A"]
    assert r.first_predicted_stockout_time_h == 6

def test_delay_sets_stockout_time():
    n = net([Node("W", "warehouse", 30, 20), Node("A", "store", 10, 8)], [Edge("W", "A", 1, 5, 8)])
    assert simulate(n, ["W"]).first_predicted_stockout_time_h == 5

def test_network_is_not_mutated():
    n = net([Node("W", "warehouse", 30, 20), Node("A", "store", 10, 8)], [Edge("W", "A", 1, 2, 8)])
    before = n.to_dict()
    simulate(n, ["W"], "reroute")
    assert n.to_dict() == before

def test_deterministic_results():
    n = net([Node("W", "warehouse", 30, 20), Node("A", "store", 10, 8)], [Edge("W", "A", 1, 2, 8)])
    assert simulate(n, ["W"]).to_dict() == simulate(n, ["W"]).to_dict()

def test_unknown_failed_node_is_error():
    n = net([Node("W", "warehouse", 30, 20)], [])
    try: simulate(n, ["missing"])
    except ValueError as exc: assert "Unknown" in str(exc)
    else: assert False
