const API_BASE_URL = "http://127.0.0.1:8000";

/*
 * Generic JSON request helper
 */
async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorData = await response.json();

      if (errorData?.detail) {
        message = errorData.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(message);
  }

  return response.json();
}

/*
 * Get the synthetic city network.
 */
export async function getNetwork() {
  return request(`${API_BASE_URL}/network`);
}

/*
 * Get available incident types and interventions.
 */
export async function getScenarios() {
  return request(`${API_BASE_URL}/scenarios`);
}

/*
 * Run a normal cascade simulation.
 */
export async function runSimulation(payload) {
  return request(`${API_BASE_URL}/simulation/run`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/*
 * Compare baseline vs intervention.
 */
export async function compareSimulation(payload) {
  return request(`${API_BASE_URL}/simulation/compare`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}