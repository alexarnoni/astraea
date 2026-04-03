// ui.js — componentes visuais reutilizáveis

/**
 * Renderiza um badge de risco.
 * @param {string|null|undefined} label - "alto", "médio" ou "baixo"
 * @returns {string} HTML string
 */
export function renderRiskBadge(label) {
  if (label == null) return "";
  return `<span class="badge badge--${label}">${label.toUpperCase()}</span>`;
}

/**
 * Renderiza um stat card com valor, label e tooltip.
 * @param {string|number} value
 * @param {string} label
 * @param {string} tooltip
 * @returns {string} HTML string
 */
export function renderStatCard(value, label, tooltip) {
  return `<div class="stat-card">
  <div class="stat-card__value">${value}</div>
  <div class="stat-card__label">${label}</div>
  <button class="stat-card__tooltip-btn" type="button">?</button>
  <div class="stat-card__tooltip-text">${tooltip}</div>
</div>`;
}

/**
 * Renderiza um metric card com valor, label e tooltip.
 * @param {string|number} value
 * @param {string} label
 * @param {string} tooltip
 * @returns {string} HTML string
 */
export function renderMetricCard(value, label, tooltip) {
  return `<div class="metric-card">
  <div class="metric-card__value">${value}</div>
  <div class="metric-card__label">${label}</div>
  <button class="metric-card__tooltip-btn" type="button">?</button>
  <div class="metric-card__tooltip-text">${tooltip}</div>
</div>`;
}

/**
 * Exibe um spinner de carregamento no container.
 * @param {HTMLElement} container
 */
export function showSpinner(container) {
  container.innerHTML = `<div class="spinner-container"><div class="spinner"></div></div>`;
}

/**
 * Exibe uma mensagem de erro no container.
 * @param {HTMLElement} container
 * @param {string} message
 */
export function showError(container, message) {
  container.innerHTML = `<p class="error-msg">${message}</p>`;
}

/**
 * Marca o link de navegação ativo com base no filename da página atual.
 * @param {string} filename - ex: "index.html"
 */
export function setActiveNav(filename) {
  const links = document.querySelectorAll(".nav__links a");
  links.forEach((link) => {
    if (link.getAttribute("href").endsWith(filename)) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });
}

/**
 * Calcula o countdown para uma data futura.
 * Trata close_approach_date como meia-noite UTC da data informada.
 * @param {string} dateStr - "YYYY-MM-DD"
 * @returns {{ days: number, hours: number, minutes: number } | null}
 */
export function renderCountdown(dateStr) {
  const target = new Date(dateStr + "T00:00:00Z");
  const now = new Date();

  const diffMs = target.getTime() - now.getTime();
  if (diffMs <= 0) return null;

  const totalMinutes = Math.floor(diffMs / 60000);
  const minutes = totalMinutes % 60;
  const totalHours = Math.floor(totalMinutes / 60);
  const hours = totalHours % 24;
  const days = Math.floor(totalHours / 24);

  return { days, hours, minutes };
}

/**
 * Formata uma data de "YYYY-MM-DD" para "DD/MM/YYYY".
 * @param {string} dateStr
 * @returns {string}
 */
export function formatDate(dateStr) {
  if (!dateStr) return "—";
  const [year, month, day] = dateStr.split("-");
  return `${day}/${month}/${year}`;
}

/**
 * Formata um número com casas decimais fixas.
 * @param {number|null|undefined} n
 * @param {number} decimals
 * @returns {string}
 */
export function formatNumber(n, decimals = 2) {
  if (n == null) return "—";
  return Number(n).toFixed(decimals);
}
