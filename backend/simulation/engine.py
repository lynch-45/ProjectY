from copy import deepcopy
import heapq

from simulation.rules import INCIDENT_START_RULES
from simulation.metrics import calculate_metrics


# ---------------------------------------------------------------------
# STATUS LOGIC
# ---------------------------------------------------------------------

def _status(load, capacity):
    if capacity <= 0:
        return "failed"

    utilization = load / capacity

    if utilization <= 0.75:
        return "operational"
    if utilization <= 0.90:
        return "degraded"
    if utilization <= 1.05:
        return "critical"
    if utilization <= 1.25:
        return "near_failure"

    return "failed"


# ---------------------------------------------------------------------
# NODE SNAPSHOT
# ---------------------------------------------------------------------

def _node_snapshot(node):
    return {
        "id": node["id"],
        "name": node["name"],
        "type": node["type"],
        "x": node["x"],
        "y": node["y"],
        "capacity": node["capacity"],
        "current_load": round(node["current_load"], 2),
        "baseline_load": round(
            node.get("baseline_load", node["current_load"]),
            2
        ),
        "status": node["status"],
        "criticality": node["criticality"],
        "zone": node["zone"],
        "service": node.get("service"),
    }


# ---------------------------------------------------------------------
# INTERVENTIONS
# ---------------------------------------------------------------------

def _apply_interventions(nodes, interventions):
    interventions = interventions or []

    if "road_capacity" in interventions:
        roads = [
            n for n in nodes.values()
            if n["type"] == "road"
        ]

        roads.sort(
            key=lambda n: n["current_load"] / max(n["capacity"], 1),
            reverse=True
        )

        for road in roads[:2]:
            road["capacity"] *= 1.25

    if "backup_hospital_power" in interventions:
        for node in nodes.values():
            if node["type"] == "hospital":
                node["hospital_backup"] = True

    if "backup_signal_power" in interventions:
        for node in nodes.values():
            if node["type"] == "signal":
                node["signal_backup"] = True

    if "emergency_route" in interventions:
        for node in nodes.values():
            if node["type"] == "emergency":
                node["emergency_route"] = True

    if "pump_redundancy" in interventions:
        for node in nodes.values():
            if node["type"] == "pump":
                node["pump_backup"] = True


# ---------------------------------------------------------------------
# IMPACT RULES
# ---------------------------------------------------------------------

def _impact_factor(
    incident_type,
    source_type,
    target_type,
    source_status,
    target_node,
):
    # -------------------------------------------------------------
    # POWER FAILURE
    # -------------------------------------------------------------

    if incident_type == "power_failure":

        table = {
            ("substation", "signal"): 1.00,
            ("substation", "pump"): 0.65,
            ("substation", "hospital"): 0.45,
            ("substation", "control"): 0.40,

            ("signal", "road"): 0.42,

            ("road", "road"): 0.45,
            ("road", "emergency"): 0.30,
            ("road", "hospital"): 0.30,
            ("road", "facility"): 0.24,
            ("road", "zone"): 0.20,

            ("hospital", "emergency"): 0.20,
            ("emergency", "facility"): 0.18,
        }

        factor = table.get(
            (source_type, target_type),
            0.05
        )

        if (
            source_type == "substation"
            and target_type == "signal"
            and target_node.get("signal_backup")
        ):
            return 0.0

        if (
            source_type == "substation"
            and target_type == "hospital"
            and target_node.get("hospital_backup")
        ):
            return 0.0

        return factor

    # -------------------------------------------------------------
    # FLOOD
    # -------------------------------------------------------------

    if incident_type == "flood":

        table = {
            ("road", "road"): 0.45,
            ("road", "hospital"): 0.25,
            ("road", "emergency"): 0.30,
            ("road", "facility"): 0.22,
            ("road", "zone"): 0.20,

            ("pump", "water"): 0.50,
            ("water", "zone"): 0.30,

            ("substation", "signal"): 0.35,
            ("substation", "hospital"): 0.25,
        }

        factor = table.get(
            (source_type, target_type),
            0.05
        )

        if (
            source_type == "pump"
            and target_type == "water"
            and target_node.get("pump_backup")
        ):
            return 0.0

        return factor

    # -------------------------------------------------------------
    # ACCIDENT
    # -------------------------------------------------------------

    if incident_type == "accident":

        table = {
            ("road", "road"): 0.50,
            ("road", "hospital"): 0.25,
            ("road", "emergency"): 0.30,
            ("road", "facility"): 0.22,
            ("road", "zone"): 0.20,
        }

        return table.get(
            (source_type, target_type),
            0.05
        )

    # -------------------------------------------------------------
    # BRIDGE FAILURE
    # -------------------------------------------------------------

    if incident_type == "bridge_failure":

        table = {
            ("bridge", "road"): 0.65,
            ("road", "road"): 0.45,
            ("road", "hospital"): 0.25,
            ("road", "emergency"): 0.30,
            ("road", "facility"): 0.22,
            ("road", "zone"): 0.20,
        }

        return table.get(
            (source_type, target_type),
            0.05
        )

    # -------------------------------------------------------------
    # FIRE
    # -------------------------------------------------------------

    if incident_type == "fire":

        table = {
            ("facility", "road"): 0.40,
            ("road", "road"): 0.40,
            ("road", "emergency"): 0.30,
            ("road", "hospital"): 0.25,
            ("road", "zone"): 0.25,
        }

        return table.get(
            (source_type, target_type),
            0.05
        )

    return 0.05


