import React, { useMemo } from "react";

export default function CausalChain({
  selectedNode = null,
  result = null,
  chain = [],
}) {
  const causalChains = result?.causal_chains || {};

  const selectedChain = useMemo(() => {
    if (!selectedNode) {
      return [];
    }

    if (Array.isArray(chain) && chain.length > 0) {
      return chain;
    }

    const possibleChain =
      causalChains[selectedNode.id];

    if (Array.isArray(possibleChain)) {
      return possibleChain;
    }

    /*
     * Backend may return causal chains keyed differently.
     * Search every chain for the selected node.
     */
    for (const value of Object.values(causalChains)) {
      if (!Array.isArray(value)) {
        continue;
      }

      const containsNode = value.some(
        (item) =>
          item?.node_id === selectedNode.id
      );

      if (containsNode) {
        return value;
      }
    }

    return [];
  }, [
    selectedNode,
    chain,
    causalChains,
  ]);

  return (
    <section className="panel causal-panel">
      <div className="panel-title">
        05 · WHY DID THIS FAIL?
      </div>

      {!selectedNode ? (
        <div className="empty-state">
          Click an asset on the map to inspect
          causality.
        </div>
      ) : (
        <>
          <div className="selected-asset">
            <div className="selected-id">
              {selectedNode.id}
            </div>

            <div className="selected-asset-info">
              <strong>
                {selectedNode.name ||
                  selectedNode.id}
              </strong>

              <span>
                {selectedNode.type || "asset"} ·{" "}
                {selectedNode.status || "unknown"}
              </span>
            </div>
          </div>

          <div className="chain">
            {selectedChain.length > 0 ? (
              selectedChain.map((item, index) => (
                <div
                  className="chain-item"
                  key={`${item?.node_id || "node"}-${index}`}
                >
                  <div className="chain-node">
                    {item?.node_id || "—"}
                  </div>

                  <div className="chain-content">
                    <strong>
                      {item?.node_name ||
                        item?.node_id ||
                        "Infrastructure asset"}
                    </strong>

                    {item?.time !== undefined && (
                      <span className="chain-time">
                        failed at {item.time} min
                      </span>
                    )}

                    <p>
                      {item?.reason ||
                        "Propagation event recorded."}
                    </p>
                  </div>

                  {index <
                    selectedChain.length - 1 && (
                    <div className="chain-arrow">
                      ↓
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p className="helper">
                No causal event was recorded for this
                asset in the selected simulation.
              </p>
            )}
          </div>
        </>
      )}
    </section>
  );
}