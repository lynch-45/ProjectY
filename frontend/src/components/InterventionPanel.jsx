export default function InterventionPanel({
  scenarios, interventions, setInterventions, onCompare, loading
}) {
  const toggle = (id) => {
    setInterventions(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  return (
    <section className="panel">
      <div className="panel-title">02 · WHAT-IF INTERVENTION</div>
      <p className="helper">Protect the network, then compare the same incident again.</p>

      {Object.entries(scenarios.interventions || {}).map(([key, value]) => (
        <button
          key={key}
          className={`intervention ${interventions.includes(key) ? "selected" : ""}`}
          onClick={() => toggle(key)}
        >
          <span>{interventions.includes(key) ? "✓" : "+"}</span>
          <div>
            <strong>{value.label}</strong>
            <small>{value.description}</small>
          </div>
        </button>
      ))}

      <button
        className="secondary"
        disabled={loading || interventions.length === 0}
        onClick={onCompare}
      >
        {loading ? "COMPARING…" : "COMPARE BEFORE / AFTER"}
      </button>
    </section>
  );
}