# ---------------------------------------------------------------------
# PROPAGATION DELAY
# ---------------------------------------------------------------------

def _propagation_delay(source_type, target_type):
    delays = {
        ("substation", "signal"): 6,
        ("substation", "pump"): 8,
        ("substation", "hospital"): 9,
        ("substation", "control"): 7,

        ("signal", "road"): 5,

        ("bridge", "road"): 7,

        ("pump", "water"): 8,
        ("water", "zone"): 10,

        ("road", "hospital"): 7,
        ("road", "emergency"): 6,
        ("road", "facility"): 8,
        ("road", "zone"): 9,

        ("hospital", "emergency"): 8,
        ("emergency", "facility"): 9,

        ("road", "road"): 4,
    }

    return delays.get(
        (source_type, target_type),
        6
    )


# ---------------------------------------------------------------------
# INCIDENT SEED
# ---------------------------------------------------------------------

def _incident_seed(node, incident_type, severity):
    rules = INCIDENT_START_RULES.get(
        incident_type,
        {}
    )

    pressure = rules.get(
        node["type"],
        0.0
    )

    if pressure <= 0:
        return False

    node["current_load"] = (
        node["capacity"]
        * (
            1.0
            + 0.55
            * severity
            * pressure
        )
    )

    node["status"] = "failed"

    return True


# ---------------------------------------------------------------------
# ROAD REROUTING
# ---------------------------------------------------------------------

def _reroute_roads(nodes, severity):
    roads = [
        n for n in nodes.values()
        if n["type"] == "road"
    ]

    stressed = [
        n for n in roads
        if n["status"] in (
            "failed",
            "near_failure",
            "critical"
        )
    ]

    if not stressed:
        return []

    operational = [
        n for n in roads
        if n["status"] == "operational"
    ]

    if not operational:
        return []

    operational.sort(
        key=lambda n: n["current_load"] / max(n["capacity"], 1)
    )

    changed = []

    for road in stressed:

        if road["status"] == "failed":
            transfer_ratio = 0.28
        elif road["status"] == "near_failure":
            transfer_ratio = 0.18
        else:
            transfer_ratio = 0.10

        transfer = (
            road["current_load"]
            * transfer_ratio
            * severity
        )

        share = transfer / max(
            len(operational[:2]),
            1
        )

        for target in operational[:2]:

            before = target["current_load"]

            target["current_load"] += share

            previous_status = target["status"]

            target["status"] = _status(
                target["current_load"],
                target["capacity"]
            )

            if target["status"] != previous_status:
                changed.append(
                    {
                        "id": target["id"],
                        "before_load": before,
                        "after_load": target["current_load"],
                        "previous_status": previous_status,
                        "status": target["status"],
                    }
                )

    failed_signals = [
        n for n in nodes.values()
        if n["type"] == "signal"
        and n["status"] == "failed"
    ]

    signal_pressure = (
        3.0
        * len(failed_signals)
        * severity
    )

    if signal_pressure > 0:

        for road in operational[:2]:

            before = road["current_load"]

            road["current_load"] += signal_pressure

            previous_status = road["status"]

            road["status"] = _status(
                road["current_load"],
                road["capacity"]
            )

            if road["status"] != previous_status:
                changed.append(
                    {
                        "id": road["id"],
                        "before_load": before,
                        "after_load": road["current_load"],
                        "previous_status": previous_status,
                        "status": road["status"],
                    }
                )

    return changed


# ---------------------------------------------------------------------
# EVENT CREATION
# ---------------------------------------------------------------------

def _event(
    time,
    node,
    previous_status,
    reason,
    parent_id,
    depth,
    load_before,
    cause_type=None,
    impact_factor=None,
    added_load=None,
    mechanism=None,
):
    utilization = (
        node["current_load"]
        / max(node["capacity"], 1)
        * 100
    )

    return {
        "time": round(time, 2),

        "node_id": node["id"],
        "node_name": node["name"],
        "node_type": node["type"],

        "status": node["status"],
        "previous_status": previous_status,

        "reason": reason,

        "parent_id": parent_id,
        "depth": depth,

        "load_before": round(
            load_before,
            2
        ),

        "load_after": round(
            node["current_load"],
            2
        ),

        "load_change": round(
            node["current_load"] - load_before,
            2
        ),

        "capacity": round(
            node["capacity"],
            2
        ),

        "utilization": round(
            utilization,
            1
        ),

        "cause_type": cause_type,

        "impact_factor": (
            round(impact_factor, 3)
            if isinstance(
                impact_factor,
                (int, float)
            )
            else None
        ),

        "added_load": (
            round(added_load, 2)
            if isinstance(
                added_load,
                (int, float)
            )
            else None
        ),

        "mechanism": mechanism,
    }


