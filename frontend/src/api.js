//frontend/src/api.js
const API_BASE = "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  if (!response.ok) {
    let errorMessage = `Erreur API: ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMessage = typeof errorData.detail === "string"
          ? errorData.detail
          : JSON.stringify(errorData.detail);
      }
    } catch {
      // rien
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export async function getStatus() {
  return request("/status");
}

export async function getTrades() {
  return request("/trades");
}

export async function getLogs() {
  return request("/logs");
}

export async function getSettings() {
  return request("/settings");
}

export async function startBot() {
  return request("/start", { method: "POST" });
}

export async function stopBot() {
  return request("/stop", { method: "POST" });
}

export async function tickBot() {
  return request("/tick", { method: "POST" });
}

export async function resetBot() {
  return request("/reset", { method: "POST" });
}

export async function resetSettings() {
  return request("/settings/reset", { method: "POST" });
}

export async function updateSettings(payload) {
  return request("/settings/update", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}