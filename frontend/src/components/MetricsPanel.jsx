import React, { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

export default function MetricsPanel({
  result = null,
  comparison = null,
}) {
  const metrics = result?.metrics || {};

  const events = Array.isArray(result?.events)
    ? result.events
    : [];

  const chartData = useMemo(() => {
    if (!events.length) {
      return [];
    }

    let failed = 0;
    let degraded = 0;
    let affected = 0;

    return events.map((event, index) => {
      const status =
        event?.status || "";

      if (status === "failed") {
        failed += 1;
      }

      if (
        status === "degraded" ||
        status === "critical" ||
        status === "near_failure"
      ) {
        degraded += 1;
      }

      affected += 1;

      return {
        time: Number(
          event?.time ?? index
        ),

        failed,

        degraded,

        affected,
      };
    });
  }, [events]);

  const metricCards = [
    {
      label: "Affected assets",
      value: formatMetric(
        metrics.affected_assets
      ),
      subtext: "assets impacted",
    },

    {
      label: "Failed assets",
      value: formatMetric(
        metrics.failed_assets
      ),
      subtext: "complete failures",
    },

    {
      label: "Degraded assets",
      value: formatMetric(
        metrics.degraded_assets
      ),
      subtext: "service degradation",
    },

    {
      label: "Cascade depth",
      value: formatMetric(
        metrics.cascade_depth
      ),
      subtext: "propagation levels",
    },

    {
      label: "Traffic increase",
      value: formatPercent(
        metrics.traffic_increase_pct
      ),
      subtext: "network traffic",
    },

    {
      label: "Travel time",
      value: formatMinutes(
        metrics.travel_time_increase_min
      ),
      subtext: "additional delay",
    },

    {
      label: "Emergency delay",
      value: formatMinutes(
        metrics.emergency_response_delay_min
      ),
      subtext: "response impact",
    },

    {
      label: "Recovery time",
      value: formatMinutes(
        metrics.recovery_time_min
      ),
      subtext: "estimated recovery",
    },
  ];

  return (
    <section className="panel metrics-panel">
      <div className="panel-title">
        03 · RESILIENCE METRICS
      </div>

      {!result ? (
        <div className="empty-state">
          <strong>Waiting for simulation</strong>

          <p>
            Run a cascade to calculate
            infrastructure impact.
          </p>
        </div>
      ) : (
        <>
          {/* =================================================
              METRIC CARDS
          ================================================= */}

          <div className="metrics-grid">
            {metricCards.map((metric) => (
              <div
                className="metric-card"
                key={metric.label}
              >
                <div className="metric-label">
                  {metric.label}
                </div>

                <div className="metric-value">
                  {metric.value}
                </div>

                <div className="metric-subtext">
                  {metric.subtext}
                </div>
              </div>
            ))}
          </div>

          {/* =================================================
              CASCADE GRAPH
          ================================================= */}

          <div className="metric-chart-section">
            <div className="chart-header">
              <div>
                <strong>
                  Failure propagation
                </strong>

                <span>
                  Assets affected over time
                </span>
              </div>

              <div className="chart-legend">
                <span>
                  <i className="legend-failed" />
                  Failed
                </span>

                <span>
                  <i className="legend-affected" />
                  Affected
                </span>
              </div>
            </div>

            {chartData.length > 0 ? (
              <div className="metric-chart">
                <ResponsiveContainer
                  width="100%"
                  height={220}
                >
                  <LineChart
                    data={chartData}
                    margin={{
                      top: 10,
                      right: 10,
                      left: -15,
                      bottom: 0,
                    }}
                  >
                    <CartesianGrid
                      stroke="#e5e9f2"
                      strokeDasharray="3 3"
                    />

                    <XAxis
                      dataKey="time"
                      tick={{
                        fontSize: 9,
                        fill: "#78849d",
                      }}
                      tickFormatter={(value) =>
                        `T+${value}`
                      }
                    />

                    <YAxis
                      allowDecimals={false}
                      tick={{
                        fontSize: 9,
                        fill: "#78849d",
                      }}
                    />

                    <Tooltip
                      contentStyle={{
                        border:
                          "1px solid #dce2ef",
                        borderRadius: "9px",
                        background:
                          "#ffffff",
                        fontSize: "11px",
                      }}
                      labelFormatter={(value) =>
                        `T+${value} min`
                      }
                    />

                    <Line
                      type="stepAfter"
                      dataKey="failed"
                      stroke="#ef4444"
                      strokeWidth={3}
                      dot={false}
                      name="Failed"
                    />

                    <Line
                      type="stepAfter"
                      dataKey="affected"
                      stroke="#7c3aed"
                      strokeWidth={2}
                      dot={false}
                      name="Affected"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="chart-empty">
                No propagation events recorded.
              </div>
            )}
          </div>

          {/* =================================================
              INTERVENTION COMPARISON
          ================================================= */}

          {comparison && (
            <ComparisonBlock
              comparison={comparison}
            />
          )}
        </>
      )}
    </section>
  );
}

/* =========================================================
   COMPARISON
========================================================= */

function ComparisonBlock({
  comparison,
}) {
  const baseline =
    comparison?.baseline?.metrics ||
    comparison?.baseline ||
    {};

  const intervention =
    comparison?.intervention?.metrics ||
    comparison?.intervention ||
    {};

  const delta =
    comparison?.delta ||
    comparison?.differences ||
    {};

  return (
    <div className="comparison-block">
      <div className="comparison-title">
        INTERVENTION IMPACT
      </div>

      <div className="comparison-grid">
        <ComparisonRow
          label="Affected assets"
          baseline={
            baseline.affected_assets
          }
          intervention={
            intervention.affected_assets
          }
          delta={
            delta.affected_assets
          }
        />

        <ComparisonRow
          label="Failed assets"
          baseline={
            baseline.failed_assets
          }
          intervention={
            intervention.failed_assets
          }
          delta={
            delta.failed_assets
          }
        />

        <ComparisonRow
          label="Cascade depth"
          baseline={
            baseline.cascade_depth
          }
          intervention={
            intervention.cascade_depth
          }
          delta={
            delta.cascade_depth
          }
        />

        <ComparisonRow
          label="Emergency delay"
          baseline={
            baseline.emergency_response_delay_min
          }
          intervention={
            intervention.emergency_response_delay_min
          }
          delta={
            delta.emergency_response_delay_min
          }
        />

        <ComparisonRow
          label="Recovery time"
          baseline={
            baseline.recovery_time_min
          }
          intervention={
            intervention.recovery_time_min
          }
          delta={
            delta.recovery_time_min
          }
        />
      </div>
    </div>
  );
}

function ComparisonRow({
  label,
  baseline,
  intervention,
  delta,
}) {
  return (
    <div className="comparison-row">
      <span>{label}</span>

      <strong>
        {formatNumber(baseline)}
      </strong>

      <strong>
        {formatNumber(intervention)}
      </strong>

      <em>
        {formatDelta(delta)}
      </em>
    </div>
  );
}

/* =========================================================
   FORMATTERS
========================================================= */

function formatMetric(value) {
  if (
    value === undefined ||
    value === null
  ) {
    return "—";
  }

  return Number.isFinite(Number(value))
    ? Math.round(Number(value))
    : "—";
}

function formatNumber(value) {
  if (
    value === undefined ||
    value === null
  ) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return Number.isInteger(number)
    ? number
    : number.toFixed(1);
}

function formatPercent(value) {
  if (
    value === undefined ||
    value === null
  ) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return `${number.toFixed(1)}%`;
}

function formatMinutes(value) {
  if (
    value === undefined ||
    value === null
  ) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return `${number.toFixed(1)} min`;
}

function formatDelta(value) {
  if (
    value === undefined ||
    value === null
  ) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  if (number > 0) {
    return `+${number.toFixed(1)}`;
  }

  return number.toFixed(1);
}