import React, {
  useEffect,
  useMemo,
  useRef,
} from "react";

import L from "leaflet";
import "leaflet/dist/leaflet.css";

const TYPE_ICON = {
  substation: "⚡",
  bridge: "🌉",
  pump: "💧",
  hospital: "✚",
  emergency: "🚑",
  signal: "⚠",
  road: "━",
  zone: "⌂",
  facility: "🏭",
  reservoir: "💧",
  water: "💧",
  control: "◈",
};

const STATUS_COLOR = {
  operational: "#4ade80",
  degraded: "#facc15",
  critical: "#fb923c",
  near_failure: "#c084fc",
  failed: "#ef4444",
};

const STATUS_LABEL = {
  operational: "Operational",
  degraded: "Degraded",
  critical: "Critical",
  near_failure: "Near failure",
  failed: "Failed",
};

/* =========================================================
   STATUS HELPERS
========================================================= */

function normalizeStatus(status) {
  const value = String(status || "operational")
    .toLowerCase()
    .trim()
    .replaceAll(" ", "_")
    .replaceAll("-", "_");

  return STATUS_COLOR[value]
    ? value
    : "operational";
}

function getSimulationNodes(result) {
  if (!result) {
    return [];
  }

  const rawNodes = result.nodes;

  if (Array.isArray(rawNodes)) {
    return rawNodes;
  }

  if (
    rawNodes &&
    typeof rawNodes === "object"
  ) {
    return Object.entries(rawNodes).map(
      ([id, node]) => ({
        ...(node || {}),
        id: node?.id || id,
      })
    );
  }

  return [];
}

function buildStatusMap(result) {
  const statusMap = {};

  const simulationNodes =
    getSimulationNodes(result);

  simulationNodes.forEach((node) => {
    if (!node?.id) {
      return;
    }

    if (node.status) {
      statusMap[node.id] =
        normalizeStatus(node.status);
    }
  });

  const events = Array.isArray(result?.events)
    ? result.events
    : [];

  events.forEach((event) => {
    const id =
      event?.node_id ??
      event?.id;

    if (!id) {
      return;
    }

    if (event?.status) {
      statusMap[id] =
        normalizeStatus(event.status);
    }
  });

  return statusMap;
}

/* =========================================================
   CASCADE HELPERS
========================================================= */

function getAffectedIds(result, statusMap) {
  const affected = new Set();

  Object.entries(statusMap).forEach(
    ([id, status]) => {
      if (status !== "operational") {
        affected.add(id);
      }
    }
  );

  const events = Array.isArray(result?.events)
    ? result.events
    : [];

  events.forEach((event) => {
    const id =
      event?.node_id ??
      event?.id;

    if (id) {
      affected.add(id);
    }

    if (event?.parent_id) {
      affected.add(event.parent_id);
    }
  });

  return affected;
}

function getCascadeEdgeKeys(result) {
  const keys = new Set();

  const events = Array.isArray(result?.events)
    ? result.events
    : [];

  events.forEach((event) => {
    const parent =
      event?.parent_id;

    const child =
      event?.node_id ??
      event?.id;

    if (
      parent &&
      child
    ) {
      keys.add(
        `${parent}->${child}`
      );
    }
  });

  return keys;
}

/* =========================================================
   MAP POSITIONING
========================================================= */

/*
 * The backend coordinates are small.
 *
 * We intentionally expand them onto a much larger visual
 * canvas so the city network has room to breathe.
 *
 * Important:
 * - Larger canvas
 * - Larger minimum separation
 * - Deterministic positioning
 * - No random movement between renders
 */

