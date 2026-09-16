INCIDENTS = {
    "flood": {
        "label": "Extreme Rainfall / Urban Flood",
        "description": "Reduces road capacity and can disrupt pumps and substations."
    },
    "accident": {
        "label": "Major Road Accident",
        "description": "Blocks a road, forcing traffic onto alternative corridors."
    },
    "power_failure": {
        "label": "Power Substation Failure",
        "description": "Reduces power availability and can disable traffic signals, pumps and hospital support."
    },
    "bridge_failure": {
        "label": "Bridge Failure",
        "description": "Removes a cross-zone connection and increases rerouting pressure."
    },
    "fire": {
        "label": "Building / Industrial Fire",
        "description": "Restricts nearby roads, increases emergency demand and can trigger evacuation."
    }
}

INTERVENTIONS = {
    "backup_signal_power": {
        "label": "Backup traffic-signal power",
        "description": "Keeps signal assets operational when their supplying substation fails."
    },
    "road_capacity": {
        "label": "Additional road capacity",
        "description": "Adds simulated capacity to the most stressed alternative corridor."
    },
    "emergency_route": {
        "label": "Alternative emergency route",
        "description": "Reduces simulated emergency travel time and delay."
    },
    "backup_hospital_power": {
        "label": "Backup hospital power",
        "description": "Prevents hospital service degradation caused directly by power loss."
    },
    "pump_redundancy": {
        "label": "Redundant water pump",
        "description": "Reduces water-service impact when a pump is disrupted."
    }
}

INCIDENT_START_RULES = {
    "flood": {
        "road": 0.65,
        "pump": 0.50,
        "substation": 0.25,
    },
    "accident": {
        "road": 1.00,
    },
    "power_failure": {
        "substation": 1.00,
    },
    "bridge_failure": {
        "bridge": 1.00,
    },
    "fire": {
        "road": 0.60,
        "facility": 0.80,
    },
}
