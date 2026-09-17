import React, {
  useEffect,
  useMemo,
  useState,
} from "react";

import IncidentPanel from "./components/IncidentPanel";
import CityMap from "./components/CityMap";
import CascadeTimeline from "./components/CascadeTimeline";
import MetricsPanel from "./components/MetricsPanel";
import CausalChain from "./components/CausalChain";
import InterventionPanel from "./components/InterventionPanel";

import {
  getNetwork,
  getScenarios,
  runSimulation,
  compareSimulation,
} from "./services/api";

import "./App.css";

export default function App() {
  const [network, setNetwork] = useState({
    nodes: [],
    edges: [],
  });

  const [scenarios, setScenarios] = useState({
    incidents: {},
    interventions: {},
  });

  const [incidentType, setIncidentType] =
    useState("power_failure");

  const [assetId, setAssetId] =
    useState("S2");

  const [severity, setSeverity] =
    useState(1);

  const [duration, setDuration] =
    useState(60);

  const [interventions, setInterventions] =
    useState([]);

  const [result, setResult] =
    useState(null);

  const [comparison, setComparison] =
    useState(null);

  const [selectedNode, setSelectedNode] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [compareLoading, setCompareLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  /* =====================================================
     LOAD INITIAL NETWORK + SCENARIOS
  ===================================================== */

  useEffect(() => {
    async function loadInitialData() {
      try {
        const [
          networkData,
          scenarioData,
        ] = await Promise.all([
          getNetwork(),
          getScenarios(),
        ]);

        setNetwork(networkData);
        setScenarios(scenarioData);

        const initialAssets =
          getAssetsForIncident(
            networkData.nodes,
            "power_failure"
          );

        if (initialAssets.length > 0) {
          setAssetId((current) => {
            const exists =
              initialAssets.some(
                (asset) =>
                  asset.id === current
              );

            return exists
              ? current
              : initialAssets[0].id;
          });
        }
      } catch (err) {
        console.error(err);

        setError(
          "Unable to load the city network."
        );
      }
    }

    loadInitialData();
  }, []);

  /* =====================================================
     COMPATIBLE ASSETS FOR CURRENT INCIDENT
  ===================================================== */

  const assetsForIncident = useMemo(() => {
    return getAssetsForIncident(
      network.nodes,
      incidentType
    );
  }, [
    network.nodes,
    incidentType,
  ]);

  /* =====================================================
     KEEP SELECTED ASSET VALID
  ===================================================== */

  useEffect(() => {
    if (!assetsForIncident.length) {
      setAssetId("");
      return;
    }

    const stillValid =
      assetsForIncident.some(
        (asset) =>
          asset.id === assetId
      );

    if (!stillValid) {
      setAssetId(
        assetsForIncident[0].id
      );
    }
  }, [
    assetsForIncident,
    assetId,
  ]);

  /* =====================================================
     RUN CASCADE
  ===================================================== */

  async function handleRunCascade() {
    if (!assetId) {
      setError(
        "Please select a starting asset."
      );

      return;
    }

    setLoading(true);
    setError("");
    setComparison(null);

    try {
      const simulation =
        await runSimulation({
          incident_type:
            incidentType,
          asset_id:
            assetId,
          severity,
          duration,
          interventions: [],
        });

      setResult(simulation);

      const incidentNode =
        network.nodes.find(
          (node) =>
            node.id === assetId
        );

      if (incidentNode) {
        setSelectedNode({
          ...incidentNode,

          status:
            simulation?.nodes?.find(
              (node) =>
                node.id === assetId
            )?.status ||
            incidentNode.status,
        });
      } else {
        setSelectedNode(null);
      }
    } catch (err) {
      console.error(err);

      setError(
        err?.message ||
          "Simulation failed."
      );
    } finally {
      setLoading(false);
    }
  }

  /* =====================================================
     COMPARE INTERVENTION
  ===================================================== */

  async function handleCompareIntervention() {
    if (!assetId) {
      setError(
        "Please select a starting asset."
      );

      return;
    }

    if (
      interventions.length === 0
    ) {
      setError(
        "Select at least one intervention first."
      );

      return;
    }

    setCompareLoading(true);
    setError("");

    try {
      const comparisonData =
        await compareSimulation({
          incident_type:
            incidentType,
          asset_id:
            assetId,
          severity,
          duration,
          interventions,
        });

      setComparison(
        comparisonData
      );

      if (
        comparisonData?.intervention
      ) {
        setResult(
          comparisonData.intervention
        );
      }
    } catch (err) {
      console.error(err);

      setError(
        err?.message ||
          "Intervention comparison failed."
      );
    } finally {
      setCompareLoading(false);
    }
  }

  /* =====================================================
     MAP NODE SELECTION
  ===================================================== */

  function handleNodeSelect(node) {
    setSelectedNode(node);
  }

  /* =====================================================
     FOOTER DATA
  ===================================================== */

  const networkAssetCount =
    Array.isArray(network.nodes)
      ? network.nodes.length
      : 0;

  const networkEdgeCount =
    Array.isArray(network.edges)
      ? network.edges.length
      : 0;

  const activeScenarioLabel =
    scenarios?.incidents?.[
      incidentType
    ]?.label ||
    formatLabel(incidentType);

  /* =====================================================
     RENDER
  ===================================================== */

  return (
    <div className="app-shell">

      {/* =================================================
          HEADER
      ================================================= */}

      <header className="topbar">

        <div>

          <div className="brand-kicker">
            CASCADIA · URBAN RESILIENCE
          </div>

          <h1>
            Cascadia
          </h1>

          <p>
            See how one infrastructure
            failure can ripple across
            an entire city.
          </p>

        </div>

        <div className="topbar-status">

          <span className="status-dot" />

          LIVE SIMULATION

        </div>

      </header>


      {/* =================================================
          ERROR
      ================================================= */}

      {error && (

        <div className="error-banner">

          <strong>
            Simulation error:
          </strong>

          <span>
            {error}
          </span>

          <button
            type="button"
            onClick={() =>
              setError("")
            }
          >
            ×
          </button>

        </div>

      )}


      {/* =================================================
          MAIN DASHBOARD
      ================================================= */}

      <main className="dashboard-grid">


        {/* =================================================
            LEFT COLUMN

            Scenario + What-if stay together.
            This fills the vertical space naturally.
        ================================================= */}

        <aside className="left-column">

          <IncidentPanel
            incidentType={
              incidentType
            }

            setIncidentType={
              setIncidentType
            }

            assetId={
              assetId
            }

            setAssetId={
              setAssetId
            }

            severity={
              severity
            }

            setSeverity={
              setSeverity
            }

            duration={
              duration
            }

            setDuration={
              setDuration
            }

            assetsForIncident={
              assetsForIncident
            }

            scenarios={
              scenarios
            }

            onRunCascade={
              handleRunCascade
            }

            loading={
              loading
            }
          />


          <InterventionPanel
            scenarios={
              scenarios
            }

            interventions={
              interventions
            }

            setInterventions={
              setInterventions
            }

            onCompare={
              handleCompareIntervention
            }

            loading={
              compareLoading
            }

            network={
              network
            }

            result={
              result
            }

            incidentType={
              incidentType
            }

            severity={
              severity
            }

            duration={
              duration
            }

            assetId={
              assetId
            }

            compact
          />

        </aside>


        {/* =================================================
            CENTER COLUMN
        ================================================= */}

        <section className="center-column">

          <CityMap
            network={
              network
            }

            result={
              result
            }

            selectedNode={
              selectedNode
            }

            setSelectedNode={
              handleNodeSelect
            }

            incidentAsset={
              result?.scenario
                ?.asset_id ||
              null
            }
          />


          <CascadeTimeline
            result={
              result
            }
          />

        </section>


        {/* =================================================
            RIGHT COLUMN
        ================================================= */}

        <aside className="right-column">

          <MetricsPanel
            result={
              result
            }

            comparison={
              comparison
            }
          />


          <CausalChain
            result={
              result
            }

            selectedNode={
              selectedNode
            }
          />

        </aside>


        {/* =================================================
            REVERSE CASCADE

            Full-width underneath the dashboard.
            This is where the reverse-cascade feature
            gets the space it actually needs.
        ================================================= */}

        <section className="reverse-cascade-row">

          <InterventionPanel
            scenarios={
              scenarios
            }

            interventions={
              interventions
            }

            setInterventions={
              setInterventions
            }

            onCompare={
              handleCompareIntervention
            }

            loading={
              compareLoading
            }

            network={
              network
            }

            result={
              result
            }

            incidentType={
              incidentType
            }

            severity={
              severity
            }

            duration={
              duration
            }

            assetId={
              assetId
            }

            reverseOnly
          />

        </section>

      </main>


      {/* =================================================
          FOOTER
      ================================================= */}

      <footer className="app-footer">

        <span>
          Cascadia
        </span>

        <span>
          Network{" "}
          {networkAssetCount} assets
        </span>

        <span>
          Dependencies{" "}
          {networkEdgeCount} links
        </span>

        <span>
          Scenario{" "}
          {activeScenarioLabel}
        </span>

        <span>
          Asset{" "}
          {assetId || "—"}
        </span>

      </footer>

    </div>
  );
}


/* =========================================================
   INCIDENT → COMPATIBLE ASSETS
========================================================= */

function getAssetsForIncident(
  nodes = [],
  incidentType
) {

  const typeMap = {

    power_failure: [
      "substation",
    ],

    flood: [
      "road",
      "pump",
      "substation",
    ],

    accident: [
      "road",
    ],

    bridge_failure: [
      "bridge",
    ],

    fire: [
      "road",
      "facility",
    ],

  };


  const allowedTypes =
    typeMap[
      incidentType
    ] || [];


  if (
    !Array.isArray(nodes)
  ) {
    return [];
  }


  return nodes.filter(
    (node) =>
      allowedTypes.includes(
        node.type
      )
  );
}


/* =========================================================
   LABEL FORMATTER
========================================================= */

function formatLabel(
  value = ""
) {

  return value
    .replaceAll(
      "_",
      " "
    )
    .replace(
      /\b\w/g,
      (char) =>
        char.toUpperCase()
    );

}