# ---------------------------------------------------------------------
# EVENT EXPLANATION
# ---------------------------------------------------------------------

def _build_event_explanation(
    parent,
    target,
    previous_status,
    new_status,
    added_load,
    factor,
):
    source_name = parent["name"]
    target_name = target["name"]

    source_type = parent["type"]
    target_type = target["type"]

    utilization = (
        target["current_load"]
        / max(target["capacity"], 1)
        * 100
    )

    mechanism_map = {
        ("substation", "signal"):
            "Loss of electrical supply reduced traffic-signal availability.",

        ("substation", "pump"):
            "Loss of electrical supply reduced water-pump operating capacity.",

        ("substation", "hospital"):
            "Loss of electrical supply reduced hospital support capacity.",

        ("substation", "control"):
            "Loss of electrical supply reduced control-system capacity.",

        ("signal", "road"):
            "Traffic-signal disruption increased pressure on the connected road corridor.",

        ("road", "road"):
            "Traffic was redistributed onto an alternative road corridor.",

        ("road", "hospital"):
            "Reduced road capacity increased pressure on hospital accessibility.",

        ("road", "emergency"):
            "Reduced road capacity increased emergency-route pressure.",

        ("road", "facility"):
            "Reduced road capacity increased access pressure around the facility.",

        ("road", "zone"):
            "Reduced road capacity increased access pressure for the zone.",

        ("bridge", "road"):
            "Bridge loss redirected traffic onto connected road corridors.",

        ("pump", "water"):
            "Pump disruption reduced water-system operating capacity.",

        ("water", "zone"):
            "Reduced water-system capacity increased service pressure in the zone.",

        ("hospital", "emergency"):
            "Hospital disruption increased pressure on emergency services.",

        ("emergency", "facility"):
            "Emergency-service pressure increased demand around the facility.",
    }

    mechanism = mechanism_map.get(
        (source_type, target_type),
        f"{source_name} propagated load pressure to {target_name}."
    )

    status_text = (
        f"{target_name} changed from "
        f"{previous_status.replace('_', ' ')} "
        f"to {new_status.replace('_', ' ')}."
    )

    load_text = (
        f"Load increased by {added_load:.1f} "
        f"to {target['current_load']:.1f} "
        f"against capacity {target['capacity']:.1f} "
        f"({utilization:.1f}% utilization)."
    )

    reason = (
        f"{mechanism} "
        f"{status_text} "
        f"{load_text}"
    )

    return {
        "reason": reason,
        "mechanism": mechanism,
        "status_change": status_text,
    }


# ---------------------------------------------------------------------
# MAIN SIMULATION
# ---------------------------------------------------------------------

