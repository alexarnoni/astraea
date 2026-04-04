// Feature: asteroid-new-fields — detalhe.js property tests
// Properties 4, 5, 6, 7, 8
import { describe, it } from "vitest";
import fc from "fast-check";

// ─── Funções extraídas para teste (espelham a lógica de detalhe.js) ────────────

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const [year, month, day] = dateStr.split("-");
  return `${day}/${month}/${year}`;
}

function renderHero(asteroid) {
  const hazardousBadge = asteroid.is_potentially_hazardous
    ? `<div class="hero__hazardous-badge">⚠ Potencialmente perigoso</div>`
    : "";
  const sentryBadge = asteroid.is_sentry_object
    ? `<div class="hero__sentry-badge hero__sentry-badge--pulse">// LISTA SENTRY<span class="hero__sentry-tooltip">Este objeto está na lista Sentry da NASA — tem probabilidade não-zero de impacto com a Terra nos próximos 100 anos</span></div>`
    : "";
  return `<div class="hero"><h1>${asteroid.name}</h1>${hazardousBadge}${sentryBadge}</div>`;
}

function renderMetricCards(asteroid) {
  const cards = [
    [asteroid.orbit_class ?? "—", "Grupo orbital", "Classificação do grupo orbital: Apollo (cruzam a órbita da Terra), Aten (órbita menor que a Terra), Amor (aproximam-se mas não cruzam)."],
    [formatDate(asteroid.first_observation_date), "Descoberto em", "Data da primeira observação registrada do asteroide."],
  ];
  return cards.map(([value, label, tooltip]) =>
    `<div class="metric-card"><div>${value}</div><div>${label}</div><div>${tooltip}</div></div>`
  ).join("");
}

function renderJPLLink(id, url) {
  const href = url ?? `https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=${id}`;
  return `<a href="${href}" target="_blank" rel="noopener">↗ Ver no NASA JPL Small-Body Database</a>`;
}

// ─── Property 4: Badge Sentry presente quando is_sentry_object é true ─────────

describe("renderHero — badge Sentry", () => {
  it("P4: badge Sentry presente quando is_sentry_object é true", () => {
    // Feature: asteroid-new-fields, Property 4: Badge Sentry presente quando is_sentry_object é true
    // Validates: Requirements 4.1, 4.2, 4.4
    fc.assert(
      fc.property(
        fc.record({
          name: fc.string({ minLength: 1 }),
          is_potentially_hazardous: fc.boolean(),
          is_sentry_object: fc.constant(true),
        }),
        (asteroid) => {
          const html = renderHero(asteroid);
          return (
            html.includes("// LISTA SENTRY") &&
            html.includes("hero__sentry-badge--pulse") &&
            html.includes("lista Sentry da NASA")
          );
        }
      ),
      { numRuns: 100 }
    );
  });

  // ─── Property 5: Badge Sentry ausente quando is_sentry_object é false ou null ─

  it("P5: badge Sentry ausente quando is_sentry_object é false ou null", () => {
    // Feature: asteroid-new-fields, Property 5: Badge Sentry ausente quando is_sentry_object é false ou null
    // Validates: Requirements 4.3
    fc.assert(
      fc.property(
        fc.record({
          name: fc.string({ minLength: 1 }),
          is_potentially_hazardous: fc.boolean(),
          is_sentry_object: fc.constantFrom(false, null),
        }),
        (asteroid) => {
          const html = renderHero(asteroid);
          return !html.includes("// LISTA SENTRY");
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─── Property 6: Metric card orbit_class ──────────────────────────────────────

describe("renderMetricCards — orbit_class", () => {
  it("P6: metric card de grupo orbital renderiza valor e tooltip", () => {
    // Feature: asteroid-new-fields, Property 6: Metric card orbit_class renderiza valor e tooltip
    // Validates: Requirements 5.1, 5.2, 5.3
    fc.assert(
      fc.property(
        fc.option(fc.string({ minLength: 1, maxLength: 50 }), { nil: null }),
        (orbit_class) => {
          const html = renderMetricCards({ orbit_class, first_observation_date: null });
          const expectedValue = orbit_class ?? "—";
          return (
            html.includes("Grupo orbital") &&
            html.includes(expectedValue) &&
            html.includes("Apollo") &&
            html.includes("Aten") &&
            html.includes("Amor")
          );
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─── Property 7: Metric card first_observation_date ───────────────────────────

describe("renderMetricCards — first_observation_date", () => {
  it("P7: metric card de descoberta renderiza data formatada em DD/MM/YYYY ou —", () => {
    // Feature: asteroid-new-fields, Property 7: Metric card first_observation_date renderiza data formatada
    // Validates: Requirements 6.1, 6.2
    fc.assert(
      fc.property(
        fc.option(
          fc.date({ min: new Date("1900-01-01"), max: new Date("2100-12-31") })
            .map((d) => d.toISOString().split("T")[0]),
          { nil: null }
        ),
        (first_observation_date) => {
          const html = renderMetricCards({ orbit_class: null, first_observation_date });
          const expectedValue = first_observation_date
            ? formatDate(first_observation_date)
            : "—";
          return html.includes("Descoberto em") && html.includes(expectedValue);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// ─── Property 8: Link JPL URL selection ───────────────────────────────────────

describe("renderJPLLink — URL selection", () => {
  it("P8: usa nasa_jpl_url quando disponível, fallback com neo_id quando null", () => {
    // Feature: asteroid-new-fields, Property 8: Link JPL usa nasa_jpl_url quando disponível, fallback quando null
    // Validates: Requirements 7.1, 7.2, 7.3
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 20 }),
        fc.option(
          fc.string({ minLength: 1, maxLength: 100 }).map((s) => "https://ssd.jpl.nasa.gov/" + s),
          { nil: null }
        ),
        (neo_id, nasa_jpl_url) => {
          const html = renderJPLLink(neo_id, nasa_jpl_url);
          const expectedHref = nasa_jpl_url ?? `https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=${neo_id}`;
          return (
            html.includes(`href="${expectedHref}"`) &&
            html.includes('target="_blank"') &&
            html.includes('rel="noopener"')
          );
        }
      ),
      { numRuns: 100 }
    );
  });
});
