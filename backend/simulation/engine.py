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

    if utilization <= 0.79:
        return "operational"
    if utilization <= 0.99:
        return "degraded"
    if utilization <= 1.10:
        return "critical"
    if utilization <= 1.35:
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
        "baseline_load": round(node.get("baseline_load", node["current_load"]), 2),
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
            # Direct power dependencies
            ("substation", "signal"): 0.95,
            ("substation", "pump"): 0.55,
            ("substation", "hospital"): 0.35,
            ("substation", "control"): 0.30,

            # Signal failure creates traffic pressure.
            ("signal", "road"): 0.32,

            # Road disruption affects emergency access.
            ("road", "emergency"): 0.18,

            # Road disruption affects hospital accessibility.
            ("road", "hospital"): 0.14,

            # -------------------------------------------------
            # THIRD CASCADE STAGE
            # -------------------------------------------------
            #
            # Hospitals and emergency bases can create additional
            # service pressure once their access is degraded.
            #
            ("hospital", "emergency"): 0.10,
            ("emergency", "facility"): 0.08,
        }

        factor = table.get(
            (source_type, target_type),
            0.05
        )

        # Backup signal power blocks the direct signal cascade.
        if (
            source_type == "substation"
            and target_type == "signal"
            and target_node.get("signal_backup")
        ):
            return 0.0

        # Backup hospital power blocks direct power degradation.
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
            ("road", "road"): 0.30,
            ("road", "hospital"): 0.12,
            ("road", "emergency"): 0.15,
            ("road", "facility"): 0.10,

            ("pump", "water"): 0.40,
            ("water", "zone"): 0.20,

            ("substation", "signal"): 0.25,
            ("substation", "hospital"): 0.15,
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
            ("road", "road"): 0.35,
            ("road", "hospital"): 0.14,
            ("road", "emergency"): 0.20,
            ("road", "facility"): 0.10,
            ("road", "zone"): 0.08,
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
            ("bridge", "road"): 0.55,
            ("road", "road"): 0.25,
            ("road", "hospital"): 0.12,
            ("road", "emergency"): 0.18,
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
            ("facility", "road"): 0.30,
            ("road", "road"): 0.25,
            ("road", "emergency"): 0.25,
            ("road", "hospital"): 0.12,
            ("road", "zone"): 0.15,
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

        # Third-stage propagation delays
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

        utilization = road["current_load"] / max(
            road["capacity"],
            1
        )

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

            target["status"] = _status(
                target["current_load"],
                target["capacity"]
            )

            if target["status"] != "operational":
                changed.append(
                    (
                        target["id"],
                        before,
                        target["current_load"]
                    )
                )

    # Failed signals add a small amount of traffic pressure.
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

            road["status"] = _status(
                road["current_load"],
                road["capacity"]
            )

            if road["status"] != "operational":
                changed.append(
                    (
                        road["id"],
                        before,
                        road["current_load"]
                    )
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
):
    return {
        "time": round(time, 2),
        "node_id": node["id"],
        "node_name": node["name"],
        "status": node["status"],
        "previous_status": previous_status,
        "reason": reason,
        "parent_id": parent_id,
        "depth": depth,
        "load_before": round(load_before, 2),
        "load_after": round(node["current_load"], 2),
        "capacity": round(node["capacity"], 2),
        "utilization": round(
            node["current_load"]
            / max(node["capacity"], 1)
            * 100,
            1
        ),
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

    # Preserve original loads.
    for node in nodes.values():
        node["baseline_load"] = node["current_load"]

    # Apply interventions before simulation.
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
        reason=f"Initial {incident_type} incident",
        parent_id=None,
        depth=0,
        load_before=root["baseline_load"],
    )

    events.append(root_event)

    # -------------------------------------------------------------
    # EVENT QUEUE
    # -------------------------------------------------------------

    queue = []

    counter = 0

    for target_id in graph.successors(asset_id):

        edge = graph.edges[asset_id, target_id]

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

        # Avoid repeatedly processing the same node at the same
        # or shallower cascade level.
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

        # Stronger propagation from failed assets.
        if parent["status"] == "failed":
            factor *= 1.12

        elif parent["status"] in (
            "critical",
            "near_failure"
        ):
            factor *= 1.05

        # Road-to-road propagation is intentionally controlled
        # to prevent unrealistic city-wide congestion.
        if (
            source_type == "road"
            and target_type == "road"
        ):
            factor *= 0.55

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

        # Emergency route reduces resulting pressure.
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
        # ONLY RECORD A REAL STATUS CHANGE
        # ---------------------------------------------------------

        if target["status"] != previous_status:

            reason = (
                f"{parent['name']} caused "
                f"{target['name']} to become "
                f"{target['status']}"
            )

            events.append(
                _event(
                    time=current_time,
                    node=target,
                    previous_status=previous_status,
                    reason=reason,
                    parent_id=parent_id,
                    depth=depth,
                    load_before=load_before,
                )
            )

        # ---------------------------------------------------------
        # PROPAGATE TO NEXT LEVEL
        # ---------------------------------------------------------

        #
        # IMPORTANT:
        # We continue propagation even when a node only becomes
        # degraded/critical. This is what allows:
        #
        # S4
        #   ↓
        # Signals
        #   ↓
        # Roads
        #   ↓
        # Hospital / Emergency
        #
        # to form a third cascade layer.
        #

        if target["status"] != "operational":

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

    # Record rerouting-induced changes.
    for (
        changed_id,
        load_before,
        load_after
    ) in reroute_changes:

        node = nodes[changed_id]

        events.append(
            _event(
                time=min(duration, 20),
                node=node,
                previous_status="operational",
                reason="Traffic rerouting increased road pressure",
                parent_id=None,
                depth=3,
                load_before=load_before,
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

                emergency["status"] = _status(
                    emergency["current_load"],
                    emergency["capacity"]
                )

                if emergency["status"] != "operational":

                    events.append(
                        _event(
                            time=12,
                            node=emergency,
                            previous_status="operational",
                            reason="Fire increased emergency response demand",
                            parent_id=asset_id,
                            depth=2,
                            load_before=before,
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
                "status": current["status"],
                "time": current["time"],
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
            "status": event["status"],
            "depth": event["depth"],
            "parent": event["parent_id"],
            "reason": event["reason"],
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

        before = baseline_metrics.get(key, 0)
        after = intervention_metrics.get(key, 0)

        if isinstance(before, (int, float)) and isinstance(
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