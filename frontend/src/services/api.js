const API_BASE_URL = "https://projecty-xr9c.onrender.com";

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

export async function getNetwork() {
  return request(`${API_BASE_URL}/network`);
}

export async function getScenarios() {
  return request(`${API_BASE_URL}/scenarios`);
}

export async function runSimulation(payload) {
  return request(`${API_BASE_URL}/simulation/run`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function compareSimulation(payload) {
  return request(`${API_BASE_URL}/simulation/compare`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function reverseSimulation(payload) {
  return request(`${API_BASE_URL}/simulation/reverse`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}