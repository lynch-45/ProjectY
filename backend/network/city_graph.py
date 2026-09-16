import networkx as nx


def asset(
    node_id, node_type, name, x, y, capacity=100, load=50,
    criticality=0.5, zone="Central", service=None
):
    return {
        "id": node_id,
        "type": node_type,
        "name": name,
        "x": x,
        "y": y,
        "capacity": capacity,
        "current_load": load,
        "status": "operational",
        "criticality": criticality,
        "zone": zone,
        "service": service,
    }


def build_city():
    g = nx.DiGraph()

    # Synthetic city layout: approximately 40 assets.
    data = [
        asset("S1", "substation", "Substation S1", 18, 78, 120, 72, .90, "North"),
        asset("S2", "substation", "Substation S2", 50, 84, 120, 70, .90, "North"),
        asset("S3", "substation", "Substation S3", 82, 76, 120, 68, .90, "East"),
        asset("S4", "substation", "Substation S4", 52, 38, 120, 75, .98, "Central"),

        asset("B1", "bridge", "Bridge B1", 35, 52, 100, 62, .90, "Central"),
        asset("B2", "bridge", "Bridge B2", 67, 52, 100, 58, .90, "East"),

        asset("P1", "pump", "Water Pump P1", 24, 28, 100, 72, .85, "South", "water"),
        asset("P2", "pump", "Water Pump P2", 76, 25, 100, 70, .85, "South", "water"),
        asset("P3", "pump", "Water Pump P3", 50, 16, 100, 63, .80, "South", "water"),

        asset("H1", "hospital", "Hospital H1", 23, 63, 100, 55, .98, "North", "health"),
        asset("H2", "hospital", "Hospital H2", 74, 62, 100, 62, .99, "East", "health"),
        asset("H3", "hospital", "Hospital H3", 49, 70, 100, 50, .95, "North", "health"),

        asset("E1", "emergency", "Emergency Base E1", 20, 45, 80, 45, .90, "West", "emergency"),
        asset("E2", "emergency", "Emergency Base E2", 80, 46, 80, 48, .90, "East", "emergency"),
        asset("E3", "emergency", "Emergency Base E3", 50, 27, 80, 42, .90, "South", "emergency"),

        asset("T1", "signal", "Traffic Signal T1", 28, 57, 100, 50, .60, "North"),
        asset("T2", "signal", "Traffic Signal T2", 45, 58, 100, 58, .65, "Central"),
        asset("T3", "signal", "Traffic Signal T3", 62, 58, 100, 60, .65, "Central"),
        asset("T4", "signal", "Traffic Signal T4", 44, 40, 100, 65, .75, "Central"),
        asset("T5", "signal", "Traffic Signal T5", 62, 39, 100, 67, .75, "Central"),
        asset("T6", "signal", "Traffic Signal T6", 76, 48, 100, 55, .65, "East"),

        asset("R1", "road", "Road R1", 28, 50, 100, 62, .65, "West"),
        asset("R2", "road", "Road R2", 42, 50, 100, 68, .70, "Central"),
        asset("R3", "road", "Road R3", 56, 50, 100, 72, .82, "Central"),
        asset("R4", "road", "Road R4", 70, 50, 100, 60, .72, "East"),
        asset("R5", "road", "Road R5", 50, 72, 100, 66, .72, "North"),
        asset("R6", "road", "Road R6", 50, 58, 100, 63, .72, "Central"),
        asset("R7", "road", "Road R7", 50, 43, 100, 61, .72, "Central"),
        asset("R8", "road", "Road R8", 50, 30, 100, 65, .72, "South"),
        asset("R9", "road", "Road R9", 30, 35, 100, 58, .68, "South"),
        asset("R10", "road", "Road R10", 70, 34, 100, 64, .75, "East"),
        asset("R11", "road", "Road R11", 35, 65, 100, 55, .70, "North"),
        asset("R12", "road", "Road R12", 65, 65, 100, 59, .70, "East"),

        asset("Z1", "zone", "Residential Zone A", 18, 20, 100, 50, .55, "South"),
        asset("Z2", "zone", "Residential Zone B", 82, 20, 100, 54, .55, "South"),
        asset("Z3", "zone", "Commercial Zone", 50, 88, 100, 65, .60, "North"),
        asset("F1", "facility", "Logistics Facility", 86, 55, 100, 48, .70, "East"),
        asset("F2", "facility", "Industrial Facility", 14, 55, 100, 52, .75, "West"),
        asset("W1", "water", "Water Reservoir", 50, 8, 120, 72, .75, "South", "water"),
        asset("C1", "control", "City Control Center", 50, 92, 100, 45, .90, "North"),
        asset("C2", "control", "Emergency Dispatch", 50, 22, 100, 55, .95, "South", "emergency"),
    ]

    for item in data:
        g.add_node(item["id"], data=item)

    # Road topology.
    road_links = [
        ("R1", "R2"), ("R2", "R3"), ("R3", "R4"),
        ("R5", "R6"), ("R6", "R7"), ("R7", "R8"),
        ("R9", "R1"), ("R9", "R8"),
        ("R10", "R4"), ("R10", "R8"),
        ("R11", "R1"), ("R11", "R5"),
        ("R12", "R4"), ("R12", "R5"),
        ("B1", "R2"), ("B1", "R6"),
        ("B2", "R3"), ("B2", "R7"),
    ]
    for u, v in road_links:
        g.add_edge(u, v, kind="road")

    # Dependency links. Direction means "u affects v".
    deps = [
        ("S1", "T1"), ("S1", "T2"), ("S2", "T2"), ("S2", "T3"),
        ("S4", "T4"), ("S4", "T5"), ("S3", "T6"),
        ("S1", "H1"), ("S4", "H2"), ("S2", "H3"),
        ("S4", "P1"), ("S3", "P2"), ("S4", "P3"),
        ("S4", "C2"), ("S1", "C1"),

        ("T1", "R1"), ("T2", "R2"), ("T3", "R3"),
        ("T4", "R7"), ("T5", "R3"), ("T6", "R4"),

        ("B1", "R2"), ("B1", "R6"), ("B2", "R3"), ("B2", "R7"),

        ("R2", "H1"), ("R3", "H2"), ("R5", "H3"),
        ("R1", "E1"), ("R4", "E2"), ("R8", "E3"),
        ("R9", "Z1"), ("R10", "Z2"), ("R5", "Z3"),
        ("R4", "F1"), ("R1", "F2"),

        ("P1", "W1"), ("P2", "W1"), ("P3", "W1"),
        ("W1", "Z1"), ("W1", "Z2"),
    ]
    for u, v in deps:
        g.add_edge(u, v, kind="dependency")

    return g