def simulate(
    city,
    incident_type,
    asset_id,
    severity=1.0,
    duration=60,
    interventions=None,
):

    graph = city.copy()

    nodes = {
        node_id: deepcopy(
            graph.nodes[node_id]["data"]
        )
        for node_id in graph.nodes
    }

    interventions = interventions or []

    for node in nodes.values():
        node["baseline_load"] = node["current_load"]

    _apply_interventions(
        nodes,
        interventions
    )

    if asset_id not in nodes:
        raise ValueError(
            f"Unknown asset: {asset_id}"
        )

    if incident_type not in INCIDENT_START_RULES:
        raise ValueError(
            f"Unknown incident type: {incident_type}"
        )

    # -------------------------------------------------------------
    # INCIDENT
    # -------------------------------------------------------------

    root = nodes[asset_id]

    previous_status = root["status"]

    root_load_before = root["current_load"]

    if not _incident_seed(
        root,
        incident_type,
        severity
    ):
        raise ValueError(
            f"Incident type '{incident_type}' "
            f"cannot start on asset type '{root['type']}'"
        )

    events = []

    root_event = _event(
        time=0,
        node=root,
        previous_status=previous_status,
        reason=f"Initial {incident_type.replace('_', ' ')} incident.",
        parent_id=None,
        depth=0,
        load_before=root_load_before,
        cause_type="incident",
        impact_factor=1.0,
        added_load=root["current_load"] - root_load_before,
        mechanism="Initial incident applied to the selected asset.",
    )

    events.append(root_event)

    # -------------------------------------------------------------
    # EVENT QUEUE
    # -------------------------------------------------------------

    queue = []

    counter = 0

    for target_id in graph.successors(asset_id):

        target = nodes[target_id]

        delay = _propagation_delay(
            root["type"],
            target["type"]
        )

        heapq.heappush(
            queue,
            (
                delay,
                counter,
                target_id,
                asset_id,
                1
            )
        )

        counter += 1

    processed = set()

    # -------------------------------------------------------------
    # PROPAGATION
    # -------------------------------------------------------------

    while queue:

        (
            current_time,
            _,
            target_id,
            parent_id,
            depth
        ) = heapq.heappop(queue)

        if current_time > duration:
            continue

        target = nodes[target_id]

        parent = nodes[parent_id]

        process_key = (
            target_id,
            depth
        )

        if process_key in processed:
            continue

        processed.add(process_key)

        previous_status = target["status"]

        load_before = target["current_load"]

        source_type = parent["type"]
        target_type = target["type"]

        factor = _impact_factor(
            incident_type,
            source_type,
            target_type,
            parent["status"],
            target,
        )

        if parent["status"] == "failed":
            factor *= 1.25

        elif parent["status"] in (
            "critical",
            "near_failure"
        ):
            factor *= 1.15

        elif parent["status"] == "degraded":
            factor *= 1.08

        if (
            source_type == "road"
            and target_type == "road"
        ):
            factor *= 0.85

        # ---------------------------------------------------------
        # APPLY LOAD
        # ---------------------------------------------------------

        added_load = (
            parent["capacity"]
            * severity
            * factor
        )

        target["current_load"] += added_load

        # ---------------------------------------------------------
        # INTERVENTION PROTECTION
        # ---------------------------------------------------------

        if (
            target_type == "signal"
            and target.get("signal_backup")
            and source_type == "substation"
        ):
            target["current_load"] = min(
                target["current_load"],
                target["capacity"] * 0.95
            )

        if (
            target_type == "hospital"
            and target.get("hospital_backup")
            and source_type == "substation"
        ):
            target["current_load"] = min(
                target["current_load"],
                target["capacity"] * 0.90
            )

        if (
            target_type == "pump"
            and target.get("pump_backup")
        ):
            target["current_load"] = min(
                target["current_load"],
                target["capacity"] * 0.90
            )

        if (
            target_type == "emergency"
            and target.get("emergency_route")
        ):
            target["current_load"] *= 0.80

        target["status"] = _status(
            target["current_load"],
            target["capacity"]
        )

        # ---------------------------------------------------------
        # RECORD STATUS CHANGE
        # ---------------------------------------------------------

        if target["status"] != previous_status:

            explanation = _build_event_explanation(
                parent=parent,
                target=target,
                previous_status=previous_status,
                new_status=target["status"],
                added_load=target["current_load"] - load_before,
                factor=factor,
            )

            events.append(
                _event(
                    time=current_time,
                    node=target,
                    previous_status=previous_status,
                    reason=explanation["reason"],
                    parent_id=parent_id,
                    depth=depth,
                    load_before=load_before,
                    cause_type=source_type,
                    impact_factor=factor,
                    added_load=target["current_load"] - load_before,
                    mechanism=explanation["mechanism"],
                )
            )

        # ---------------------------------------------------------
        # CONTINUE CASCADE WHEN LOAD ACTUALLY PROPAGATES
        # ---------------------------------------------------------

        meaningful_propagation = (
            target["current_load"] > load_before + 0.5
        )

        if meaningful_propagation:

            for next_id in graph.successors(target_id):

                if next_id == parent_id:
                    continue

                next_node = nodes[next_id]

                next_delay = _propagation_delay(
                    target["type"],
                    next_node["type"]
                )

                heapq.heappush(
                    queue,
                    (
                        current_time + next_delay,
                        counter,
                        next_id,
                        target_id,
                        depth + 1
                    )
                )

                counter += 1

    # -------------------------------------------------------------
    # REROUTING AFTER CASCADE
    # -------------------------------------------------------------

    reroute_changes = _reroute_roads(
        nodes,
        severity
    )

    for change in reroute_changes:

        node = nodes[change["id"]]

        events.append(
            _event(
                time=min(duration, 20),
                node=node,
                previous_status=change["previous_status"],
                reason=(
                    f"Traffic rerouting increased pressure on "
                    f"{node['name']}. "
                    f"Load changed from "
                    f"{change['before_load']:.1f} to "
                    f"{change['after_load']:.1f} "
                    f"against capacity {node['capacity']:.1f}."
                ),
                parent_id=None,
                depth=3,
                load_before=change["before_load"],
                cause_type="rerouting",
                impact_factor=None,
                added_load=(
                    change["after_load"]
                    - change["before_load"]
                ),
                mechanism=(
                    "Traffic was redistributed from a stressed "
                    "road onto an alternative corridor."
                ),
            )
        )

    # -------------------------------------------------------------
    # FIRE-SPECIFIC EMERGENCY DEMAND
    # -------------------------------------------------------------

    if incident_type == "fire":

        emergency_nodes = [
            n for n in nodes.values()
            if n["type"] == "emergency"
        ]

        for emergency in emergency_nodes:

            if emergency["status"] == "operational":

                before = emergency["current_load"]

                emergency["current_load"] += (
                    8.0 * severity
                )

                previous_status = emergency["status"]

                emergency["status"] = _status(
                    emergency["current_load"],
                    emergency["capacity"]
                )

                if emergency["status"] != "operational":

                    events.append(
                        _event(
                            time=12,
                            node=emergency,
                            previous_status=previous_status,
                            reason=(
                                f"Fire increased emergency demand. "
                                f"{emergency['name']} changed from "
                                f"{previous_status} to "
                                f"{emergency['status']}."
                            ),
                            parent_id=asset_id,
                            depth=2,
                            load_before=before,
                            cause_type="fire_demand",
                            impact_factor=None,
                            added_load=(
                                emergency["current_load"]
                                - before
                            ),
                            mechanism=(
                                "Fire increased emergency-response "
                                "demand."
                            ),
                        )
                    )

    # -------------------------------------------------------------
    # NODE SNAPSHOTS
    # -------------------------------------------------------------

    node_list = [
        _node_snapshot(node)
        for node in nodes.values()
    ]

    # -------------------------------------------------------------
    # METRICS
    # -------------------------------------------------------------

    metrics = calculate_metrics(
        events,
        node_list,
        duration,
        interventions
    )

    # -------------------------------------------------------------
    # CAUSAL CHAINS
    # -------------------------------------------------------------

    event_by_id = {}

    for event in events:
        event_by_id.setdefault(
            event["node_id"],
            event
        )

    causal_chains = []

    for event in events:

        if event["depth"] <= 0:
            continue

        chain = []

        current = event

        visited = set()

        while current:

            node_id = current["node_id"]

            if node_id in visited:
                break

            visited.add(node_id)

            chain.append({
                "node_id": current["node_id"],
                "node_name": current["node_name"],
                "node_type": current.get("node_type"),
                "status": current["status"],
                "previous_status": current.get(
                    "previous_status"
                ),
                "time": current["time"],
                "reason": current.get("reason"),
                "mechanism": current.get("mechanism"),
                "load_before": current.get(
                    "load_before"
                ),
                "load_after": current.get(
                    "load_after"
                ),
                "capacity": current.get(
                    "capacity"
                ),
                "utilization": current.get(
                    "utilization"
                ),
            })

            parent_id = current.get("parent_id")

            if not parent_id:
                break

            current = event_by_id.get(
                parent_id
            )

        chain.reverse()

        if chain:
            causal_chains.append(chain)

    # Remove duplicate chains.
    unique_chains = []

    seen_chains = set()

    for chain in causal_chains:

        key = tuple(
            item["node_id"]
            for item in chain
        )

        if key not in seen_chains:

            seen_chains.add(key)

            unique_chains.append(chain)

    # -------------------------------------------------------------
    # DEBUG TRACE
    # -------------------------------------------------------------

    debug_trace = [
        {
            "time": event["time"],
            "node": event["node_id"],
            "node_type": event.get("node_type"),
            "status": event["status"],
            "previous_status": event.get(
                "previous_status"
            ),
            "depth": event["depth"],
            "parent": event["parent_id"],
            "reason": event["reason"],
            "mechanism": event.get(
                "mechanism"
            ),
            "load_before": event.get(
                "load_before"
            ),
            "load_after": event.get(
                "load_after"
            ),
            "capacity": event.get(
                "capacity"
            ),
            "utilization": event.get(
                "utilization"
            ),
            "added_load": event.get(
                "added_load"
            ),
            "impact_factor": event.get(
                "impact_factor"
            ),
        }
        for event in sorted(
            events,
            key=lambda e: (
                e["time"],
                e["depth"]
            )
        )
    ]

    # -------------------------------------------------------------
    # RESPONSE
    # -------------------------------------------------------------

    return {
        "scenario": {
            "incident_type": incident_type,
            "asset_id": asset_id,
            "severity": severity,
            "duration": duration,
            "interventions": interventions,
        },

        "nodes": node_list,

        "events": sorted(
            events,
            key=lambda e: (
                e["time"],
                e["depth"]
            )
        ),

        "metrics": metrics,

        "causal_chains": unique_chains,

        "debug_trace": debug_trace,

        "assumptions": [
            "Synthetic city network.",
            "Dependencies are represented as directed graph edges.",
            "Load propagation is deterministic.",
            "Road congestion is modeled through capacity utilization.",
            "Interventions modify selected dependency or capacity behavior.",
            "Cascade depth represents propagation levels through dependent assets.",
        ],
    }