function buildDisplayPositions(nodes) {
  const positions = {};

  if (
    !Array.isArray(nodes) ||
    nodes.length === 0
  ) {
    return positions;
  }

  const raw = nodes.map((node) => ({
    id: node.id,
    x: Number(node?.x ?? 0),
    y: Number(node?.y ?? 0),
  }));

  const minX = Math.min(
    ...raw.map((p) => p.x)
  );

  const maxX = Math.max(
    ...raw.map((p) => p.x)
  );

  const minY = Math.min(
    ...raw.map((p) => p.y)
  );

  const maxY = Math.max(
    ...raw.map((p) => p.y)
  );

  const rangeX =
    Math.max(1, maxX - minX);

  const rangeY =
    Math.max(1, maxY - minY);

  /*
   * MUCH larger display canvas.
   *
   * Previously:
   * 35 -> 205
   *
   * Now:
   * 25 -> 285
   */
  const points = raw.map((point) => ({
    id: point.id,

    x:
      25 +
      ((point.x - minX) / rangeX) * 260,

    y:
      25 +
      ((point.y - minY) / rangeY) * 260,
  }));

  /*
   * Push nearby nodes apart.
   *
   * Previous minimum:
   * 14
   *
   * New minimum:
   * 23
   */
  for (
    let iteration = 0;
    iteration < 24;
    iteration += 1
  ) {
    for (
      let i = 0;
      i < points.length;
      i += 1
    ) {
      for (
        let j = i + 1;
        j < points.length;
        j += 1
      ) {
        const a = points[i];
        const b = points[j];

        const dx =
          b.x - a.x;

        const dy =
          b.y - a.y;

        const distance =
          Math.sqrt(
            dx * dx +
            dy * dy
          ) || 0.001;

        const minimumDistance = 23;

        if (
          distance <
          minimumDistance
        ) {
          const push =
            (minimumDistance -
              distance) /
            2;

          const nx =
            dx / distance;

          const ny =
            dy / distance;

          a.x -=
            nx * push;

          a.y -=
            ny * push;

          b.x +=
            nx * push;

          b.y +=
            ny * push;
        }
      }
    }
  }

  /*
   * Keep everything inside the visual canvas.
   */
  points.forEach((point) => {
    point.x = Math.max(
      15,
      Math.min(295, point.x)
    );

    point.y = Math.max(
      15,
      Math.min(295, point.y)
    );
  });

  points.forEach((point) => {
    positions[point.id] = [
      point.y,
      point.x,
    ];
  });

  return positions;
}

function getCoords(
  node,
  displayPositions
) {
  if (
    node?.id &&
    displayPositions?.[node.id]
  ) {
    return displayPositions[node.id];
  }

  const x =
    Number(node?.x ?? 0);

  const y =
    Number(node?.y ?? 0);

  return [
    25 + y * 4,
    25 + x * 4,
  ];
}

/* =========================================================
   NODE ICON
========================================================= */

function createNodeIcon(
  node,
  status,
  selected,
  incident,
  affected
) {
  const safeStatus =
    normalizeStatus(status);

  const color =
    STATUS_COLOR[safeStatus];

  const icon =
    TYPE_ICON[node?.type] ||
    "●";

  /*
   * Slightly reduce the icon size from the previous version.
   *
   * The map itself is now much more spacious, so we don't
   * need enormous markers.
   */
  const size =
    selected
      ? 48
      : incident
        ? 44
        : affected
          ? 34
          : 28;

  const opacity =
    affected ||
    selected ||
    incident
      ? 1
      : 0.68;

  const border =
    selected
      ? "3px solid #ffffff"
      : incident
        ? "3px solid #a78bfa"
        : affected
          ? `2px solid ${color}`
          : "2px solid rgba(255,255,255,0.55)";

  const shadow =
    selected
      ? "0 0 0 5px rgba(139,92,246,.30), 0 8px 22px rgba(0,0,0,.45)"
      : incident
        ? "0 0 0 4px rgba(124,58,237,.20), 0 7px 18px rgba(0,0,0,.38)"
        : affected
          ? "0 5px 15px rgba(0,0,0,.38)"
          : "0 3px 9px rgba(0,0,0,.22)";

  return L.divIcon({
    className:
      "digital-twin-node",

    html: `
      <div
        style="
          width:${size}px;
          height:${size}px;
          border-radius:${selected ? 15 : 11}px;
          background-color:${color};
          border:${border};
          box-shadow:${shadow};
          display:flex;
          align-items:center;
          justify-content:center;
          font-size:${selected ? 21 : affected ? 15 : 12}px;
          color:#0b1026;
          font-weight:900;
          position:relative;
          box-sizing:border-box;
          opacity:${opacity};
          transition:
            background-color .25s ease,
            transform .2s ease,
            box-shadow .2s ease,
            opacity .2s ease;
        "
      >
        ${icon}

        ${
          incident
            ? `
              <span
                style="
                  position:absolute;
                  top:-7px;
                  right:-7px;
                  width:14px;
                  height:14px;
                  border-radius:50%;
                  background:#7c3aed;
                  border:2px solid white;
                  box-sizing:border-box;
                "
              ></span>
            `
            : ""
        }
      </div>
    `,

    iconSize: [
      size,
      size,
    ],

    iconAnchor: [
      size / 2,
      size / 2,
    ],
  });
}

