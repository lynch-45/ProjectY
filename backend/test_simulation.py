from network.city_graph import build_city
from simulation.engine import simulate, compare_simulations

city = build_city()

result = simulate(city, "power_failure", "S4", 1.0, 60, [])
assert result["scenario"]["asset_id"] == "S4"
assert len(result["events"]) >= 1
assert result["metrics"]["failed_assets"] >= 1

comparison = compare_simulations(city, "power_failure", "S4", 1.0, 60, ["backup_signal_power"])
assert comparison["baseline"]["metrics"]["failed_assets"] >= 1

print("Simulation smoke test passed.")
print("Baseline metrics:", result["metrics"])
print("Intervention deltas:", comparison["improvements"])
