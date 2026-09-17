import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  reverseSimulation,
} from "../services/api";


export default function InterventionPanel({
  scenarios,
  interventions,
  setInterventions,
  onCompare,
  loading,

  network,
  result,

  incidentType,
  severity,
  duration,

  compact = false,
  reverseOnly = false,
}) {

  const allAssets =
    Array.isArray(
      network?.nodes
    )
      ? network.nodes
      : [];


  /* =========================================================
     TARGET ASSETS FOR REVERSE CASCADE

     Every infrastructure type can be selected.
  ========================================================= */

  const targetAssets =
    useMemo(() => {

      const resultNodes =
        Array.isArray(
          result?.nodes
        )
          ? result.nodes
          : [];


      const affectedIds =
        new Set(
          resultNodes
            .filter(
              (node) =>
                node.status !==
                "operational"
            )
            .map(
              (node) =>
                node.id
            )
        );


      return [
        ...allAssets,
      ].sort(
        (a, b) => {

          const aAffected =
            affectedIds.has(
              a.id
            );

          const bAffected =
            affectedIds.has(
              b.id
            );


          if (
            aAffected &&
            !bAffected
          ) {
            return -1;
          }


          if (
            !aAffected &&
            bAffected
          ) {
            return 1;
          }


          return String(
            a.name || a.id
          ).localeCompare(
            String(
              b.name || b.id
            )
          );

        }
      );

    }, [
      allAssets,
      result,
    ]);


  /* =========================================================
     DEFAULT REVERSE TARGET
  ========================================================= */

  const defaultTarget =
    targetAssets.find(
      (node) =>
        node.status ===
          "failed" ||
        node.status ===
          "near_failure" ||
        node.status ===
          "critical"
    ) ||
    targetAssets[0] ||
    null;


  const [
    targetAssetId,
    setTargetAssetId,
  ] = useState(
    defaultTarget?.id ||
    ""
  );


  const [
    reverseData,
    setReverseData,
  ] = useState(null);


  const [
    reverseLoading,
    setReverseLoading,
  ] = useState(false);


  const [
    reverseError,
    setReverseError,
  ] = useState("");


  /* =========================================================
     KEEP TARGET VALID
  ========================================================= */

  useEffect(() => {

    if (
      !targetAssets.length
    ) {

      setTargetAssetId(
        ""
      );

      return;
    }


    const exists =
      targetAssets.some(
        (node) =>
          node.id ===
          targetAssetId
      );


    if (!exists) {

      setTargetAssetId(
        defaultTarget?.id ||
        targetAssets[0].id
      );

    }

  }, [
    targetAssets,
    targetAssetId,
    defaultTarget,
  ]);


  /* =========================================================
     INTERVENTION TOGGLE
  ========================================================= */

  function toggle(
    id
  ) {

    setInterventions(
      (previous) => {

        if (
          previous.includes(
            id
          )
        ) {

          return previous.filter(
            (item) =>
              item !== id
          );

        }

        return [
          ...previous,
          id,
        ];

      }
    );

  }


  /* =========================================================
     REVERSE CASCADE
  ========================================================= */

  async function runReverseAnalysis() {

    if (
      !targetAssetId
    ) {

      setReverseError(
        "Select a target asset first."
      );

      return;
    }


    setReverseLoading(
      true
    );

    setReverseError(
      ""
    );

    setReverseData(
      null
    );


    try {

      const data =
        await reverseSimulation({

          target_asset_id:
            targetAssetId,

          incident_type:
            incidentType,

          severity:
            severity,

          duration:
            duration,

        });


      setReverseData(
        data
      );

    } catch (error) {

      console.error(
        error
      );

      setReverseError(
        error?.message ||
        "Reverse analysis failed."
      );

    } finally {

      setReverseLoading(
        false
      );

    }

  }


  const solution =
    reverseData?.solution ||
    null;


  const candidates =
    Array.isArray(
      reverseData?.candidates
    )
      ? reverseData.candidates
      : [];


  const selectedTarget =
    targetAssets.find(
      (node) =>
        node.id ===
        targetAssetId
    );


  /* =========================================================
     WHAT-IF PANEL
  ========================================================= */

  if (
    compact
  ) {

    return (

      <section className="panel intervention-panel compact-intervention">

        <div className="panel-title">
          02 · WHAT-IF INTERVENTION
        </div>


        <p className="helper">
          Protect the network, then compare the same incident again.
        </p>


        <div className="compact-intervention-list">

          {Object.entries(
            scenarios?.interventions ||
            {}
          ).map(
            ([key, value]) => (

              <button
                key={key}
                type="button"
                className={`intervention-card ${
                  interventions.includes(
                    key
                  )
                    ? "selected"
                    : ""
                }`}
                onClick={() =>
                  toggle(key)
                }
              >

                <span className="intervention-icon">

                  {interventions.includes(
                    key
                  )
                    ? "✓"
                    : "+"}

                </span>


                <div className="intervention-content">

                  <strong>
                    {value.label}
                  </strong>


                  <p>
                    {value.description}
                  </p>

                </div>

              </button>

            )
          )}

        </div>


        <button
          className="secondary compare-button"
          type="button"
          disabled={
            loading ||
            interventions.length ===
              0
          }
          onClick={
            onCompare
          }
        >

          {loading
            ? "COMPARING…"
            : "COMPARE BEFORE / AFTER"}

        </button>

      </section>

    );

  }


  /* =========================================================
     REVERSE CASCADE PANEL
  ========================================================= */

  return (

    <section
      className="panel reverse-cascade-panel"
    >

      <div className="panel-title">
        03 · REVERSE CASCADE
      </div>


      <p className="helper reverse-intro">
        Start from a critical outcome and trace backwards to find what could have prevented it.
      </p>


      {/* =====================================================
          TOP CONTROL ROW
      ===================================================== */}

      <div className="reverse-control-grid">


        {/* TARGET */}

        <div>

          <label
            htmlFor="reverse-target"
            className="reverse-label"
          >
            Target outcome
          </label>


          <select
            id="reverse-target"
            value={
              targetAssetId
            }
            onChange={(event) => {

              setTargetAssetId(
                event.target.value
              );

              setReverseData(
                null
              );

              setReverseError(
                ""
              );

            }}
            className="reverse-select"
          >

            {targetAssets.map(
              (asset) => (

                <option
                  key={
                    asset.id
                  }
                  value={
                    asset.id
                  }
                >

                  {asset.name} ({asset.id})

                  {asset.status !==
                    "operational"
                    ? ` · ${formatStatus(
                        asset.status
                      )}`
                    : ""}

                </option>

              )
            )}

          </select>


          {selectedTarget && (

            <div className="reverse-current-status">

              Current network status:{" "}

              <strong
                style={{
                  color:
                    getStatusColor(
                      selectedTarget.status
                    ),
                }}
              >
                {formatStatus(
                  selectedTarget.status
                )}
              </strong>

            </div>

          )}

        </div>


        {/* EXPLANATION */}

        <div className="reverse-explanation">

          <div className="reverse-explanation-title">
            WHAT IS HAPPENING?
          </div>


          <div className="reverse-explanation-text">

            {selectedTarget ? (
              <>
                <strong>
                  {selectedTarget.name}
                </strong>{" "}
                is the outcome we're investigating.
                Cascadia traces its upstream dependencies
                and tests which asset could have stopped
                the chain.
              </>
            ) : (
              <>
                Select an infrastructure asset to investigate.
              </>
            )}

          </div>

        </div>


        {/* BUTTON */}

        <button
          className="secondary compare-button reverse-button"
          type="button"
          disabled={
            reverseLoading ||
            !targetAssetId
          }
          onClick={
            runReverseAnalysis
          }
        >

          {reverseLoading
            ? "TRACING BACK…"
            : "TRACE ROOT CAUSE"}

        </button>

      </div>


      {/* =====================================================
          ERROR
      ===================================================== */}

      {reverseError && (

        <div className="reverse-error">
          {reverseError}
        </div>

      )}


      {/* =====================================================
          RESULTS
      ===================================================== */}

      {(solution ||
        candidates.length >
          0) && (

        <div className="reverse-results">


          {/* =================================================
              SOLUTION
          ================================================= */}

          {solution && (

            <div className="reverse-solution">

              <div className="reverse-solution-label">

                {solution.available
                  ? "SOLUTION FOUND"
                  : "BEST AVAILABLE ACTION"}

              </div>


              <div className="reverse-solution-title">

                {solution.action}

              </div>


              <p className="reverse-solution-text">

                {solution.explanation}

              </p>


              {solution.target_status_before && (

                <div className="reverse-status-grid">

                  <StatusBox
                    label="WITHOUT PROTECTION"
                    status={
                      solution.target_status_before
                    }
                    danger
                  />


                  <StatusBox
                    label="WITH PROTECTION"
                    status={
                      solution.target_status_after
                    }
                  />

                </div>

              )}


              {Array.isArray(
                solution.path
              ) &&
                solution.path.length >
                  0 && (

                  <div className="reverse-path">

                    <span>
                      CASCADE PATH
                    </span>

                    <strong>
                      {solution.path.join(
                        " → "
                      )}
                    </strong>

                  </div>

                )}

            </div>

          )}


          {/* =================================================
              RANKED CANDIDATES
          ================================================= */}

          {candidates.length >
            0 && (

            <div className="reverse-candidates">

              <div className="reverse-candidates-title">
                RANKED UPSTREAM CANDIDATES
              </div>


              <div className="reverse-candidate-grid">

                {candidates
                  .slice(
                    0,
                    6
                  )
                  .map(
                    (
                      candidate
                    ) => (

                      <div
                        key={`${candidate.asset_id}-${candidate.rank}`}
                        className="reverse-candidate"
                      >

                        <div className="reverse-candidate-heading">

                          <strong>
                            #{candidate.rank}{" "}
                            {candidate.asset_name}
                          </strong>


                          <span>
                            {
                              candidate.asset_id
                            }
                          </span>

                        </div>


                        <div className="reverse-candidate-path">

                          Path:{" "}

                          {Array.isArray(
                            candidate.path
                          )
                            ? candidate.path.join(
                                " → "
                              )
                            : "—"}

                        </div>


                        <div className="reverse-status-grid">

                          <StatusBox
                            label="WITHOUT"
                            status={
                              candidate.target_status_without_protection
                            }
                            danger
                          />


                          <StatusBox
                            label="PROTECTED"
                            status={
                              candidate.target_status_with_protection
                            }
                          />

                        </div>


                        <div
                          className={
                            candidate.protection_effective
                              ? "reverse-effective"
                              : "reverse-partial"
                          }
                        >

                          {candidate.protection_effective
                            ? "✓ Can prevent the critical outcome"
                            : "Reduces impact but does not fully prevent it"}

                        </div>

                      </div>

                    )
                  )}

              </div>

            </div>

          )}

        </div>

      )}


      {/* =====================================================
          NO RESULTS
      ===================================================== */}

      {reverseData &&
        candidates.length ===
          0 &&
        !solution && (

          <div className="empty-state reverse-empty">

            No upstream candidate was found for this target under the current scenario.

          </div>

        )}

    </section>

  );
}


/* =========================================================
   STATUS BOX
========================================================= */

function StatusBox({
  label,
  status,
  danger = false,
}) {

  return (

    <div
      className={
        danger
          ? "reverse-status-box danger"
          : "reverse-status-box safe"
      }
    >

      <span>
        {label}
      </span>


      <strong>
        {formatStatus(
          status
        )}
      </strong>

    </div>

  );
}


/* =========================================================
   STATUS FORMATTER
========================================================= */

function formatStatus(
  status = ""
) {

  return String(
    status
  )
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


/* =========================================================
   STATUS COLOR
========================================================= */

function getStatusColor(
  status
) {

  if (
    status ===
    "failed"
  ) {
    return "#dc2626";
  }

  if (
    status ===
    "critical"
  ) {
    return "#ea580c";
  }

  if (
    status ===
    "near_failure"
  ) {
    return "#7c3aed";
  }

  if (
    status ===
    "degraded"
  ) {
    return "#ca8a04";
  }

  return "#6d28d9";
}