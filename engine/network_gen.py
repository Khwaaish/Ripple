from engine.models import Edge, Node, SupplyNetwork


def create_sample_network() -> SupplyNetwork:
    """Build the fixed 12-node demo supply network."""
    nodes = [
        Node("S1", "supplier", 150, 115), Node("S2", "supplier", 120, 100), Node("S3", "supplier", 100, 75),
        Node("WH1", "warehouse", 110, 100, 8, recovery_hours=24),
        Node("WH2", "warehouse", 130, 105, 12, recovery_hours=18),
        Node("WH3", "warehouse", 100, 70, 6, recovery_hours=20),
        Node("ST1", "store", 35, 30, 4, True, recovery_hours=8), Node("ST2", "store", 30, 24, 8),
        Node("ST3", "store", 32, 27, 3), Node("ST4", "store", 28, 22, 10, True, recovery_hours=6),
        Node("ST5", "store", 25, 20, 5), Node("ST6", "store", 30, 25, 12),
    ]
    edges = [
        Edge("S1", "WH1", .7, 2, 80), Edge("S2", "WH1", .3, 3, 40, is_alt=True),
        Edge("S2", "WH2", .65, 2, 90), Edge("S3", "WH2", .35, 4, 50, is_alt=True),
        Edge("S1", "WH3", .35, 3, 40), Edge("S3", "WH3", .65, 2, 70),
        Edge("WH1", "ST1", .7, 1, 30), Edge("WH2", "ST1", .3, 2, 20, is_alt=True),
        Edge("WH1", "ST2", 1, 1, 30), Edge("WH2", "ST3", .7, 1, 30), Edge("WH3", "ST3", .3, 2, 15, is_alt=True),
        Edge("WH2", "ST4", 1, 1, 28), Edge("WH3", "ST5", .6, 1, 20), Edge("WH2", "ST5", .4, 2, 15, is_alt=True),
        Edge("WH3", "ST6", .7, 1, 25), Edge("WH1", "ST6", .3, 2, 15, is_alt=True),
    ]
    return SupplyNetwork({n.id: n for n in nodes}, edges)


def create_network(nodes: list[Node], edges: list[Edge]) -> SupplyNetwork:
    """Create a validated network from caller supplied nodes and edges."""
    network = SupplyNetwork()
    for node in nodes:
        network.add_node(node)
    for edge in edges:
        network.add_edge(edge)
    return network
