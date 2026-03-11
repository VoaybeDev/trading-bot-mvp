// frontend/src/api.js
// La cle API est lue depuis la variable d'environnement Vite
// Ajoutez VITE_API_KEY=votre_cle dans votre fichier .env du dossier frontend
const API_BASE  = import.meta.env.VITE_API_URL  || "http://127.0.0.1:8000";
const API_KEY   = import.meta.env.VITE_API_KEY  || "";

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `Erreur API: ${response.status}`;
    if (response.status === 403) {
      errorMessage = "Acces refuse : cle API invalide ou manquante (X-API-Key)";
    }
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMessage = typeof errorData.detail === "string"
          ? errorData.detail
          : JSON.stringify(errorData.detail);
      }
    } catch {
      // reponse non-JSON, on garde le message par defaut
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export async function getStatus()        { return request("/status"); }
export async function getTrades()        { return request("/trades"); }
export async function getLogs()          { return request("/logs"); }
export async function getSettings()      { return request("/settings"); }
export async function startBot()         { return request("/start",           { method: "POST" }); }
export async function stopBot()          { return request("/stop",            { method: "POST" }); }
export async function tickBot()          { return request("/tick",            { method: "POST" }); }
export async function resetBot()         { return request("/reset",           { method: "POST" }); }
export async function resetSettings()    { return request("/settings/reset",  { method: "POST" }); }
export async function getHealth() { return request("/health"); }
export async function updateSettings(payload) {
  return request("/settings/update", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}