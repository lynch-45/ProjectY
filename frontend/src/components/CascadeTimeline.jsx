import React from "react";

export default function CascadeTimeline({ result = null }) {
  const events = Array.isArray(result?.events)
    ? result.events
    : [];

  /*
   * Do not use events.length here.
   * Using the first item is also safe because events
   * is guaranteed to be an array above.
   */
  const hasEvents = events[0] !== undefined;

  return (
    <section className="panel timeline-panel">
      <div className="panel-title">
        04 · CASCADE TIMELINE
      </div>

      {!hasEvents ? (
        <div className="empty-state">
          <strong>No cascade yet</strong>

          <p>
            Configure an incident and click
            "Run Cascade" to see how failure
            propagates through the network.
          </p>
        </div>
      ) : (
        <div className="timeline">
          {events.map((event, index) => {
            const time = Number(
              event?.time ?? 0
            );

            const nodeId =
              event?.node_id ??
              event?.id ??
              "—";

            const nodeName =
              event?.node_name ??
              event?.name ??
              nodeId;

            const status =
              event?.status ??
              "unknown";

            const reason =
              event?.reason ??
              "Infrastructure state changed.";

            return (
              <div
                className="timeline-item"
                key={`${nodeId}-${time}-${index}`}
              >
                <div className="timeline-time">
                  T+{time}m
                </div>

                <div className="timeline-dot" />

                <div className="timeline-content">
                  <div>
                    <strong>
                      {nodeName}
                    </strong>

                    <span
                      className={`timeline-status status-${status}`}
                    >
                      {formatStatus(status)}
                    </span>
                  </div>

                  <p>
                    {reason}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
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