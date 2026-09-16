# ============================================================
# SIMULATION METRICS
# ============================================================
#
# All metrics are derived from the simulated node state.
#
# The model distinguishes between:
#
#   normal utilization
#   increased utilization
#   overloaded capacity
#
# This means traffic-related metrics do not remain at 0 just
# because a road has not crossed 100% capacity.
# ============================================================


def _safe_capacity(node):
    """
    Return a safe capacity value.
    """

    capacity = node.get("capacity", 0)

    try:
        capacity = float(capacity)
    except (TypeError, ValueError):
        return 1.0

    return max(capacity, 1.0)


def _safe_load(node):
    """
    Return a safe current-load value.
    """

    load = node.get("current_load", 0)

    try:
        return float(load)
    except (TypeError, ValueError):
        return 0.0


def _baseline_load(node):
    """
    Estimate the normal load of a node.

    Preferred source:
        baseline_load

    Fallback:
        65% of capacity.

    The engine will provide baseline_load once the next
    integration step is applied.
    """

    if node.get("baseline_load") is not None:

        try:
            return float(
                node["baseline_load"]
            )
        except (TypeError, ValueError):
            pass

    return _safe_capacity(node) * 0.65


def _utilization(node):
    """
    Current utilization = current_load / capacity.
    """

    return (
        _safe_load(node)
        /
        _safe_capacity(node)
    )


def _baseline_utilization(node):
    """
    Normal utilization before the incident.
    """

    return (
        _baseline_load(node)
        /
        _safe_capacity(node)
    )


def _status_rank(status):
    """
    Convert infrastructure status to a numeric severity level.

    This is useful for comparing how much a node deteriorated.
    """

    ranks = {
        "operational": 0,
        "degraded": 1,
        "critical": 2,
        "near_failure": 3,
        "failed": 4,
    }

    return ranks.get(
        str(status).lower(),
        0
    )


# ============================================================
# ROAD TRAFFIC METRICS
# ============================================================

def _road_metrics(roads):
    """
    Calculate traffic-related metrics directly from road
    utilization.

    Returns:

        average_utilization
        baseline_average_utilization
        traffic_increase_pct
        overloaded_roads
        congestion_index
        travel_time_increase_min
    """

    if not roads:

        return {
            "average_utilization": 0.0,
            "baseline_average_utilization": 0.0,
            "traffic_increase_pct": 0.0,
            "overloaded_roads": 0,
            "congestion_index": 0.0,
            "travel_time_increase_min": 0.0,
        }

    current_utilizations = [
        _utilization(road)
        for road in roads
    ]

    baseline_utilizations = [
        _baseline_utilization(road)
        for road in roads
    ]

    average_utilization = (
        sum(current_utilizations)
        /
        len(current_utilizations)
    )

    baseline_average_utilization = (
        sum(baseline_utilizations)
        /
        len(baseline_utilizations)
    )

    # --------------------------------------------------------
    # Traffic increase
    #
    # Example:
    #
    # baseline = 65%
    # current  = 78%
    #
    # increase = 20%
    #
    # This is different from "overloaded roads".
    # A road can experience increased traffic without being
    # above 100% capacity.
    # --------------------------------------------------------

    if baseline_average_utilization > 0:

        traffic_increase_pct = (
            (
                average_utilization
                -
                baseline_average_utilization
            )
            /
            baseline_average_utilization
        ) * 100.0

    else:

        traffic_increase_pct = 0.0

    traffic_increase_pct = max(
        0.0,
        traffic_increase_pct
    )

    # --------------------------------------------------------
    # Count actual overloaded roads.
    # --------------------------------------------------------

    overloaded_roads = sum(

        1

        for road in roads

        if _utilization(road) > 1.0

    )

    # --------------------------------------------------------
    # Network congestion index.
    #
    # This measures pressure above a comfortable 80%
    # utilization threshold.
    #
    # It is NOT used to declare failure.
    # --------------------------------------------------------

    congestion_values = [

        max(
            0.0,
            _utilization(road) - 0.80
        )

        for road in roads

    ]

    congestion_index = (

        sum(congestion_values)
        /
        len(congestion_values)

    )

    # --------------------------------------------------------
    # Travel-time model
    #
    # Base trip = 10 minutes.
    #
    # As utilization rises above normal, travel time rises.
    #
    # We cap the simulated increase so the prototype doesn't
    # produce absurd values such as 900% traffic growth.
    # --------------------------------------------------------

    base_travel_time = 10.0

    utilization_pressure = max(
        0.0,
        average_utilization
        -
        baseline_average_utilization
    )

    # Convert utilization pressure into travel-time impact.
    #
    # 0.10 additional utilization ≈ 18% increase in travel
    # time before the cap.
    travel_multiplier = min(
        0.80,
        utilization_pressure * 1.8
    )

    travel_time_increase = (
        base_travel_time
        *
        travel_multiplier
    )

    return {

        "average_utilization":
            round(
                average_utilization,
                3
            ),

        "baseline_average_utilization":
            round(
                baseline_average_utilization,
                3
            ),

        "traffic_increase_pct":
            round(
                traffic_increase_pct,
                1
            ),

        "overloaded_roads":
            overloaded_roads,

        "congestion_index":
            round(
                congestion_index,
                3
            ),

        "travel_time_increase_min":
            round(
                travel_time_increase,
                2
            ),

    }


