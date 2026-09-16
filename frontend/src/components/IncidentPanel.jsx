import React from "react";

export default function IncidentPanel({
  incidentType,
  setIncidentType,
  assetId,
  setAssetId,
  severity,
  setSeverity,
  duration,
  setDuration,
  assetsForIncident = [],
  scenarios = {},
  onRunCascade,
  loading = false,
}) {
  const incidents = scenarios?.incidents || {};

  const safeAssets = Array.isArray(assetsForIncident)
    ? assetsForIncident
    : [];

  const incidentEntries = Object.entries(incidents);

  const selectedAsset =
    safeAssets.find((asset) => asset.id === assetId) || null;

  const incidentLabel =
    incidents?.[incidentType]?.label ||
    formatLabel(incidentType);

  return (
    <section className="control-panel incident-panel">
      {/* HEADER */}
      <div className="panel-header">
        <div>
          <span className="panel-kicker">01 · SCENARIO</span>
          <h2>Incident Setup</h2>
        </div>

        <div className="panel-icon">⚡</div>
      </div>

      {/* INCIDENT TYPE */}
      <div className="field-group">
        <label htmlFor="incident-type">
          Incident type
        </label>

        <select
          id="incident-type"
          value={incidentType}
          onChange={(event) =>
            setIncidentType(event.target.value)
          }
        >
          {incidentEntries.length > 0 ? (
            incidentEntries.map(([key, incident]) => (
              <option key={key} value={key}>
                {incident?.label || formatLabel(key)}
              </option>
            ))
          ) : (
            <>
              <option value="power_failure">
                Power Substation Failure
              </option>

              <option value="flood">
                Extreme Rainfall / Urban Flood
              </option>

              <option value="accident">
                Major Road Accident
              </option>

              <option value="bridge_failure">
                Bridge Failure
              </option>

              <option value="fire">
                Building / Industrial Fire
              </option>
            </>
          )}
        </select>

        {incidents?.[incidentType]?.description && (
          <p className="field-description">
            {incidents[incidentType].description}
          </p>
        )}
      </div>

      {/* STARTING ASSET */}
      <div className="field-group">
        <label htmlFor="asset-id">
          Starting asset
        </label>

        <select
          id="asset-id"
          value={assetId}
          onChange={(event) =>
            setAssetId(event.target.value)
          }
          disabled={safeAssets.length === 0}
        >
          {safeAssets.length > 0 ? (
            safeAssets.map((asset) => (
              <option
                key={asset.id}
                value={asset.id}
              >
                {asset.name || asset.id}
              </option>
            ))
          ) : (
            <option value="">
              No compatible assets
            </option>
          )}
        </select>

        {selectedAsset && (
          <p className="field-description">
            {selectedAsset.type}
          </p>
        )}
      </div>

      {/* SEVERITY */}
      <div className="field-group">
        <div className="range-label">
          <label htmlFor="severity">
            Severity
          </label>

          <strong>
            {Math.round(severity * 100)}%
          </strong>
        </div>

        <input
          id="severity"
          type="range"
          min="0.1"
          max="1"
          step="0.05"
          value={severity}
          onChange={(event) =>
            setSeverity(Number(event.target.value))
          }
        />

        <div className="range-scale">
          <span>Low</span>
          <span>Extreme</span>
        </div>
      </div>

      {/* DURATION */}
      <div className="field-group">
        <div className="range-label">
          <label htmlFor="duration">
            Incident duration
          </label>

          <strong>
            {duration} min
          </strong>
        </div>

        <input
          id="duration"
          type="range"
          min="10"
          max="240"
          step="10"
          value={duration}
          onChange={(event) =>
            setDuration(Number(event.target.value))
          }
        />

        <div className="range-scale">
          <span>10 min</span>
          <span>240 min</span>
        </div>
      </div>

      {/* CURRENT SCENARIO */}
      <div className="scenario-summary">
        <div className="summary-title">
          Current scenario
        </div>

        <div className="summary-row">
          <span>Incident</span>
          <strong>{incidentLabel}</strong>
        </div>

        <div className="summary-row">
          <span>Asset</span>
          <strong>{assetId || "—"}</strong>
        </div>

        <div className="summary-row">
          <span>Severity</span>
          <strong>
            {Math.round(severity * 100)}%
          </strong>
        </div>

        <div className="summary-row">
          <span>Duration</span>
          <strong>{duration} min</strong>
        </div>
      </div>

      {/* NOTICE */}
      <div className="scenario-notice">
        <span>ⓘ</span>

        <p>
          Changing these controls only changes the{" "}
          <strong>pending scenario</strong>. Your current
          cascade remains visible until you run a new one.
        </p>
      </div>

      {/* RUN CASCADE */}
      <button
        type="button"
        className="primary-action run-cascade-button"
        onClick={onRunCascade}
        disabled={loading || !assetId}
      >
        {loading ? (
          <>
            <span className="button-spinner" />
            RUNNING CASCADE...
          </>
        ) : (
          <>
            RUN CASCADE
            <span className="button-arrow">→</span>
          </>
        )}
      </button>
    </section>
  );
}

function formatLabel(value = "") {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}