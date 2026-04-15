// asteroides.js — lógica da página de lista de asteroides (filtros, tabela, paginação)

import { fetchAsteroids } from "./api.js";
import {
  renderRiskBadge,
  showSpinner,
  showError,
  setActiveNav,
  formatDate,
  formatNumber,
} from "./ui.js";

// ─── State ─────────────────────────────────────────────────────────────────────

let currentOffset = 0;
let currentRisk = null;     // null | "alto" | "médio" | "baixo"
let currentHazardous = null; // null | true
const LIMIT = 50;

// ─── Load ──────────────────────────────────────────────────────────────────────

async function loadAsteroids() {
  const tableEl = document.getElementById("asteroids-table");
  if (!tableEl) return;

  showSpinner(tableEl);

  try {
    const startDateInput = document.getElementById("start-date");
    const endDateInput = document.getElementById("end-date");
    const data = await fetchAsteroids({
      limit: LIMIT,
      offset: currentOffset,
      risk_label: currentRisk,
      hazardous: currentHazardous,
      start_date: startDateInput?.value || null,
      end_date: endDateInput?.value || null,
    });
    renderTable(data);
    updatePagination(data.length);
  } catch (err) {
    showError(tableEl, err.message ?? "Erro ao carregar asteroides.");
  }
}

// ─── Render Table ──────────────────────────────────────────────────────────────

function renderTable(asteroids) {
  const container = document.getElementById("asteroids-table");
  if (!container) return;

  if (!asteroids.length) {
    container.innerHTML = `<p class="error-msg" style="color:var(--muted)">Nenhum asteroide encontrado com os filtros selecionados.</p>`;
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
        <th>Data de Aproximação</th>
        <th>Distância</th>
        <th>Velocidade</th>
        <th>Diâmetro</th>
        <th>Risco</th>
      </tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>`;
}

// ─── Pagination ────────────────────────────────────────────────────────────────

function updatePagination(count) {
  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");
  const pageInfo = document.getElementById("page-info");

  if (btnPrev) btnPrev.disabled = currentOffset === 0;
  if (btnNext) btnNext.disabled = count < LIMIT;
  if (pageInfo) pageInfo.textContent = `página ${Math.floor(currentOffset / LIMIT) + 1}`;
}

// ─── Bootstrap ─────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  setActiveNav("asteroides.html");

  // Filter buttons
  document.querySelectorAll(".filter-btn[data-risk]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn[data-risk]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const risk = btn.dataset.risk;
      currentRisk = risk === "" ? null : risk;
      currentOffset = 0;
      loadAsteroids();
    });
  });

  // Hazardous checkbox
  const hazardousCheck = document.getElementById("hazardous-check");
  if (hazardousCheck) {
    hazardousCheck.addEventListener("change", () => {
      currentHazardous = hazardousCheck.checked ? true : null;
      currentOffset = 0;
      loadAsteroids();
    });
  }

  // Date filters
  const startDateInput = document.getElementById("start-date");
  const endDateInput = document.getElementById("end-date");
  if (startDateInput) {
    startDateInput.addEventListener("change", () => { currentOffset = 0; loadAsteroids(); });
  }
  if (endDateInput) {
    endDateInput.addEventListener("change", () => { currentOffset = 0; loadAsteroids(); });
  }

  // Pagination
  const btnPrev = document.getElementById("btn-prev");
  const btnNext = document.getElementById("btn-next");

  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      currentOffset = Math.max(0, currentOffset - LIMIT);
      loadAsteroids();
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      currentOffset += LIMIT;
      loadAsteroids();
    });
  }

  loadAsteroids();
});
