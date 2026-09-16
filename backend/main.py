from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import SimulationRequest
from network.city_graph import build_city
from simulation.engine import simulate, compare_simulations
from simulation.rules import INCIDENTS, INTERVENTIONS

app = FastAPI(
    title="Infrastructure Resilience Digital Twin",
    version="1.0.0",
    description="Hackathon MVP: deterministic cascading-failure simulation over a synthetic city."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CITY = build_city()


@app.get("/")
def root():
    return {
        "name": "Infrastructure Resilience Digital Twin",
        "status": "running",
        "message": "Synthetic-city hackathon MVP API"
    }


@app.get("/network")
def get_network():
    return {
        "nodes": [CITY.nodes[n]["data"] for n in CITY.nodes],
        "edges": [
            {
                "source": u,
                "target": v,
                "kind": CITY.edges[u, v].get("kind", "dependency")
            }
            for u, v in CITY.edges
        ]
    }


@app.get("/network/{node_id}")
def get_node(node_id: str):
    if node_id not in CITY:
        raise HTTPException(status_code=404, detail="Asset not found")
    return CITY.nodes[node_id]["data"]


@app.get("/scenarios")
def get_scenarios():
    return {
        "incidents": INCIDENTS,
        "interventions": INTERVENTIONS
    }


@app.post("/simulation/run")
def run_simulation(request: SimulationRequest):
    if request.asset_id not in CITY:
        raise HTTPException(status_code=404, detail=f"Unknown asset: {request.asset_id}")
    if request.incident_type not in INCIDENTS:
        raise HTTPException(status_code=400, detail="Unknown incident type")

    return simulate(
        CITY,
        incident_type=request.incident_type,
        asset_id=request.asset_id,
        severity=request.severity,
        duration=request.duration,
        interventions=request.interventions,
    )


@app.post("/simulation/compare")
def compare(request: SimulationRequest):
    if request.asset_id not in CITY:
        raise HTTPException(status_code=404, detail=f"Unknown asset: {request.asset_id}")
    return compare_simulations(
        CITY,
        incident_type=request.incident_type,
        asset_id=request.asset_id,
        severity=request.severity,
        duration=request.duration,
        interventions=request.interventions,
    )
