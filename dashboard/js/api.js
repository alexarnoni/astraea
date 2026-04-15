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
  return apiFetch("/v1/stats/summary");
}

export async function fetchUpcoming() {
  return apiFetch("/v1/asteroids/upcoming");
}

export async function fetchAsteroids({ limit, offset, hazardous, risk_label, start_date, end_date } = {}) {
  const params = new URLSearchParams();
  if (limit != null) params.append("limit", limit);
  if (offset != null) params.append("offset", offset);
  if (hazardous != null) params.append("hazardous", hazardous);
  if (risk_label != null) params.append("risk_label", risk_label);
  if (start_date != null) params.append("start_date", start_date);
  if (end_date != null) params.append("end_date", end_date);
  const qs = params.toString();
  return apiFetch("/v1/asteroids" + (qs ? "?" + qs : ""));
}

export async function fetchAsteroid(neo_id) {
  return apiFetch(`/v1/asteroids/${neo_id}`);
}

export async function fetchSolarEvents({ limit, offset, event_type } = {}) {
  const params = new URLSearchParams();
  if (limit != null) params.append("limit", limit);
  if (offset != null) params.append("offset", offset);
  if (event_type != null) params.append("event_type", event_type);
  const qs = params.toString();
  return apiFetch("/v1/solar-events" + (qs ? "?" + qs : ""));
}

export async function fetchEarthDirected() {
  return apiFetch("/v1/solar-events/earth-directed");
}

export async function fetchSolarEvent(eventId){
  return apiFetch(`/v1/solar-events/${eventId}`);
}