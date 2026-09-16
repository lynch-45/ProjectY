import React from "react";

export default function CascadeTimeline({ result = null }) {
  const events = Array.isArray(result?.events)
    ? result.events
    : [];

  const hasEvents = events.length > 0;

  return (
    <section className="panel timeline-panel">
      <div className="panel-title">
        04 · CASCADE TIMELINE
      </div>

      {!hasEvents ? (
        <div className="timeline-empty">
          <div className="timeline-empty-icon">⌁</div>

          <div>
            <strong>No cascade yet</strong>
            <p>
              Configure an incident and click
              <b> Run Cascade</b> to see how failure
              propagates through the network.
            </p>
          </div>
        </div>
      ) : (
        <div className="cascade-timeline">
          {events.map((event, index) => {
            const time = Number(event?.time ?? 0);

            const nodeId =
              event?.node_id ??
              event?.id ??
              "—";

            const nodeName =
              event?.node_name ??
              event?.name ??
              nodeId;

            const nodeType =
              event?.node_type ??
              "infrastructure";

            const status =
              event?.status ??
              "unknown";

            const previousStatus =
              event?.previous_status ??
              null;

            const reason =
              event?.reason ??
              "Infrastructure state changed.";

            const mechanism =
              event?.mechanism ??
              null;

            const loadBefore = Number(
              event?.load_before ?? 0
            );

            const loadAfter = Number(
              event?.load_after ?? 0
            );

            const capacity = Number(
              event?.capacity ?? 0
            );

            const utilization =
              capacity > 0
                ? (loadAfter / capacity) * 100
                : null;

            const isInitial =
              index === 0 ||
              event?.cause_type === "incident";

            const icon = getTypeIcon(nodeType);

            return (
              <div
                className={`cascade-event ${
                  isInitial ? "cascade-event-initial" : ""
                }`}
                key={`${nodeId}-${time}-${index}`}
              >
                {/* TIME */}
                <div className="cascade-time">
                  <span>T+</span>
                  <strong>{time}</strong>
                  <small>min</small>
                </div>

                {/* TIMELINE */}
                <div className="cascade-track">
                  <div className="cascade-dot">
                    {icon}
                  </div>

                  {index < events.length - 1 && (
                    <div className="cascade-line" />
                  )}
                </div>

                {/* EVENT CARD */}
                <div className="cascade-card">
                  <div className="cascade-card-header">
                    <div className="cascade-asset">
                      <div className="cascade-asset-name">
                        {nodeName}
                      </div>

                      <div className="cascade-asset-meta">
                        <span>{nodeId}</span>
                        <span className="meta-divider">•</span>
                        <span>
                          {formatType(nodeType)}
                        </span>
                      </div>
                    </div>

                    <div
                      className={`cascade-status status-${status}`}
                    >
                      <span className="status-dot" />
                      {formatStatus(status)}
                    </div>
                  </div>

                  {/* STATUS TRANSITION */}
                  {previousStatus &&
                    previousStatus !== status && (
                      <div className="status-transition">
                        <span>
                          {formatStatus(previousStatus)}
                        </span>

                        <span className="transition-arrow">
                          →
                        </span>

                        <strong>
                          {formatStatus(status)}
                        </strong>
                      </div>
                    )}

                  {/* EXPLANATION */}
                  <div className="cascade-explanation">
                    <div className="explanation-label">
                      {isInitial
                        ? "INITIAL INCIDENT"
                        : "PROPAGATION"}
                    </div>

                    <p>{reason}</p>

                    {mechanism && (
                      <div className="cascade-mechanism">
                        <span className="mechanism-icon">
                          ↳
                        </span>
                        <span>{mechanism}</span>
                      </div>
                    )}
                  </div>

                  {/* LOAD IMPACT */}
                  {capacity > 0 &&
                    (loadBefore > 0 ||
                      loadAfter > 0) && (
                      <div className="load-impact">
                        <div className="load-header">
                          <span>LOAD IMPACT</span>

                          <strong>
                            {utilization.toFixed(0)}%
                            utilization
                          </strong>
                        </div>

                        <div className="load-bar">
                          <div
                            className={`load-fill ${
                              utilization >= 100
                                ? "load-over"
                                : utilization >= 80
                                ? "load-high"
                                : ""
                            }`}
                            style={{
                              width: `${Math.min(
                                utilization,
                                100
                              )}%`,
                            }}
                          />

                          <div
                            className="capacity-marker"
                            style={{
                              left: "100%",
                            }}
                          />
                        </div>

                        <div className="load-values">
                          <span>
                            {loadBefore.toFixed(1)}
                            {" → "}
                            {loadAfter.toFixed(1)}
                          </span>

                          <span>
                            Capacity {capacity.toFixed(1)}
                          </span>
                        </div>
                      </div>
                    )}

                  {/* LOAD CHANGE */}
                  {event?.added_load !== undefined &&
                    Number(event.added_load) !== 0 && (
                      <div className="load-change">
                        <span>Network load transferred</span>
                        <strong>
                          +{Number(
                            event.added_load
                          ).toFixed(1)}
                        </strong>
                      </div>
                    )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <style>{`
        .timeline-panel {
          overflow: hidden;
        }

        .cascade-timeline {
          position: relative;
          max-height: 430px;
          overflow-y: auto;
          padding: 10px 8px 12px 0;
          scrollbar-width: thin;
        }

        .cascade-timeline::-webkit-scrollbar {
          width: 5px;
        }

        .cascade-timeline::-webkit-scrollbar-thumb {
          background: rgba(93, 67, 190, 0.25);
          border-radius: 10px;
        }

        .cascade-event {
          display: grid;
          grid-template-columns: 58px 42px minmax(0, 1fr);
          min-height: 118px;
          position: relative;
        }

        .cascade-time {
          padding-top: 13px;
          text-align: right;
          padding-right: 12px;
          color: #667085;
          white-space: nowrap;
          line-height: 1;
        }

        .cascade-time span {
          font-size: 11px;
          font-weight: 600;
          margin-right: 2px;
        }

        .cascade-time strong {
          font-size: 16px;
          color: #3f3a55;
        }

        .cascade-time small {
          display: block;
          margin-top: 4px;
          font-size: 9px;
          color: #98a2b3;
        }

        .cascade-track {
          position: relative;
          display: flex;
          justify-content: center;
        }

        .cascade-dot {
          position: relative;
          z-index: 2;
          width: 30px;
          height: 30px;
          margin-top: 7px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f3edff;
          border: 1px solid #d8c9ff;
          color: #7547df;
          font-size: 14px;
          box-shadow: 0 0 0 5px rgba(117, 71, 223, 0.05);
        }

        .cascade-event-initial .cascade-dot {
          background: #7547df;
          color: white;
          border-color: #7547df;
          box-shadow:
            0 0 0 5px rgba(117, 71, 223, 0.08),
            0 5px 14px rgba(117, 71, 223, 0.2);
        }

        .cascade-line {
          position: absolute;
          top: 37px;
          bottom: -4px;
          width: 1px;
          background: linear-gradient(
            to bottom,
            #d7cdf1,
            #e8e4f0
          );
        }

        .cascade-card {
          margin: 0 8px 14px 4px;
          padding: 14px 16px;
          border: 1px solid #e7e3ef;
          border-radius: 12px;
          background: #ffffff;
          box-shadow:
            0 2px 7px rgba(25, 20, 45, 0.035);
          transition:
            transform 0.15s ease,
            box-shadow 0.15s ease;
        }

        .cascade-card:hover {
          transform: translateY(-1px);
          box-shadow:
            0 5px 16px rgba(25, 20, 45, 0.07);
        }

        .cascade-event-initial .cascade-card {
          border-color: #d9cdf5;
          background: linear-gradient(
            135deg,
            #ffffff 0%,
            #faf8ff 100%
          );
        }

        .cascade-card-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
        }

        .cascade-asset-name {
          font-size: 14px;
          font-weight: 700;
          color: #242132;
          line-height: 1.25;
        }

        .cascade-asset-meta {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-top: 5px;
          font-size: 10px;
          color: #8a849b;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        .meta-divider {
          color: #c4becf;
        }

        .cascade-status {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 5px 9px;
          border-radius: 999px;
          font-size: 10px;
          font-weight: 700;
          white-space: nowrap;
          text-transform: uppercase;
          letter-spacing: 0.03em;
          background: #f2f4f7;
          color: #667085;
        }

        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: currentColor;
        }

        .status-failed {
          background: #fff0f0;
          color: #c73737;
        }

        .status-critical {
          background: #fff5e8;
          color: #c77716;
        }

        .status-degraded {
          background: #fff8e8;
          color: #a87500;
        }

        .status-near_failure {
          background: #fff5e8;
          color: #c77716;
        }

        .status-operational {
          background: #edf9f2;
          color: #218653;
        }

        .status-transition {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          margin-top: 10px;
          padding: 6px 9px;
          border-radius: 7px;
          background: #f7f6fa;
          border: 1px solid #ece9f2;
          font-size: 9px;
          font-weight: 600;
          color: #888294;
          text-transform: uppercase;
          letter-spacing: 0.035em;
        }

        .status-transition strong {
          color: #c73737;
        }

        .transition-arrow {
          color: #9c94aa;
          font-size: 12px;
        }

        .cascade-explanation {
          margin-top: 11px;
        }

        .explanation-label {
          margin-bottom: 4px;
          font-size: 9px;
          font-weight: 800;
          color: #7547df;
          letter-spacing: 0.08em;
        }

        .cascade-explanation p {
          margin: 0;
          color: #5f5a6d;
          font-size: 11px;
          line-height: 1.55;
        }

        .cascade-mechanism {
          display: flex;
          align-items: flex-start;
          gap: 6px;
          margin-top: 7px;
          padding: 7px 9px;
          border-radius: 7px;
          background: #faf9fc;
          color: #777181;
          font-size: 10px;
          line-height: 1.45;
        }

        .mechanism-icon {
          color: #7547df;
          font-weight: 800;
        }

        .load-impact {
          margin-top: 12px;
          padding-top: 10px;
          border-top: 1px solid #f0edf4;
        }

        .load-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 6px;
          font-size: 9px;
          color: #8a8495;
          letter-spacing: 0.05em;
        }

        .load-header strong {
          color: #5c5668;
          font-size: 10px;
          letter-spacing: 0;
        }

        .load-bar {
          position: relative;
          height: 5px;
          border-radius: 99px;
          background: #eeeaf3;
          overflow: visible;
        }

        .load-fill {
          height: 100%;
          border-radius: 99px;
          background: #7547df;
          transition: width 0.3s ease;
        }

        .load-fill.load-high {
          background: #d99a2b;
        }

        .load-fill.load-over {
          background: #d64545;
        }

        .capacity-marker {
          position: absolute;
          top: -3px;
          width: 1px;
          height: 11px;
          background: #77717f;
          opacity: 0.5;
        }

        .load-values {
          display: flex;
          justify-content: space-between;
          margin-top: 5px;
          font-size: 9px;
          color: #9a94a4;
        }

        .load-change {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 9px;
          padding: 6px 8px;
          border-radius: 6px;
          background: #fff8ee;
          color: #98713a;
          font-size: 9px;
        }

        .load-change strong {
          color: #c77716;
          font-size: 10px;
        }

        .timeline-empty {
          min-height: 180px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 14px;
          padding: 30px;
          color: #777181;
          text-align: left;
        }

        .timeline-empty-icon {
          width: 42px;
          height: 42px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #f3edff;
          color: #7547df;
          font-size: 22px;
        }

        .timeline-empty strong {
          display: block;
          color: #3f3a55;
          font-size: 13px;
          margin-bottom: 5px;
        }

        .timeline-empty p {
          max-width: 390px;
          margin: 0;
          font-size: 11px;
          line-height: 1.5;
        }

        @media (max-width: 700px) {
          .cascade-event {
            grid-template-columns: 45px 34px minmax(0, 1fr);
          }

          .cascade-time strong {
            font-size: 13px;
          }

          .cascade-card {
            padding: 12px;
          }

          .cascade-card-header {
            flex-direction: column;
            gap: 8px;
          }

          .cascade-status {
            align-self: flex-start;
          }
        }
      `}</style>
    </section>
  );
}

function formatStatus(status = "") {
  return String(status)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) =>
      char.toUpperCase()
    );
}

function formatType(type = "") {
  return String(type)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) =>
      char.toUpperCase()
    );
}

function getTypeIcon(type = "") {
  const value = String(type).toLowerCase();

  if (value.includes("hospital")) return "✚";
  if (value.includes("road")) return "↔";
  if (value.includes("signal")) return "●";
  if (value.includes("bridge")) return "═";
  if (value.includes("substation") || value.includes("power")) {
    return "ϟ";
  }
  if (value.includes("water") || value.includes("pump")) {
    return "≈";
  }
  if (value.includes("fire")) return "△";

  return "◆";
}