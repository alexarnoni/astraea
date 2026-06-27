// detalhe.js — página de detalhe do asteroide

import { fetchAsteroid } from "./api.js";
import {
  renderRiskBadge,
  renderMetricCard,
  showSpinner,
  showError,
  setActiveNav,
  formatDate,
  formatNumber,
} from "./ui.js";

// ─── Normalize Risk Class ───────────────────────────────────────────────────────

export function normalizeRiskClass(label) {
  return (label || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

// ─── Extract ID ────────────────────────────────────────────────────────────────

const neoId = new URLSearchParams(location.search).get("id");
if (!neoId) {
  location.replace("asteroides.html");
}

// ─── Countdown helpers ─────────────────────────────────────────────────────────

function calcCountdown(dateStr) {
  const target = new Date(dateStr + "T00:00:00Z");
  const diffMs = target.getTime() - Date.now();
  if (diffMs <= 0) return null;

  const totalSec = Math.floor(diffMs / 1000);
  const seconds = totalSec % 60;
  const totalMin = Math.floor(totalSec / 60);
  const minutes = totalMin % 60;
  const totalHours = Math.floor(totalMin / 60);
  const hours = totalHours % 24;
  const days = Math.floor(totalHours / 24);

  return { days, hours, minutes, seconds };
}

function pad(n) {
  return String(n).padStart(2, "0");
}

// ─── Render Hero ───────────────────────────────────────────────────────────────

function renderHero(asteroid) {
  const breadcrumbName = document.getElementById("breadcrumb-name");
  if (breadcrumbName) breadcrumbName.textContent = asteroid.name;
  document.title = `ASTRAEA — ${asteroid.name}`;

  const hazardousBadge = asteroid.is_potentially_hazardous
    ? `<div class="hero__hazardous-badge">⚠ Potencialmente perigoso</div>`
    : "";

  const sentryBadge = asteroid.is_sentry_object
    ? `<div class="hero__sentry-badge hero__sentry-badge--pulse">// LISTA SENTRY<span class="hero__sentry-tooltip">Este objeto está na lista Sentry da NASA — tem probabilidade não-zero de impacto com a Terra nos próximos 100 anos</span></div>`
    : "";

  const heroEl = document.getElementById("asteroid-hero");
  if (!heroEl) return;
  heroEl.innerHTML = `<div class="hero">
  <h1 class="hero__title">${asteroid.name}</h1>
  ${hazardousBadge}
  ${sentryBadge}
  <p class="hero__subtitle" style="margin-top:0.75rem">Objeto próximo à Terra monitorado pela NASA · aproximação em ${formatDate(asteroid.close_approach_date)}</p>
</div>`;
}

// ─── Render Countdown ──────────────────────────────────────────────────────────

let countdownInterval = null;

function renderCountdownSection(asteroid) {
  const section = document.getElementById("countdown-section");
  if (!section) return;

  if (!asteroid.close_approach_date) {
    section.style.display = "none";
    return;
  }

  const isHighRisk = asteroid.is_potentially_hazardous || asteroid.risk_label_ml === "alto";

  function update() {
    const cd = calcCountdown(asteroid.close_approach_date);
    if (!cd) {
      if (countdownInterval) clearInterval(countdownInterval);
      section.innerHTML = `<p style="color:var(--muted);font-size:0.9rem;margin:1rem 0">Aproximação já ocorreu em ${formatDate(asteroid.close_approach_date)}.</p>`;
      return;
    }

    const boxClass = isHighRisk ? "countdown-box countdown-box--danger" : "countdown-box";
    const valueClass = isHighRisk ? "countdown__value" : "countdown__value";
    const dangerStyle = isHighRisk ? "color:var(--badge-alto-bg)" : "";

    section.innerHTML = `<div style="margin:1.5rem 0">
  <p class="section-label">tempo até a aproximação</p>
  <div class="${boxClass}">
    <div class="countdown__unit">
      <span class="${valueClass}" style="${dangerStyle}">${cd.days}</span>
      <span class="countdown__label">dias</span>
    </div>
    <span class="countdown__sep">:</span>
    <div class="countdown__unit">
      <span class="${valueClass}" style="${dangerStyle}">${pad(cd.hours)}</span>
      <span class="countdown__label">horas</span>
    </div>
    <span class="countdown__sep">:</span>
    <div class="countdown__unit">
      <span class="${valueClass}" style="${dangerStyle}">${pad(cd.minutes)}</span>
      <span class="countdown__label">min</span>
    </div>
    <span class="countdown__sep">:</span>
    <div class="countdown__unit">
      <span class="${valueClass}" style="${dangerStyle}">${pad(cd.seconds)}</span>
      <span class="countdown__label">seg</span>
    </div>
  </div>
</div>`;
  }

  update();
  if (countdownInterval) clearInterval(countdownInterval);
  countdownInterval = setInterval(update, 1000);
}

// ─── Render Metric Cards ───────────────────────────────────────────────────────

export function renderMetricCards(asteroid) {
  const container = document.getElementById("metric-cards");
  if (!container) return;

  const hazardousText = asteroid.is_potentially_hazardous ? "Sim" : "Não";
  const hazardousStyle = asteroid.is_potentially_hazardous
    ? `style="color:var(--badge-alto-bg)"`
    : `style="color:var(--badge-baixo-bg)"`;

  const velocityKmH = asteroid.relative_velocity_km_s != null
    ? formatNumber(asteroid.relative_velocity_km_s * 3600, 0)
    : "—";

  const label = asteroid.risk_label_ml;
  const cls = normalizeRiskClass(label);
  const probaMap = { baixo: asteroid.risk_proba_baixo, medio: asteroid.risk_proba_medio, alto: asteroid.risk_proba_alto };
  const predictedProba = probaMap[cls] ?? null;
  const mlDisplay = predictedProba != null
    ? `${Math.round(predictedProba * 100)}% probabilidade ${label ? renderRiskBadge(label) : ""}`
    : "—";

  const cards = [
    [
      `${formatNumber(asteroid.miss_distance_lunar, 2)} LD<br><small style="font-size:0.75rem;color:var(--muted)">${formatNumber(asteroid.miss_distance_km, 0)} km</small>`,
      "Distância mínima",
      "Distância de aproximação em Distâncias Lunares (LD) e quilômetros. 1 LD ≈ 384.400 km.",
    ],
    [
      `${formatNumber(asteroid.relative_velocity_km_s, 2)} km/s<br><small style="font-size:0.75rem;color:var(--muted)">${velocityKmH} km/h</small>`,
      "Velocidade relativa",
      "Velocidade relativa ao passar pela Terra em km/s e km/h.",
    ],
    [
      `${formatNumber(asteroid.estimated_diameter_min_km, 3)} a ${formatNumber(asteroid.estimated_diameter_max_km, 3)} km`,
      "Diâmetro estimado",
      "Faixa de estimativa do diâmetro do objeto em quilômetros.",
    ],
    [
      `${formatNumber(asteroid.absolute_magnitude_h, 1)}`,
      "Magnitude absoluta (H)",
      "Brilho intrínseco do asteroide. Valores menores indicam objetos maiores e mais brilhantes.",
    ],
    [
      `<span ${hazardousStyle}>${hazardousText}</span>`,
      "Risco NASA",
      "Classificação oficial da NASA: indica se o objeto é potencialmente perigoso (PHA) com base em tamanho e distância.",
    ],
    [
      mlDisplay,
      "Score ML",
      "Probabilidade atribuída pelo modelo de machine learning à classe de risco predita.",
    ],
    [
      asteroid.orbit_class ?? "—",
      "Grupo orbital",
      "Classificação do grupo orbital: Apollo (cruzam a órbita da Terra), Aten (órbita menor que a Terra), Amor (aproximam-se mas não cruzam).",
    ],
    [
      formatDate(asteroid.first_observation_date),
      "Descoberto em",
      "Data da primeira observação registrada do asteroide.",
    ],
  ];

  container.innerHTML = cards
    .map(([value, label, tooltip]) => renderMetricCard(value, label, tooltip))
    .join("");
}

// ─── Render Perspective Section ───────────────────────────────────────────────

function renderPerspectiveSection(asteroid) {
  const mlPanel = document.getElementById("ml-panel");
  if (!mlPanel) return;

  // Remove previous instance if re-rendered
  const existing = document.getElementById("perspective-section");
  if (existing) existing.remove();

  const section = document.createElement("div");
  section.id = "perspective-section";
  section.style.marginTop = "1.5rem";

  // 1. Tamanho comparativo
  const dMin = asteroid.estimated_diameter_min_km ?? 0;
  const dMax = asteroid.estimated_diameter_max_km ?? 0;
  const avgM = ((dMin + dMax) / 2) * 1000;
  let sizeLabel, sizeDetail;
  if (avgM < 25) {
    sizeLabel = "do tamanho de uma casa";
    sizeDetail = `~${Math.round(avgM)} m de diâmetro estimado`;
  } else if (avgM < 100) {
    sizeLabel = "do tamanho de um estádio de futebol";
    sizeDetail = `~${Math.round(avgM)} m de diâmetro estimado`;
  } else if (avgM < 300) {
    sizeLabel = "do tamanho de um bairro pequeno";
    sizeDetail = `~${Math.round(avgM)} m de diâmetro estimado`;
  } else if (avgM < 1000) {
    sizeLabel = "do tamanho de uma cidade pequena";
    sizeDetail = `~${Math.round(avgM)} m de diâmetro estimado`;
  } else {
    sizeLabel = "do tamanho de uma grande cidade";
    sizeDetail = `~${(avgM / 1000).toFixed(1)} km de diâmetro estimado`;
  }

  // 2. Distância humanizada
  const lunar = asteroid.miss_distance_lunar != null ? Number(asteroid.miss_distance_lunar).toFixed(1) : "—";
  const distKm = asteroid.miss_distance_km != null
    ? Number(asteroid.miss_distance_km).toLocaleString("pt-BR", { maximumFractionDigits: 0 })
    : "—";
  const distLabel = `Passará a ${distKm} km`;
  const distDetail = `${lunar} vezes a distância da Lua`;

  // 3. Velocidade comparada
  const velKmH = asteroid.relative_velocity_km_s != null ? asteroid.relative_velocity_km_s * 3600 : null;
  const planeX = velKmH != null ? Math.round(velKmH / 900) : null;
  const velLabel = planeX != null ? `${planeX}× mais rápido que um avião comercial` : "—";
  const velDetail = velKmH != null ? `${Math.round(velKmH).toLocaleString("pt-BR")} km/h` : "—";

  // 4. Classificação
  const classLabel = asteroid.is_potentially_hazardous
    ? "Objeto Potencialmente Perigoso (PHA)"
    : "Objeto Próximo à Terra (NEO)";
  const classDetail = asteroid.is_potentially_hazardous
    ? "Classificado pela NASA como PHA — passa a menos de 7,5 milhões de km da Terra e tem mais de 140m de diâmetro"
    : "Monitorado pela NASA como NEO — sem risco de impacto previsto";

  // 5. Impacto hipotético
  let impactLabel, impactDetail;
  if (avgM < 25) {
    impactLabel = "Queimaria na atmosfera";
    impactDetail = "Causaria no máximo um rastro luminoso no céu, sem atingir o solo";
  } else if (avgM < 50) {
    impactLabel = "Explosão atmosférica";
    impactDetail = "Energia similar ao evento de Chelyabinsk (Rússia, 2013) — janelas quebradas num raio de centenas de km";
  } else if (avgM < 300) {
    impactLabel = "Destruição local";
    impactDetail = "Devastaria uma cidade inteira e arredores";
  } else if (avgM < 1000) {
    impactLabel = "Destruição regional";
    impactDetail = "Causaria destruição em área do tamanho de um país pequeno e tsunamis se cair no oceano";
  } else {
    impactLabel = "Evento catastrófico global";
    impactDetail = "Impacto comparável a extinções em massa — alteraria o clima do planeta";
  }

  // 6. Tempo de viagem até a Lua
  const moonMinutes = velKmH != null ? Math.round(384400 / velKmH * 60) : null;
  const moonLabel = moonMinutes != null ? `Chegaria à Lua em ${moonMinutes} minutos` : "—";
  const moonDetail = velKmH != null ? `Viajando à velocidade de ${Math.round(velKmH).toLocaleString("pt-BR")} km/h` : "—";

  const item = (label, value, detail) => `
    <div>
      <p style="font-family:var(--font-mono);font-size:9px;text-transform:uppercase;letter-spacing:0.15em;color:var(--muted);margin-bottom:4px">${label}</p>
      <p style="font-family:var(--font-body);font-size:13px;color:#e2e8f0;margin-bottom:2px">${value}</p>
      <p style="font-family:var(--font-body);font-size:11px;color:#64748b">${detail}</p>
    </div>`;

  section.innerHTML = `<div style="background:#111827;border:1px solid #1e2d45;border-radius:8px;padding:20px;margin-bottom:1.5rem">
  <p style="font-family:var(--font-mono);font-size:10px;text-transform:uppercase;letter-spacing:0.15em;color:#64748b;margin-bottom:16px">// em perspectiva</p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    ${item("tamanho comparativo", sizeLabel, sizeDetail)}
    ${item("distância", distLabel, distDetail)}
    ${item("velocidade", velLabel, velDetail)}
    ${item("classificação", classLabel, classDetail)}
    ${item("impacto hipotético", impactLabel, impactDetail)}
    ${item("tempo de viagem", moonLabel, moonDetail)}
  </div>
</div>`;

  mlPanel.parentNode.insertBefore(section, mlPanel);
}

// ─── Render ML Panel ───────────────────────────────────────────────────────────

export function renderMLPanel(asteroid) {
  const container = document.getElementById("ml-panel");
  if (!container) return;

  const probaBaixo = asteroid.risk_proba_baixo;
  const probaMedio = asteroid.risk_proba_medio;
  const probaAlto = asteroid.risk_proba_alto;

  if (probaBaixo == null || probaMedio == null || probaAlto == null) {
    container.innerHTML = `<p style="color:var(--muted);font-size:0.9rem">Análise de risco indisponível para este objeto</p>`;
    return;
  }

  const label = asteroid.risk_label_ml || "";
  const cls = normalizeRiskClass(label);

  const probaMap = { baixo: probaBaixo, medio: probaMedio, alto: probaAlto };
  const predictedProba = probaMap[cls] ?? 0;
  const pct = Math.round(predictedProba * 100);

  const colors = { baixo: "#22c55e", medio: "#f59e0b", alto: "#ef4444" };

  const probaRow = (name, displayLabel, value) => {
    const color = colors[name];
    const w = Math.round(value * 100);
    return `<div class="proba-row">
    <span class="proba-row__label">${displayLabel}</span>
    <div class="proba-bar-track"><div class="proba-bar-fill" style="width:${w}%;background:${color}"></div></div>
    <span class="proba-row__value">${w}%</span>
  </div>`;
  };

  container.innerHTML = `<div class="ml-panel">
  <p class="section-label">análise de risco — modelo ml</p>
  <div style="margin-bottom:0.75rem"><span class="risk-badge risk-badge--${cls}">${label}</span></div>
  <p style="font-size:0.9rem;color:var(--muted);margin-bottom:0.75rem">
    Classificado como <strong style="color:var(--text)">${label}</strong> risco com <strong style="color:var(--text)">${pct}%</strong> de probabilidade
  </p>
  ${probaRow("baixo", "baixo", probaBaixo)}
  ${probaRow("medio", "médio", probaMedio)}
  ${probaRow("alto", "alto", probaAlto)}
  <p style="font-size:0.8rem;color:var(--muted);margin-top:0.75rem;font-style:italic">
    ⚠ Este modelo não substitui avaliações oficiais da NASA.
  </p>
</div>`;
}

// ─── Render JPL Link ───────────────────────────────────────────────────────────

function renderJPLLink(id, url) {
  const container = document.getElementById("jpl-link");
  if (!container) return;
  const href = url ?? `https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=${id}`;
  container.innerHTML = `<a href="${href}" target="_blank" rel="noopener" class="mono" style="font-size:0.85rem">
  ↗ Ver no NASA JPL Small-Body Database
</a>`;
}

// ─── Bootstrap ─────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  setActiveNav("asteroides.html");

  const heroEl = document.getElementById("asteroid-hero");
  if (heroEl) showSpinner(heroEl);

  try {
    const asteroid = await fetchAsteroid(neoId);
    renderHero(asteroid);
    renderCountdownSection(asteroid);
    renderMetricCards(asteroid);
    renderPerspectiveSection(asteroid);
    renderMLPanel(asteroid);
    renderJPLLink(neoId, asteroid.nasa_jpl_url);
  } catch (err) {
    const heroContainer = document.getElementById("asteroid-hero");
    if (!heroContainer) return;
    if (err.message === "Recurso não encontrado.") {
      showError(heroContainer, "Asteroide não encontrado.");
    } else {
      showError(heroContainer, err.message);
    }
  }
});
