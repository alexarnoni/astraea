// home.js — lógica da página inicial (status-bar, hero, stat-cards, tabela upcoming, eventos recentes)

import { fetchStats, fetchUpcoming, fetchSolarEvents } from "./api.js";
import {
  renderRiskBadge,
  renderStatCard,
  showSpinner,
  showError,
  setActiveNav,
  formatDate,
  formatNumber,
} from "./ui.js";

// ─── Status Bar ────────────────────────────────────────────────────────────────

function renderStatusBar() {
  const bar = document.getElementById("status-bar");
  if (!bar) return;
  const today = new Date().toLocaleDateString("pt-BR");
  bar.innerHTML = `<span class="status-bar__dot"></span> Pipeline ativo — última coleta: ${today}`;
}

// ─── Hero ──────────────────────────────────────────────────────────────────────

function renderHero(asteroids) {
  const h1 = document.querySelector("#hero h1.hero__title");
  if (!h1) return;
  h1.innerHTML = `<span class="hero__count">${asteroids.length}</span> objetos próximos à Terra rastreados nos próximos 7 dias`;
}

// ─── Stat Cards ────────────────────────────────────────────────────────────────

function renderStatCards(stats) {
  const container = document.getElementById("stat-cards");
  if (!container) return;

  const closestValue = `${formatNumber(stats.closest_approach_lunar, 2)} LD`;
  const closestLabel = stats.closest_asteroid_name
    ? `<span style="font-size:0.75rem;color:var(--muted);display:block;margin-top:0.25rem">${stats.closest_asteroid_name}</span>`
    : "";

  const cards = [
    renderStatCard(
      formatNumber(stats.total_asteroids, 0),
      "Objetos rastreados",
      "Total de asteroides monitorados no banco de dados."
    ),
    renderStatCard(
      formatNumber(stats.hazardous_count, 0),
      "Potencialmente perigosos",
      "Asteroides classificados pela NASA como potencialmente perigosos (PHA) — objetos com diâmetro > 140m e distância < 0,05 UA."
    ),
    renderStatCard(
      closestValue + closestLabel,
      "Aproximação mais próxima",
      "Distância em Distâncias Lunares (LD). 1 LD ≈ 384.400 km."
    ),
    renderStatCard(
      formatNumber(stats.total_solar_events, 0),
      "Eventos solares",
      "Total de eventos solares registrados (CMEs e tempestades geomagnéticas)."
    ),
  ];

  container.innerHTML = cards.join("");
}

// ─── Upcoming Table ────────────────────────────────────────────────────────────

function renderUpcomingTable(asteroids) {
  const container = document.getElementById("upcoming-table");
  if (!container) return;

  if (!asteroids.length) {
    container.innerHTML = `<p class="error-msg" style="color:var(--muted)">Nenhuma aproximação prevista nos próximos dias.</p>`;
    return;
  }

  const rows = asteroids
    .map(
      (a) => `<tr onclick="location.href='detalhe.html?id=${a.neo_id}'" style="cursor:pointer">
      <td>${a.name ?? "—"}</td>
      <td>${formatDate(a.close_approach_date)}</td>
      <td>${formatNumber(a.miss_distance_lunar, 2)} LD<br><small>${formatNumber(a.miss_distance_km, 0)} km</small></td>
      <td>${formatNumber(a.relative_velocity_km_s, 1)} km/s</td>
      <td>${formatNumber(a.estimated_diameter_min_km, 2)}–${formatNumber(a.estimated_diameter_max_km, 2)} km</td>
      <td>${renderRiskBadge(a.risk_label_ml)}</td>
    </tr>`
    )
    .join("");

  container.innerHTML = `<table class="data-table">
    <thead>
      <tr>
        <th>Asteroide</th>
        <th>Data</th>
        <th>Distância</th>
        <th>Velocidade</th>
        <th>Diâmetro</th>
        <th>Risco</th>
      </tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>`;
}

// ─── Recent Events ─────────────────────────────────────────────────────────────

const EVENT_DESCRIPTIONS = {
  CME: "Ejeção de massa coronal — nuvem de plasma lançada pelo Sol.",
  GST: "Tempestade geomagnética — perturbação no campo magnético terrestre.",
};

function renderRecentEvents(events) {
  const container = document.getElementById("recent-events");
  if (!container) return;

  if (!events.length) {
    container.innerHTML = `<p class="error-msg" style="color:var(--muted)">Nenhum evento solar recente.</p>`;
    return;
  }

  const cards = events
    .map((e) => {
      const type = e.event_type ?? "—";
      const description = EVENT_DESCRIPTIONS[type] ?? "";
      const speedLine =
        e.speed_km_s != null
          ? `<p class="event-card__detail">Velocidade: ${formatNumber(e.speed_km_s, 0)} km/s</p>`
          : "";
      const kpLine =
        e.kp_index_max != null
          ? `<p class="event-card__detail">Índice Kp: ${e.kp_index_max}</p>`
          : "";
      const noteLine = e.note
        ? `<p class="event-card__note">${e.note}</p>`
        : "";

      return `<div class="event-card">
        <div class="event-card__header">
          <span class="badge badge--event">${type}</span>
          <span class="event-card__date">${formatDate(e.event_date)}</span>
        </div>
        ${description ? `<p class="event-card__description">${description}</p>` : ""}
        ${speedLine}${kpLine}${noteLine}
      </div>`;
    })
    .join("");

  container.innerHTML = cards;
}

// ─── Bootstrap ─────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  setActiveNav("index.html");
  renderStatusBar();

  // Show spinners while loading
  const statCardsEl = document.getElementById("stat-cards");
  const upcomingEl = document.getElementById("upcoming-table");
  const eventsEl = document.getElementById("recent-events");

  if (statCardsEl) showSpinner(statCardsEl);
  if (upcomingEl) showSpinner(upcomingEl);
  if (eventsEl) showSpinner(eventsEl);

  const [statsResult, upcomingResult, eventsResult] = await Promise.allSettled([
    fetchStats(),
    fetchUpcoming(),
    fetchSolarEvents({ limit: 3 }),
  ]);

  // Stats
  if (statsResult.status === "fulfilled") {
    renderStatCards(statsResult.value);
  } else {
    if (statCardsEl) showError(statCardsEl, statsResult.reason?.message ?? "Erro ao carregar estatísticas.");
  }

  // Upcoming asteroids
  if (upcomingResult.status === "fulfilled") {
    renderHero(upcomingResult.value);
    renderUpcomingTable(upcomingResult.value);
  } else {
    const h1 = document.querySelector("#hero h1.hero__title");
    if (h1) h1.textContent = "Erro ao carregar dados.";
    if (upcomingEl) showError(upcomingEl, upcomingResult.reason?.message ?? "Erro ao carregar próximas aproximações.");
  }

  // Solar events
  if (eventsResult.status === "fulfilled") {
    renderRecentEvents(eventsResult.value);
  } else {
    if (eventsEl) showError(eventsEl, eventsResult.reason?.message ?? "Erro ao carregar eventos solares.");
  }
});
