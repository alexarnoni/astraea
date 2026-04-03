// api.js — centraliza todas as chamadas à API FastAPI

import { CONFIG } from "./config.js";

async function apiFetch(path) {
  let res;
  try {
    res = await fetch(CONFIG.API_BASE_URL + path);
  } catch {
    throw new Error("Não foi possível conectar à API. Verifique sua conexão.");
  }

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error("Recurso não encontrado.");
    }
    if (res.status >= 500) {
      throw new Error("Erro no servidor. Tente novamente mais tarde.");
    }
    throw new Error(`Erro ${res.status}: não foi possível carregar os dados.`);
  }

  return res.json();
}

export async function fetchStats() {
  return apiFetch("/stats/summary");
}

export async function fetchUpcoming() {
  return apiFetch("/asteroids/upcoming");
}

export async function fetchAsteroids({ limit, offset, hazardous, risk_label } = {}) {
  const params = new URLSearchParams();
  if (limit != null) params.append("limit", limit);
  if (offset != null) params.append("offset", offset);
  if (hazardous != null) params.append("hazardous", hazardous);
  if (risk_label != null) params.append("risk_label", risk_label);
  const qs = params.toString();
  return apiFetch("/asteroids" + (qs ? "?" + qs : ""));
}

export async function fetchAsteroid(neo_id) {
  return apiFetch(`/asteroids/${neo_id}`);
}

export async function fetchSolarEvents({ limit, offset, event_type } = {}) {
  const params = new URLSearchParams();
  if (limit != null) params.append("limit", limit);
  if (offset != null) params.append("offset", offset);
  if (event_type != null) params.append("event_type", event_type);
  const qs = params.toString();
  return apiFetch("/solar-events" + (qs ? "?" + qs : ""));
}

export async function fetchEarthDirected() {
  return apiFetch("/solar-events/earth-directed");
}
