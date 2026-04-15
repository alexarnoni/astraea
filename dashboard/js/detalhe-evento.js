// detalhe-evento.js — página de detalhe do evento solar

import { fetchSolarEvent } from "./api.js";
import { showSpinner, showError, setActiveNav } from "./ui.js";

// ─── Helpers ───────────────────────────────────────────────────────────────────

const MONTHS_PT = [
  "janeiro","fevereiro","março","abril","maio","junho",
  "julho","agosto","setembro","outubro","novembro","dezembro"
];

export function formatDatePT(dateStr) {
  if (!dateStr) return "—";
  const [year, month, day] = dateStr.split("-");
  return `${parseInt(day, 10)} de ${MONTHS_PT[parseInt(month, 10) - 1]} de ${year}`;
}

export function typeBadgeStyle(type) {
  if (type === "CME") return "background:#1e40af;color:#bfdbfe";
  if (type === "GST") return "background:#78350f;color:#fde68a";
  return "";
}

function intensityBadgeClass(label) {
  if (!label) return "";
  const l = label.toUpperCase();
  if (l === "EXTREMO") return "badge--alto";
  if (l === "MODERADO") return "badge--médio";
  if (l === "FRACO") return "badge--baixo";
  return "badge--baixo";
}

// ─── Extract ID ────────────────────────────────────────────────────────────────

const eventId = new URLSearchParams(location.search).get("id");
if (!eventId) {
  location.replace("eventos.html");
}

// ─── Render Hero ───────────────────────────────────────────────────────────────

function renderHero(ev) {
  const breadcrumbName = document.getElementById("breadcrumb-name");
  if (breadcrumbName) breadcrumbName.textContent = ev.event_type;
  document.title = `ASTRAEA — ${ev.event_type} — ${formatDatePT(ev.event_date)}`;

  const typeBadge = `<span class="badge" style="${typeBadgeStyle(ev.event_type)}">${ev.event_type}</span>`;
  const intensityBadge = ev.intensity_label
    ? `<span class="badge ${intensityBadgeClass(ev.intensity_label)}">${ev.intensity_label.toUpperCase()}</span>`
    : "";

  const explainer = ev.event_type === "CME"
    ? "Ejeção de massa coronal — explosão solar que lança plasma para o espaço"
    : "Tempestade geomagnética — perturbação no campo magnético da Terra";

  const heroEl = document.getElementById("event-hero");
  if (!heroEl) return;
  heroEl.innerHTML = `<div class="hero">
  <h1 class="hero__title">${ev.event_type === "CME" ? "Ejeção de Massa Coronal" : "Tempestade Geomagnética"}</h1>
  <div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.5rem">
    ${typeBadge}
    ${intensityBadge}
  </div>
  <p class="hero__subtitle" style="margin-top:0.75rem">${explainer} · ${formatDatePT(ev.event_date)}</p>
</div>`;
}

// ─── Render Details ────────────────────────────────────────────────────────────

export function renderDetails(ev) {
  const container = document.getElementById("event-details");
  if (!container) return;

  const field = (label, value) => value != null && value !== ""
    ? `<div class="detail-field">
        <span class="detail-field__label">${label}</span>
        <span class="detail-field__value">${value}</span>
      </div>`
    : "";

  let fields = "";
  fields += field("Data", formatDatePT(ev.event_date));
  fields += field("Tipo", ev.event_type);

  if (ev.event_type === "CME") {
    fields += field("Velocidade", ev.speed_km_s != null ? `${Math.round(ev.speed_km_s)} km/s` : null);
    fields += field("Direcionado à Terra", ev.is_earth_directed != null ? (ev.is_earth_directed ? "Sim ☀️→🌍" : "Não") : null);
    fields += field("Tipo CME", ev.cme_type);
    fields += field("Meio-ângulo", ev.half_angle_deg != null ? `${ev.half_angle_deg}°` : null);
    fields += field("Latitude", ev.latitude != null ? `${ev.latitude}°` : null);
    fields += field("Longitude", ev.longitude != null ? `${ev.longitude}°` : null);
  }

  if (ev.event_type === "GST") {
    fields += field("Índice Kp máximo", ev.kp_index_max);
  }

  fields += field("Intensidade", ev.intensity_label ? ev.intensity_label.toUpperCase() : null);

  container.innerHTML = `<div class="detail-section">
  <p class="section-label">dados do evento</p>
  ${fields}
</div>`;
}

// ─── Render Note ───────────────────────────────────────────────────────────────

export function renderNote(ev) {
  const container = document.getElementById("event-note");
  if (!container) return;

  if (!ev.note) {
    container.innerHTML = "";
    return;
  }

  container.innerHTML = `<div class="note-section">
  <span style="font-family:var(--font-mono);font-size:9px;color:#64748b;border:1px solid #1e2d45;padding:1px 6px;border-radius:3px;margin-right:0.4em;vertical-align:middle">NASA (EN)</span>
  ${ev.note}
</div>`;
}

// ─── Render DONKI Link ─────────────────────────────────────────────────────────

function renderDONKILink(ev) {
  const container = document.getElementById("donki-link");
  if (!container) return;

  const baseUrl = ev.event_type === "CME"
    ? "https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/CME/"
    : "https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/GST/";

  container.innerHTML = `<a href="${baseUrl}${encodeURIComponent(ev.event_id)}" target="_blank" rel="noopener" class="mono" style="font-size:0.85rem">
  ↗ Ver na NASA DONKI
</a>`;
}

// ─── Bootstrap ─────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  setActiveNav("eventos.html");

  const heroEl = document.getElementById("event-hero");
  if (heroEl) showSpinner(heroEl);

  try {
    const ev = await fetchSolarEvent(eventId);
    renderHero(ev);
    renderDetails(ev);
    renderNote(ev);
    renderDONKILink(ev);
  } catch (err) {
    const heroContainer = document.getElementById("event-hero");
    if (!heroContainer) return;
    if (err.message === "Recurso não encontrado.") {
      showError(heroContainer, "Evento solar não encontrado.");
    } else {
      showError(heroContainer, err.message);
    }
  }
});