# ============================================================
# EMERGENCY RESPONSE METRICS
# ============================================================

def _emergency_delay(
    roads,
    nodes,
    travel_time_increase,
    interventions
):
    """
    Estimate emergency response delay.

    Emergency delay is based on:

        road travel-time increase
        + critical infrastructure disruption
        + emergency-route intervention

    This remains a synthetic simulation metric, not a real
    emergency-response prediction.
    """

    interventions = interventions or []

    hospitals = [
        node
        for node in nodes
        if node.get("type") == "hospital"
    ]

    emergency_bases = [
        node
        for node in nodes
        if node.get("type") == "emergency"
    ]

    critical_hospitals = sum(

        1

        for hospital in hospitals

        if hospital.get("status")
        != "operational"

    )

    affected_emergency_bases = sum(

        1

        for base in emergency_bases

        if base.get("status")
        != "operational"

    )

    # --------------------------------------------------------
    # Base relationship:
    #
    # travel delay is the largest component.
    # --------------------------------------------------------

    delay = (
        travel_time_increase
        * 1.20
    )

    # --------------------------------------------------------
    # Critical hospital disruption adds service pressure.
    # --------------------------------------------------------

    delay += (
        critical_hospitals
        * 2.0
    )

    # --------------------------------------------------------
    # Emergency-base disruption adds additional pressure.
    # --------------------------------------------------------

    delay += (
        affected_emergency_bases
        * 2.5
    )

    # --------------------------------------------------------
    # Alternative emergency route intervention.
    #
    # This reduces the simulated travel component rather than
    # simply subtracting an arbitrary fixed number.
    # --------------------------------------------------------

    if "emergency_route" in interventions:

        delay *= 0.70

    return round(
        max(0.0, delay),
        2
    )


# ============================================================
# MAIN METRIC FUNCTION
# ============================================================

