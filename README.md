# Infrastructure Resilience Digital Twin — Hackathon MVP

A runnable prototype for the Manipal Hackathon Round 1 concept:

**Cascading Failure Simulation, Impact Analysis & Resilience Planning Platform**

The prototype uses:

- Python + FastAPI for the deterministic simulation engine
- NetworkX for the dependency graph
- NumPy/Pandas for calculations and result processing
- React + Vite for the dashboard
- Leaflet/React-Leaflet for the synthetic-city map
- Recharts for metrics
- A synthetic city so the demo is reproducible and does not claim real engineering limits

## Live Demo

### Frontend — Vercel

https://project-y-rho.vercel.app

### Backend API — Render

https://projecty-xr9c.onrender.com

### Backend API Documentation

https://projecty-xr9c.onrender.com/docs

## 1. Prerequisites

Install:

- Python 3.10+
- Node.js 18+
- npm

## 2. Run the backend

```bash
cd backend

python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

uvicorn main:app --reload --port 8000
Backend:

http://localhost:8000

API docs:

http://localhost:8000/docs

3. Run the frontend

Open another terminal:

cd frontend

npm install

npm run dev

Open the URL printed by Vite, normally:

http://localhost:5173

4. Demo flow

Recommended first demo:

Incident: Power Substation Failure
Asset: S4
Severity: 100%
Run Simulation
Watch the map and timeline
Click a failed/degraded asset to inspect "Why did this fail?"
Add "Backup traffic-signal power"
Run comparison
Explain that all percentages are simulated outputs, not engineering predictions
5. API
GET /network
GET /network/{node_id}
GET /scenarios
POST /simulation/run
POST /simulation/compare
POST /simulation/reverse

Example:

POST /simulation/run

{
  "incident_type": "power_failure",
  "asset_id": "S4",
  "severity": 1.0,
  "duration": 60,
  "interventions": []
}
6. Project structure
infrastructure-resilience-digital-twin/

├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── models/
│   │   └── schemas.py
│   ├── network/
│   │   └── city_graph.py
│   └── simulation/
│       ├── engine.py
│       ├── rules.py
│       └── metrics.py
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── api.js
        ├── styles.css
        └── components/
            ├── IncidentPanel.jsx
            ├── CityMap.jsx
            ├── MetricsPanel.jsx
            ├── CascadeTimeline.jsx
            ├── CausalChain.jsx
            └── InterventionPanel.jsx

Important modeling note

This is intentionally a controlled hackathon simulation. Capacity thresholds and effects are parameters of the synthetic model. They are not real-world engineering limits, certifications, forecasts, or operational guarantees.