/* =========================================================
   LABEL
========================================================= */

function createLabel(
  node,
  status,
  selected
) {
  const safeStatus =
    normalizeStatus(status);

  const color =
    STATUS_COLOR[safeStatus];

  return L.divIcon({
    className:
      "asset-label",

    html: `
      <div
        style="
          margin-top:${selected ? 27 : 22}px;
          margin-left:${selected ? -6 : 0}px;
          background:rgba(8,11,30,.96);
          border:1px solid ${color};
          color:white;
          padding:5px 8px;
          border-radius:6px;
          font-size:${selected ? 11 : 10}px;
          font-weight:700;
          line-height:1.15;
          white-space:nowrap;
          box-shadow:0 4px 11px rgba(0,0,0,.28);
        "
      >
        ${node?.name || node?.id || ""}
      </div>
    `,

    iconSize: [
      0,
      0,
    ],

    iconAnchor: [
      0,
      0,
    ],
  });
}

/* =========================================================
   CITY MAP
========================================================= */

export default function CityMap({
  network = {
    nodes: [],
    edges: [],
  },

  result = null,

  selectedNode = null,

  setSelectedNode = () => {},

  incidentAsset = null,
}) {
  const mapContainerRef =
    useRef(null);

  const mapRef =
    useRef(null);

  const layersRef =
    useRef({
      grid: null,
      edges: null,
      nodes: null,
      labels: null,
    });

  const statusMap =
    useMemo(
      () =>
        buildStatusMap(result),
      [result]
    );

  const affectedIds =
    useMemo(
      () =>
        getAffectedIds(
          result,
          statusMap
        ),
      [
        result,
        statusMap,
      ]
    );

  const cascadeEdgeKeys =
    useMemo(
      () =>
        getCascadeEdgeKeys(result),
      [result]
    );

  const displayPositions =
    useMemo(
      () =>
        buildDisplayPositions(
          Array.isArray(
            network?.nodes
          )
            ? network.nodes
            : []
        ),
      [network]
    );

  /* =======================================================
     CREATE MAP
  ======================================================= */

  useEffect(() => {
    if (
      !mapContainerRef.current ||
      mapRef.current
    ) {
      return;
    }

    const map =
      L.map(
        mapContainerRef.current,
        {
          crs: L.CRS.Simple,

          minZoom: -2,

          maxZoom: 3,

          zoomControl: false,

          attributionControl:
            false,
        }
      );

    map.setView(
      [150, 150],
      -1
    );

    L.control
      .zoom({
        position:
          "bottomright",
      })
      .addTo(map);

    mapRef.current =
      map;

    /*
     * Give Leaflet time to calculate the container
     * dimensions before the first render.
     */
    setTimeout(() => {
      if (mapRef.current) {
        mapRef.current.invalidateSize();
      }
    }, 100);

    return () => {
      map.remove();

      mapRef.current =
        null;
    };
  }, []);

  /* =======================================================
     GRID
  ======================================================= */

  useEffect(() => {
    const map =
      mapRef.current;

    if (!map) {
      return;
    }

    if (
      layersRef.current.grid
    ) {
      map.removeLayer(
        layersRef.current.grid
      );
    }

    const grid =
      L.layerGroup();

    /*
     * Larger grid to match the new 300 x 300 map.
     */
    for (
      let i = 0;
      i <= 300;
      i += 15
    ) {
      L.polyline(
        [
          [i, 0],
          [i, 300],
        ],
        {
          color:
            "#273154",

          weight: 1,

          opacity: 0.18,
        }
      ).addTo(grid);

      L.polyline(
        [
          [0, i],
          [300, i],
        ],
        {
          color:
            "#273154",

          weight: 1,

          opacity: 0.18,
        }
      ).addTo(grid);
    }

    grid.addTo(map);

    layersRef.current.grid =
      grid;
  }, []);

  /* =======================================================
     DRAW NETWORK
  ======================================================= */

  useEffect(() => {
    const map =
      mapRef.current;

    if (!map) {
      return;
    }

    const nodes =
      Array.isArray(
        network?.nodes
      )
        ? network.nodes
        : [];

    const edges =
      Array.isArray(
        network?.edges
      )
        ? network.edges
        : [];

    /*
     * Remove previous layers.
     */
    if (
      layersRef.current.edges
    ) {
      map.removeLayer(
        layersRef.current.edges
      );
    }

    if (
      layersRef.current.nodes
    ) {
      map.removeLayer(
        layersRef.current.nodes
      );
    }

    if (
      layersRef.current.labels
    ) {
      map.removeLayer(
        layersRef.current.labels
      );
    }

    /* =====================================================
       EDGES
    ===================================================== */

    const edgeLayer =
      L.layerGroup();

    edges.forEach(
      (edge) => {
        const source =
          nodes.find(
            (node) =>
              node.id ===
              edge.source
          );

        const target =
          nodes.find(
            (node) =>
              node.id ===
              edge.target
          );

        if (
          !source ||
          !target
        ) {
          return;
        }

        const isDependency =
          edge.kind ===
          "dependency";

        const cascadeKey =
          `${edge.source}->${edge.target}`;

        const isCascadePath =
          cascadeEdgeKeys.has(
            cascadeKey
          );

        let edgeColor =
          isDependency
            ? "#6d5bb3"
            : "#475569";

        let edgeWeight =
          isDependency
            ? 1.2
            : 1.5;

        let edgeOpacity =
          isDependency
            ? 0.20
            : 0.28;

        let dashArray =
          isDependency
            ? "5 7"
            : undefined;

        /*
         * Cascade paths become visually prominent.
         */
        if (
          isCascadePath
        ) {
          edgeColor =
            "#a855f7";

          edgeWeight =
            3;

          edgeOpacity =
            0.9;

          dashArray =
            "7 5";
        }

        /*
         * Affected infrastructure gets slightly stronger
         * connections without making the entire network glow.
         */
        else if (
          affectedIds.has(
            edge.source
          ) ||
          affectedIds.has(
            edge.target
          )
        ) {
          edgeColor =
            "#8b5cf6";

          edgeWeight =
            1.8;

          edgeOpacity =
            0.48;

          if (
            isDependency
          ) {
            dashArray =
              "5 5";
          }
        }

        L.polyline(
          [
            getCoords(
              source,
              displayPositions
            ),

            getCoords(
              target,
              displayPositions
            ),
          ],
          {
            color:
              edgeColor,

            weight:
              edgeWeight,

            opacity:
              edgeOpacity,

            dashArray,
          }
        ).addTo(
          edgeLayer
        );
      }
    );

    edgeLayer.addTo(map);

    /* =====================================================
       NODES
    ===================================================== */

    const nodeLayer =
      L.layerGroup();

    const labelLayer =
      L.layerGroup();

    nodes.forEach(
      (node) => {
        const status =
          statusMap[node.id] ||
          normalizeStatus(
            node.status ||
              "operational"
          );

        const isSelected =
          selectedNode?.id ===
          node.id;

        const isIncident =
          incidentAsset ===
          node.id;

        const isAffected =
          affectedIds.has(
            node.id
          );

        const marker =
          L.marker(
            getCoords(
              node,
              displayPositions
            ),
            {
              icon:
                createNodeIcon(
                  node,
                  status,
                  isSelected,
                  isIncident,
                  isAffected
                ),

              zIndexOffset:
                isSelected
                  ? 3000
                  : isIncident
                    ? 2500
                    : isAffected
                      ? 1500
                      : 0,
            }
          );

        marker.on(
          "click",
          () => {
            setSelectedNode({
              ...node,
              status,
            });
          }
        );

        marker.bindTooltip(
          `
            <strong>
              ${node.name || node.id}
            </strong>
            <br />
            ${node.type || "asset"}
            <br />
            <span
              style="
                color:${STATUS_COLOR[status]}
              "
            >
              ${STATUS_LABEL[status]}
            </span>
          `,
          {
            direction:
              "top",

            offset: [
              0,
              -18,
            ],

            className:
              "map-tooltip",
          }
        );

        marker.addTo(
          nodeLayer
        );

        /*
         * IMPORTANT CHANGE
         *
         * Do NOT show labels for every affected asset.
         *
         * This was the main source of visual clutter.
         *
         * Labels now appear only for:
         *
         * 1. The incident asset
         * 2. The currently selected asset
         *
         * Hovering any other asset still shows its tooltip.
         */
        const shouldShowLabel =
          isIncident ||
          isSelected;

        if (
          shouldShowLabel
        ) {
          L.marker(
            getCoords(
              node,
              displayPositions
            ),
            {
              icon:
                createLabel(
                  node,
                  status,
                  isSelected
                ),

              interactive:
                false,

              zIndexOffset:
                isSelected
                  ? 2900
                  : 2400,
            }
          ).addTo(
            labelLayer
          );
        }
      }
    );

    nodeLayer.addTo(map);

    labelLayer.addTo(map);

    layersRef.current.edges =
      edgeLayer;

    layersRef.current.nodes =
      nodeLayer;

    layersRef.current.labels =
      labelLayer;

    /* =====================================================
       FIT MAP
    ===================================================== */

    if (
      nodes.length > 0
    ) {
      const bounds =
        L.latLngBounds(
          nodes.map(
            (node) =>
              getCoords(
                node,
                displayPositions
              )
          )
        );

      if (
        bounds.isValid()
      ) {
        map.fitBounds(
          bounds.pad(0.18)
        );
      }
    }

    /*
     * Fix Leaflet rendering after React/Vite layout updates.
     */
    setTimeout(() => {
      if (mapRef.current) {
        mapRef.current.invalidateSize();
      }
    }, 50);

  }, [
    network,
    result,
    statusMap,
    affectedIds,
    cascadeEdgeKeys,
    displayPositions,
    selectedNode,
    incidentAsset,
    setSelectedNode,
  ]);

  /* =======================================================
     DISPLAY DATA
  ======================================================= */

  const eventCount =
    Array.isArray(
      result?.events
    )
      ? result.events.length
      : 0;

  const affectedCount =
    affectedIds.size;

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <section className="map-card">

      <div
        className="map-container"
        ref={
          mapContainerRef
        }
      />

      {/* =================================================
          MAP HEADER
      ================================================= */}

      <div className="map-overlay-header">
        <div>
          <span className="map-kicker">
            CITY NETWORK
          </span>

          <strong>
            {result
              ? `${eventCount} propagation events`
              : "Awaiting simulation"}
          </strong>

          <span>
            {" "}
            · click an asset to inspect
            causality
          </span>
        </div>
      </div>

      {/* =================================================
          CASCADE INDICATOR
      ================================================= */}

      {result &&
        affectedCount > 0 && (
          <div
            style={{
              position:
                "absolute",

              left:
                "22px",

              top:
                "88px",

              zIndex:
                500,

              padding:
                "7px 11px",

              borderRadius:
                "8px",

              background:
                "rgba(15,18,45,.92)",

              border:
                "1px solid rgba(168,85,247,.45)",

              color:
                "#ddd6fe",

              fontSize:
                "11px",

              fontWeight:
                700,

              boxShadow:
                "0 5px 15px rgba(0,0,0,.2)",
            }}
          >
            <span
              style={{
                display:
                  "inline-block",

                width:
                  "7px",

                height:
                  "7px",

                borderRadius:
                  "50%",

                background:
                  "#a855f7",

                marginRight:
                  "7px",
              }}
            />

            {affectedCount}
            {" "}
            affected assets
          </div>
        )}

      {/* =================================================
          LEGEND
      ================================================= */}

      <div className="map-legend">
        {Object.entries(
          STATUS_LABEL
        ).map(
          ([
            status,
            label,
          ]) => (
            <div
              className="legend-item"
              key={status}
            >
              <span
                className="legend-dot"
                style={{
                  background:
                    STATUS_COLOR[
                      status
                    ],
                }}
              />

              {label}
            </div>
          )
        )}
      </div>

      {/* =================================================
          FOOTER
      ================================================= */}

      <div className="map-footer-left">
        SYNTHETIC URBAN NETWORK
      </div>

      <div className="map-footer-right">
        DEPENDENCY GRAPH · CAPACITY MODEL
      </div>

    </section>
  );
}