# ---------------------------------------------------------------------
# REVERSE / ROOT-CAUSE ANALYSIS
# ---------------------------------------------------------------------

def find_root_causes(
    city,
    incident_type,
    target_asset_id,
    severity=1.0,
    duration=60,
):
    """
    Reverse cascade analysis.

    Starts from a target asset and walks backwards through the
    dependency graph. Every upstream asset is tested as a possible
    protection point by removing it from a copied network and
    rerunning the forward cascade.

    The result identifies:
    - the target outcome
    - upstream dependency paths
    - what happens without protection
    - what happens with protection
    - the strongest single protection point
    - a practical resilience action
    """

    if target_asset_id not in city:
        raise ValueError(
            f"Unknown target asset: {target_asset_id}"
        )

    if incident_type not in INCIDENT_START_RULES:
        raise ValueError(
            f"Unknown incident type: {incident_type}"
        )

    # -------------------------------------------------------------
    # STATUS SEVERITY
    # -------------------------------------------------------------

    status_level = {
        "operational": 0,
        "degraded": 1,
        "critical": 2,
        "near_failure": 3,
        "failed": 4,
    }

    def level(status):
        return status_level.get(
            status,
            0
        )

    def readable_status(status):
        return str(status).replace(
            "_",
            " "
        ).title()

    target_name = city.nodes[
        target_asset_id
    ]["data"]["name"]

    # -------------------------------------------------------------
    # FIND ALL UPSTREAM PATHS TO TARGET
    # -------------------------------------------------------------

    def upstream_paths(target_id):
        paths = []

        stack = [
            (
                target_id,
                [target_id]
            )
        ]

        visited_states = set()

        while stack:

            current_id, path = stack.pop()

            state = (
                current_id,
                tuple(path)
            )

            if state in visited_states:
                continue

            visited_states.add(state)

            predecessors = list(
                city.predecessors(
                    current_id
                )
            )

            if not predecessors:

                paths.append(
                    list(reversed(path))
                )

                continue

            for parent_id in predecessors:

                if parent_id in path:
                    continue

                stack.append(
                    (
                        parent_id,
                        path + [parent_id]
                    )
                )

        return paths

    all_paths = upstream_paths(
        target_asset_id
    )

    # -------------------------------------------------------------
    # POSSIBLE INCIDENT SOURCES
    # -------------------------------------------------------------

    seed_types = {
        asset_type
        for asset_type, pressure
        in INCIDENT_START_RULES[
            incident_type
        ].items()
        if pressure > 0
    }

    seed_ids = [
        node_id
        for node_id in city.nodes
        if city.nodes[node_id]["data"]["type"]
        in seed_types
    ]

    # -------------------------------------------------------------
    # ONLY KEEP PATHS THAT START AT A VALID INCIDENT SOURCE
    # -------------------------------------------------------------

    valid_paths = [
        path
        for path in all_paths
        if path
        and path[0] in seed_ids
    ]

    # -------------------------------------------------------------
    # IF NO FORMAL PATH EXISTS
    # -------------------------------------------------------------

    if not valid_paths:

        return {
            "target_asset_id":
                target_asset_id,

            "target_asset_name":
                target_name,

            "incident_type":
                incident_type,

            "severity":
                severity,

            "duration":
                duration,

            "solution": {
                "available":
                    False,

                "asset_id":
                    None,

                "asset_name":
                    None,

                "asset_type":
                    None,

                "action":
                    "No upstream dependency path found.",

                "target_status_before":
                    None,

                "target_status_after":
                    None,

                "path":
                    [],

                "explanation":
                    (
                        f"No upstream incident path from a "
                        f"valid {incident_type.replace('_', ' ')} "
                        f"source reaches {target_name}."
                    ),
            },

            "candidates":
                [],

            "root_causes":
                [],
        }

    # -------------------------------------------------------------
    # RUN A FORWARD SIMULATION FROM EVERY VALID SOURCE
    # -------------------------------------------------------------

    baseline_results = {}

    for path in valid_paths:

        seed_id = path[0]

        if seed_id in baseline_results:
            continue

        result = simulate(
            city,

            incident_type=
                incident_type,

            asset_id=
                seed_id,

            severity=
                severity,

            duration=
                duration,

            interventions=[],
        )

        target = next(
            (
                node
                for node in result["nodes"]
                if node["id"]
                == target_asset_id
            ),
            None
        )

        if target is None:
            continue

        baseline_results[
            seed_id
        ] = {
            "result":
                result,

            "status":
                target["status"],
        }

    # -------------------------------------------------------------
    # ONLY ANALYZE SOURCES WHERE TARGET IS ACTUALLY AFFECTED
    # -------------------------------------------------------------

    affected_sources = {
        seed_id: data
        for seed_id, data
        in baseline_results.items()
        if level(
            data["status"]
        ) >= 2
    }

    # If the target is not critical in this scenario,
    # return that honestly.
    if not affected_sources:

        current_status = (
            next(
                (
                    data["status"]
                    for data
                    in baseline_results.values()
                ),
                "operational"
            )
        )

        return {
            "target_asset_id":
                target_asset_id,

            "target_asset_name":
                target_name,

            "incident_type":
                incident_type,

            "severity":
                severity,

            "duration":
                duration,

            "solution": {
                "available":
                    False,

                "asset_id":
                    None,

                "asset_name":
                    None,

                "asset_type":
                    None,

                "action":
                    "No critical outcome detected.",

                "target_status_before":
                    current_status,

                "target_status_after":
                    current_status,

                "path":
                    [],

                "explanation":
                    (
                        f"{target_name} reaches "
                        f"{readable_status(current_status)} "
                        f"under the current scenario, so there "
                        f"is no critical outcome to reverse."
                    ),
            },

            "candidates":
                [],

            "root_causes":
                [],
        }

    # -------------------------------------------------------------
    # BUILD CANDIDATE LIST
    # -------------------------------------------------------------

    candidate_paths = {}

    for path in valid_paths:

        seed_id = path[0]

        if seed_id not in affected_sources:
            continue

        # Exclude the target itself.
        for index, node_id in enumerate(
            path[:-1]
        ):

            downstream_path = path[
                index:
            ]

            candidate_paths.setdefault(
                node_id,
                []
            ).append(
                downstream_path
            )

    # -------------------------------------------------------------
    # TEST EVERY UPSTREAM CANDIDATE
    # -------------------------------------------------------------

    candidates = []

    for candidate_id, paths in candidate_paths.items():

        candidate = city.nodes[
            candidate_id
        ]["data"]

        relevant_cases = 0
        prevented_cases = 0
        total_improvement = 0

        test_cases = []

        for seed_id, baseline in affected_sources.items():

            matching_paths = [
                path
                for path in paths
                if path[0] == seed_id
            ]

            if not matching_paths:
                continue

            relevant_cases += 1

            without_status = baseline[
                "status"
            ]

            # -----------------------------------------------------
            # PROTECTION TEST
            # -----------------------------------------------------

            if candidate_id == seed_id:

                # Protecting the incident source means the
                # initial incident never enters the network.
                with_status = "operational"

            else:

                protected_city = city.copy()

                if candidate_id in protected_city:

                    protected_city.remove_node(
                        candidate_id
                    )

                protected_result = simulate(
                    protected_city,

                    incident_type=
                        incident_type,

                    asset_id=
                        seed_id,

                    severity=
                        severity,

                    duration=
                        duration,

                    interventions=[],
                )

                protected_target = next(
                    (
                        node
                        for node
                        in protected_result["nodes"]
                        if node["id"]
                        == target_asset_id
                    ),
                    None
                )

                if protected_target is None:

                    with_status = "operational"

                else:

                    with_status = (
                        protected_target[
                            "status"
                        ]
                    )

            improvement = max(
                0,
                level(
                    without_status
                )
                -
                level(
                    with_status
                )
            )

            total_improvement += (
                improvement
            )

            prevented = (
                level(
                    with_status
                ) < 2
            )

            if prevented:
                prevented_cases += 1

            test_cases.append(
                {
                    "seed_id":
                        seed_id,

                    "without_protection":
                        without_status,

                    "with_protection":
                        with_status,

                    "prevented":
                        prevented,
                }
            )

        if relevant_cases == 0:
            continue

        # ---------------------------------------------------------
        # CHOOSE REPRESENTATIVE CASE
        # ---------------------------------------------------------

        representative_case = max(
            test_cases,

            key=lambda case:
                (
                    level(
                        case[
                            "without_protection"
                        ]
                    ),

                    level(
                        case[
                            "without_protection"
                        ]
                    )
                    -
                    level(
                        case[
                            "with_protection"
                        ]
                    ),
                )
        )

        representative_seed = (
            representative_case[
                "seed_id"
            ]
        )

        representative_paths = [
            path
            for path in paths
            if path[0]
            == representative_seed
        ]

        if not representative_paths:
            continue

        # Prefer the shortest dependency path.
        representative_path = min(
            representative_paths,
            key=len
        )

        # ---------------------------------------------------------
        # ACTION
        # ---------------------------------------------------------

        action_map = {

            "substation":
                (
                    "Protect this substation with resilient "
                    "backup power so it cannot become a "
                    "single point of failure."
                ),

            "signal":
                (
                    "Add backup traffic-signal power so "
                    "this signal remains operational during "
                    "a power disruption."
                ),

            "road":
                (
                    "Increase corridor capacity or create "
                    "an alternative emergency route."
                ),

            "bridge":
                (
                    "Create a redundant crossing or "
                    "alternative route around this bridge."
                ),

            "pump":
                (
                    "Add pump redundancy so downstream "
                    "water service remains available."
                ),

            "water":
                (
                    "Add water-system redundancy for "
                    "downstream service continuity."
                ),

            "hospital":
                (
                    "Add backup hospital power and "
                    "service redundancy."
                ),

            "emergency":
                (
                    "Add an alternative emergency route "
                    "and response capacity."
                ),

            "facility":
                (
                    "Add resilient facility access and "
                    "alternative service capacity."
                ),

            "control":
                (
                    "Add resilient backup power and "
                    "control-system redundancy."
                ),

            "zone":
                (
                    "Provide alternative service and "
                    "access capacity for this zone."
                ),
            }

        action = action_map.get(
            candidate["type"],
            (
                f"Protect {candidate['name']} "
                f"from becoming a single point of failure."
            )
        )

        protection_effective = (
            level(
                representative_case[
                    "with_protection"
                ]
            ) < 2
        )

        # ---------------------------------------------------------
        # EXPLANATION
        # ---------------------------------------------------------

        if protection_effective:

            explanation = (
                f"{candidate['name']} sits upstream of "
                f"{target_name}. Without protection, "
                f"{target_name} reaches "
                f"{readable_status(representative_case['without_protection'])}. "
                f"When {candidate['name']} is protected, "
                f"the target changes to "
                f"{readable_status(representative_case['with_protection'])}. "
                f"This breaks the simulated dependency chain "
                f"before it reaches the target."
            )

        else:

            explanation = (
                f"{candidate['name']} sits upstream of "
                f"{target_name}. Protecting it changes the "
                f"target from "
                f"{readable_status(representative_case['without_protection'])} "
                f"to "
                f"{readable_status(representative_case['with_protection'])}, "
                f"but another dependency path still keeps the "
                f"target at or above the critical threshold."
            )

        candidates.append(
            {
                "asset_id":
                    candidate_id,

                "asset_name":
                    candidate["name"],

                "asset_type":
                    candidate["type"],

                "path":
                    representative_path,

                "target_status_without_protection":
                    representative_case[
                        "without_protection"
                    ],

                "target_status_with_protection":
                    representative_case[
                        "with_protection"
                    ],

                "prevented_seed_cases":
                    prevented_cases,

                "relevant_seed_cases":
                    relevant_cases,

                "status_improvement":
                    total_improvement,

                "protection_effective":
                    protection_effective,

                "action":
                    action,

                "explanation":
                    explanation,

                "cases":
                    test_cases,
            }
        )

    # -------------------------------------------------------------
    # RANK
    # -------------------------------------------------------------

    candidates.sort(
        key=lambda item: (
            item[
                "protection_effective"
            ],

            item[
                "prevented_seed_cases"
            ],

            item[
                "status_improvement"
            ],

            item[
                "relevant_seed_cases"
            ],

            -len(
                item["path"]
            ),
        ),

        reverse=True,
    )

    for rank, candidate in enumerate(
        candidates,
        start=1
    ):

        candidate["rank"] = rank

    # -------------------------------------------------------------
    # BEST SOLUTION
    # -------------------------------------------------------------

    effective_candidates = [
        candidate
        for candidate in candidates
        if candidate[
            "protection_effective"
        ]
    ]

    if effective_candidates:

        recommended = (
            effective_candidates[0]
        )

        solution = {
            "available":
                True,

            "asset_id":
                recommended[
                    "asset_id"
                ],

            "asset_name":
                recommended[
                    "asset_name"
                ],

            "asset_type":
                recommended[
                    "asset_type"
                ],

            "action":
                recommended[
                    "action"
                ],

            "target_status_before":
                recommended[
                    "target_status_without_protection"
                ],

            "target_status_after":
                recommended[
                    "target_status_with_protection"
                ],

            "path":
                recommended[
                    "path"
                ],

            "explanation":
                recommended[
                    "explanation"
                ],
        }

    elif candidates:

        recommended = candidates[0]

        solution = {
            "available":
                False,

            "asset_id":
                recommended[
                    "asset_id"
                ],

            "asset_name":
                recommended[
                    "asset_name"
                ],

            "asset_type":
                recommended[
                    "asset_type"
                ],

            "action":
                recommended[
                    "action"
                ],

            "target_status_before":
                recommended[
                    "target_status_without_protection"
                ],

            "target_status_after":
                recommended[
                    "target_status_with_protection"
                ],

            "path":
                recommended[
                    "path"
                ],

            "explanation":
                (
                    f"No single upstream asset completely "
                    f"prevents {target_name} from reaching "
                    f"a critical state. The strongest available "
                    f"protection point is "
                    f"{recommended['asset_name']} "
                    f"({recommended['asset_id']}), which reduces "
                    f"the target from "
                    f"{readable_status(recommended['target_status_without_protection'])} "
                    f"to "
                    f"{readable_status(recommended['target_status_with_protection'])}."
                ),
        }

    else:

        solution = {
            "available":
                False,

            "asset_id":
                None,

            "asset_name":
                None,

            "asset_type":
                None,

            "action":
                "No upstream protection point identified.",

            "target_status_before":
                None,

            "target_status_after":
                None,

            "path":
                [],

            "explanation":
                (
                    f"No upstream candidate could be tested "
                    f"for {target_name}."
                ),
        }

    # -------------------------------------------------------------
    # FINAL RESPONSE
    # -------------------------------------------------------------

    return {
        "target_asset_id":
            target_asset_id,

        "target_asset_name":
            target_name,

        "incident_type":
            incident_type,

        "severity":
            severity,

        "duration":
            duration,

        "solution":
            solution,

        "candidates":
            candidates,

        "root_causes":
            candidates,
    }

