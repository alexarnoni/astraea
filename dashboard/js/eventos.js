// eventos.js — lógica da página de eventos solares

import { fetchSolarEvents } from "./api.js";
import { showSpinner, showError, setActiveNav } from "./ui.js";

const MONTHS_PT = [
  "janeiro","fevereiro","março","abril","maio","junho",
  "julho","agosto","setembro","outubro","novembro","dezembro"
];

function formatDatePT(dateStr) {
  if (!dateStr) return "—";
  const [year, month, day] = dateStr.split("-");
  return `${parseInt(day, 10)} de ${MONTHS_PT[parseInt(month, 10) - 1]} de ${year}`;
}

function intensityBadgeClass(label) {
  if (!label) return "";
  const l = label.toUpperCase();
  if (l === "EXTREMO") return "badge--alto";
  if (l === "MODERADO") return "badge--médio";
  if (l === "FRACO") return "badge--baixo";
  return "badge--baixo";
}

function typeBadgeStyle(type) {
  if (type === "CME") return "background:#1e40af;color:#bfdbfe";
  if (type === "GST") return "background:#78350f;color:#fde68a";
  return "";
}

function renderCard(ev) {
  const typeBadge = `<span class="badge" style="${typeBadgeStyle(ev.event_type)}">${ev.event_type}</span>`;

  const intensityBadge = ev.intensity_label
    ? `<span class="badge ${intensityBadgeClass(ev.intensity_label)}">${ev.intensity_label.toUpperCase()}</span>`
    : "";

  const speedField = ev.event_type === "CME" && ev.speed_km_s != null
    ? `<p class="event-card__field">Velocidade: <span>${Math.round(ev.speed_km_s)} km/s</span></p>`
    : "";

  const kpField = ev.event_type === "GST" && ev.kp_index_max != null
    ? `<p class="event-card__field">Índice Kp: <span>${ev.kp_index_max}</span></p>`
    : "";

  const noteField = ev.note
    ? `<p class="event-card__note"><span style="font-family:var(--font-mono);font-size:9px;color:#64748b;border:1px solid #1e2d45;padding:1px 6px;border-radius:3px;margin-right:0.4em;vertical-align:middle">NASA (EN)</span>${ev.note}</p>`
    : "";

  const explainer = ev.event_type === "CME"
    ? "Ejeção de massa coronal — explosão solar que lança plasma para o espaço"
    : "Tempestade geomagnética — perturbação no campo magnético da Terra";

  return `<a href="detalhe-evento.html?id=${ev.event_id}" style="text-decoration:none;color:inherit;cursor:pointer;display:block">
<div class="event-card">
  <div class="event-card__header">
    <div style="display:flex;align-items:center;gap:0.5rem">
      ${typeBadge}
      ${intensityBadge}
    </div>
    <span class="event-card__date">${formatDatePT(ev.event_date)}</span>
  </div>
  ${speedField}
  ${kpField}
  ${noteField}
  <p style="font-size:0.75rem;color:var(--muted);margin-top:0.25rem;font-style:italic">${explainer}</p>
</div>
</a>`;
}

// all events cached after first load
let allEvents = [];
let currentFilter = "";

function applyFilter() {
  const grid = document.getElementById("events-grid");
  if (!grid) return;

  const filtered = currentFilter
    ? allEvents.filter(ev => ev.event_type === currentFilter)
    : allEvents;

  if (filtered.length === 0) {
    grid.innerHTML = `<p class="error-msg" style="grid-column:1/-1">Nenhum evento encontrado para este filtro.</p>`;
    return;
  }

  grid.innerHTML = filtered.map(renderCard).join("");
}

async function loadEvents() {
  const grid = document.getElementById("events-grid");
  if (!grid) return;

  showSpinner(grid);

  try {
    allEvents = await fetchSolarEvents({ limit: 50 });
    applyFilter();
  } catch (err) {
    showError(grid, err.message);
  }
}

function attachFilterListeners() {
  const buttons = document.querySelectorAll("#event-filters .filter-btn");
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.getAttribute("data-type");
      applyFilter();
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setActiveNav("eventos.html");
  attachFilterListeners();
  loadEvents();
});