def calculate_metrics(
    events,
    nodes,
    duration,
    interventions=None
):
    """
    Calculate the complete simulation metric set.

    Parameters
    ----------
    events:
        Propagation events generated by the simulation engine.

    nodes:
        Final simulated node states.

    duration:
        Incident duration in minutes.

    interventions:
        Interventions active during this simulation.

    Returns
    -------
    dict
        Simulation metrics.
    """

    interventions = interventions or []

    # --------------------------------------------------------
    # AFFECTED ASSETS
    # --------------------------------------------------------

    affected = [

        node

        for node in nodes

        if node.get("status")
        != "operational"

    ]

    # --------------------------------------------------------
    # DEGRADED / CRITICAL / NEAR-FAILURE
    # --------------------------------------------------------

    degraded = [

        node

        for node in nodes

        if node.get("status")
        in (
            "degraded",
            "critical",
            "near_failure"
        )

    ]

    # --------------------------------------------------------
    # FAILED
    # --------------------------------------------------------

    failed = [

        node

        for node in nodes

        if node.get("status")
        == "failed"

    ]

    # --------------------------------------------------------
    # ROADS
    # --------------------------------------------------------

    roads = [

        node

        for node in nodes

        if node.get("type")
        == "road"

    ]

    # --------------------------------------------------------
    # HOSPITALS
    # --------------------------------------------------------

    hospitals = [

        node

        for node in nodes

        if node.get("type")
        == "hospital"

    ]

    impacted_hospitals = [

        hospital

        for hospital in hospitals

        if hospital.get("status")
        != "operational"

    ]

    # --------------------------------------------------------
    # ROAD METRICS
    # --------------------------------------------------------

    road_metrics = _road_metrics(
        roads
    )

    traffic_increase_pct = (
        road_metrics[
            "traffic_increase_pct"
        ]
    )

    travel_time_increase = (
        road_metrics[
            "travel_time_increase_min"
        ]
    )

    overloaded_roads = (
        road_metrics[
            "overloaded_roads"
        ]
    )

    # --------------------------------------------------------
    # EMERGENCY RESPONSE
    # --------------------------------------------------------

    emergency_delay = _emergency_delay(

        roads,

        nodes,

        travel_time_increase,

        interventions

    )

    # --------------------------------------------------------
    # CASCADE DEPTH
    # --------------------------------------------------------

    max_depth = max(

        (
            event.get(
                "depth",
                0
            )

            for event in events

        ),

        default=0

    )

    # --------------------------------------------------------
    # NUMBER OF PROPAGATION EVENTS
    # --------------------------------------------------------

    propagation_events = len(
        events
    )

    # --------------------------------------------------------
    # RECOVERY TIME
    #
    # Recovery burden grows with cascade size and depth.
    # --------------------------------------------------------

    recovery_estimate = max(

        10,

        int(

            propagation_events * 3

            +
            max_depth * 2

        )

    )

    recovery_time = min(

        duration,

        recovery_estimate

    )

    # --------------------------------------------------------
    # SEVERITY SUMMARY
    #
    # Useful for the frontend/debugging and makes the metrics
    # more explainable.
    # --------------------------------------------------------

    status_changes = sum(

        1

        for event in events

        if event.get(
            "previous_status"
        )
        != event.get(
            "status"
        )

    )

    # --------------------------------------------------------
    # UTILIZATION SUMMARY
    # --------------------------------------------------------

    if roads:

        max_road_utilization = max(

            _utilization(road)

            for road in roads

        )

        average_road_utilization = (

            sum(
                _utilization(road)
                for road in roads
            )
            /
            len(roads)

        )

    else:

        max_road_utilization = 0.0

        average_road_utilization = 0.0

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    return {

        # Core impact metrics
        "affected_assets":
            len(affected),

        "degraded_assets":
            len(degraded),

        "failed_assets":
            len(failed),

        "overloaded_roads":
            overloaded_roads,

        # Traffic
        "traffic_increase_pct":
            traffic_increase_pct,

        "travel_time_increase_min":
            travel_time_increase,

        # Emergency services
        "emergency_response_delay_min":
            emergency_delay,

        "critical_facilities_affected":
            len(impacted_hospitals),

        # Cascade
        "cascade_depth":
            max_depth,

        "recovery_time_min":
            recovery_time,

        # Additional useful simulation information
        "propagation_events":
            propagation_events,

        "status_changes":
            status_changes,

        "average_road_utilization_pct":
            round(
                average_road_utilization * 100,
                1
            ),

        "max_road_utilization_pct":
            round(
                max_road_utilization * 100,
                1
            ),

        "congestion_index":
            road_metrics[
                "congestion_index"
            ],

    }