# ---------------------------------------------------------------------
# BASELINE VS INTERVENTION
# ---------------------------------------------------------------------

def compare_simulations(
    city,
    incident_type,
    asset_id,
    severity=1.0,
    duration=60,
    interventions=None,
):

    interventions = interventions or []

    # Baseline: no interventions.
    baseline = simulate(
        city,
        incident_type=incident_type,
        asset_id=asset_id,
        severity=severity,
        duration=duration,
        interventions=[],
    )

    # Intervention scenario.
    intervention = simulate(
        city,
        incident_type=incident_type,
        asset_id=asset_id,
        severity=severity,
        duration=duration,
        interventions=interventions,
    )

    # -------------------------------------------------------------
    # METRIC DELTAS
    # -------------------------------------------------------------

    improvements = {}

    baseline_metrics = baseline["metrics"]

    intervention_metrics = intervention["metrics"]

    for key in baseline_metrics:

        before = baseline_metrics.get(
            key,
            0
        )

        after = intervention_metrics.get(
            key,
            0
        )

        if isinstance(
            before,
            (int, float)
        ) and isinstance(
            after,
            (int, float)
        ):

            improvements[key] = round(
                before - after,
                2
            )

    return {
        "baseline": baseline,

        "intervention": intervention,

        "improvements": improvements,
    }