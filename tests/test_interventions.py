from engine.interventions import compare_interventions
from engine.models import Edge, Node, SupplyNetwork
from engine.simulate import simulate


def make(nodes, edges):
    n = SupplyNetwork()
    for x in nodes: n.add_node(x)
    for x in edges: n.add_edge(x)
    return n

def base():
    return make([Node("W", "warehouse", 20, 10), Node("A", "store", 10, 8)], [Edge("W", "A", 1, 1, 8)])

def test_all_strategies_run():
    comp = compare_interventions(base(), ["W"])
    assert set(comp.scenarios) == {"none", "reroute", "backup_supplier", "prioritize"}

def test_backup_activation_delay_limits_coverage():
    n = make([Node("W", "warehouse", 20, 10), Node("A", "store", 10, 8)], [Edge("W", "A", 1, 1, 8)])
    delayed = simulate(n, ["W"], "backup_supplier", backup_capacity=8, activation_delay_h=12)
    ready = simulate(n, ["W"], "backup_supplier", backup_capacity=8, activation_delay_h=0)
    assert delayed.node_impacts["A"]["shortage"] > ready.node_impacts["A"]["shortage"]

def test_backup_has_finite_capacity_and_cost():
    n = make([Node("W", "warehouse", 20, 10), Node("A", "store", 10, 8)], [Edge("W", "A", 1, 1, 8)])
    r = simulate(n, ["W"], "backup_supplier", backup_capacity=2, activation_delay_h=0, operational_cost=7)
    assert r.node_impacts["A"]["shortage"] == 6
    assert r.intervention_cost == 7

def test_prioritize_critical_destination_first():
    n = make([Node("F", "warehouse", 20, 10), Node("ALT", "warehouse", 12, 10), Node("C", "store", 10, 8, critical=True), Node("N", "store", 10, 8)],
             [Edge("F", "C", .5, 1, 4), Edge("F", "N", .5, 1, 4), Edge("ALT", "C", .5, 1, 4, is_alt=True), Edge("ALT", "N", .5, 1, 4, is_alt=True)])
    r = simulate(n, ["F"], "prioritize")
    assert r.node_impacts["C"]["shortage"] <= r.node_impacts["N"]["shortage"]

def test_reroute_can_create_alternate_capacity_pressure():
    n = make([Node("F", "warehouse", 20, 10), Node("ALT", "warehouse", 12, 10), Node("C", "store", 10, 8), Node("OTHER", "store", 10, 8)],
             [Edge("F", "C", .5, 1, 4), Edge("ALT", "C", .5, 1, 4, is_alt=True), Edge("ALT", "OTHER", 1, 1, 8)])
    r = simulate(n, ["F"], "reroute")
    assert "ALT" in r.overloaded_nodes

def test_rerouting_pressure_causes_a_secondary_shortage():
    n = make([Node("F", "warehouse", 20, 10), Node("ALT", "warehouse", 12, 10),
              Node("A", "store", 10, 8), Node("B", "store", 10, 8)],
             [Edge("F", "A", .5, 1, 4), Edge("ALT", "A", .5, 1, 4, is_alt=True),
              Edge("ALT", "B", 1, 1, 8)])
    baseline = simulate(n, ["F"], "none")
    routed = simulate(n, ["F"], "reroute")
    assert routed.node_impacts["B"]["shortage"] > baseline.node_impacts["B"]["shortage"]
    assert "B" in routed.second_order_impacted_nodes

def test_recommendation_is_deterministic_and_schema_stable():
    n = base()
    first, second = compare_interventions(n, ["W"]), compare_interventions(n, ["W"])
    assert first.to_dict() == second.to_dict()
    expected = {"impact_score", "nodes_disrupted", "critical_shortages", "overloaded_nodes", "estimated_recovery_time_h", "intervention_cost", "relative_impact_vs_baseline", "reasoning", "node_impacts"}
    assert set(first.scenarios["none"]) == expected
    assert first.recommended_strategy == first.ranking[0]
