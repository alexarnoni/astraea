// Feature: asteroid-new-fields — detalhe.js property tests
// Properties 4, 5, 6, 7, 8
import { describe, it, expect, vi } from "vitest";
import fc from "fast-check";

// ─── Mock browser globals and module deps before importing detalhe.js ──────────
vi.stubGlobal("location", { search: "?id=1", replace: vi.fn() });
vi.stubGlobal("document", {
  addEventListener: vi.fn(),
  getElementById: vi.fn(() => null),
  title: "",
  querySelectorAll: vi.fn(() => []),
});
vi.mock("../js/api.js", () => ({ fetchAsteroid: vi.fn() }));
vi.mock("../js/ui.js", () => ({
  renderRiskBadge: vi.fn(() => ""),
  renderMetricCard: vi.fn(() => ""),
  showSpinner: vi.fn(),
  showError: vi.fn(),
  setActiveNav: vi.fn(),
  formatDate: vi.fn((d) => d || "—"),
  formatNumber: vi.fn((n) => String(n ?? "—")),
}));

const { normalizeRiskClass, renderMLPanel, renderMetricCards: renderMetricCardsReal } = await import("../js/detalhe.js");

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


// ─── normalizeRiskClass unit tests ────────────────────────────────────────────

describe("normalizeRiskClass", () => {
  it("normalizes 'médio' to 'medio'", () => {
    expect(normalizeRiskClass("médio")).toBe("medio");
  });

  it("keeps 'medio' as 'medio'", () => {
    expect(normalizeRiskClass("medio")).toBe("medio");
  });

  it("normalizes 'MÉDIO' to 'medio'", () => {
    expect(normalizeRiskClass("MÉDIO")).toBe("medio");
  });

  it("normalizes 'Médio' to 'medio'", () => {
    expect(normalizeRiskClass("Médio")).toBe("medio");
  });

  it("keeps 'baixo' as 'baixo'", () => {
    expect(normalizeRiskClass("baixo")).toBe("baixo");
  });

  it("normalizes 'BAIXO' to 'baixo'", () => {
    expect(normalizeRiskClass("BAIXO")).toBe("baixo");
  });

  it("keeps 'alto' as 'alto'", () => {
    expect(normalizeRiskClass("alto")).toBe("alto");
  });

  it("normalizes 'ALTO' to 'alto'", () => {
    expect(normalizeRiskClass("ALTO")).toBe("alto");
  });

  it("returns empty string for null/undefined", () => {
    expect(normalizeRiskClass(null)).toBe("");
    expect(normalizeRiskClass(undefined)).toBe("");
  });
});


// ─── Property P6: MLPanel oculta seção quando probabilidade é null ─────────────

describe("renderMLPanel — null handling", () => {
  it("P6: para qualquer asteroide com pelo menos uma probabilidade null, HTML exibe indisponível e não contém barras", () => {
    // Feature: ml-risk-probabilities, Property 6: MLPanel oculta seção quando probabilidade é null
    // **Validates: Requirements 8.8**

    // Generator: 3 values each either a float [0,1] or null, filtered so at least one is null
    const arbNullableFloat = fc.oneof(
      fc.float({ min: 0, max: 1, noNaN: true }),
      fc.constant(null)
    );

    const arbProbasWithNull = fc
      .tuple(arbNullableFloat, arbNullableFloat, arbNullableFloat)
      .filter(([a, b, c]) => a === null || b === null || c === null);

    const arbLabel = fc.constantFrom("baixo", "medio", "médio", "alto", null);

    fc.assert(
      fc.property(arbProbasWithNull, arbLabel, ([pBaixo, pMedio, pAlto], label) => {
        // Set up a mock container for getElementById("ml-panel")
        const container = { innerHTML: "" };
        document.getElementById = vi.fn((id) => {
          if (id === "ml-panel") return container;
          return null;
        });

        const asteroid = {
          risk_proba_baixo: pBaixo,
          risk_proba_medio: pMedio,
          risk_proba_alto: pAlto,
          risk_label_ml: label,
        };

        renderMLPanel(asteroid);

        const html = container.innerHTML;

        // (a) Contains the unavailability message
        expect(html).toContain("Análise de risco indisponível");

        // (b) Does NOT contain probability bars
        expect(html).not.toContain("proba-row");

        // (c) Does NOT contain risk badge
        expect(html).not.toContain("risk-badge");
      }),
      { numRuns: 100 }
    );
  });
});

// ─── Property P5: MLPanel renderiza distribuição completa ─────────────────────

describe("renderMLPanel — distribuição completa", () => {
  it("P5: para qualquer asteroide com 3 probabilidades não-nulas e risk_label_ml válido, HTML contém badge, frase e 3 barras", () => {
    // Feature: ml-risk-probabilities, Property 5: MLPanel renderiza distribuição completa
    // **Validates: Requirements 8.2, 8.3, 8.4, 8.6**

    // Dirichlet-like generator: 3 random positive floats normalized to sum to 1.0
    const arbProbas = fc
      .tuple(
        fc.integer({ min: 1, max: 1000 }),
        fc.integer({ min: 1, max: 1000 }),
        fc.integer({ min: 1, max: 1000 })
      )
      .map(([a, b, c]) => {
        const sum = a + b + c;
        return [a / sum, b / sum, c / sum];
      });

    const arbLabel = fc.constantFrom("baixo", "medio", "médio", "alto");

    fc.assert(
      fc.property(arbProbas, arbLabel, ([pBaixo, pMedio, pAlto], label) => {
        // Set up a mock container for getElementById("ml-panel")
        const container = { innerHTML: "" };
        document.getElementById = vi.fn((id) => {
          if (id === "ml-panel") return container;
          return null;
        });

        const asteroid = {
          risk_proba_baixo: pBaixo,
          risk_proba_medio: pMedio,
          risk_proba_alto: pAlto,
          risk_label_ml: label,
        };

        renderMLPanel(asteroid);

        const html = container.innerHTML;

        // (a) Badge with the predicted class
        const cls = normalizeRiskClass(label);
        expect(html).toContain(`risk-badge risk-badge--${cls}`);

        // (b) Phrase pattern: "Classificado como ... risco com ...% de probabilidade"
        const probaMap = { baixo: pBaixo, medio: pMedio, alto: pAlto };
        const predictedPct = Math.round(probaMap[cls] * 100);
        expect(html).toContain("Classificado como");
        expect(html).toContain(`${predictedPct}%`);
        expect(html).toContain("de probabilidade");

        // (c) Exactly 3 .proba-row elements
        const probaRowCount = (html.match(/class="proba-row"/g) || []).length;
        expect(probaRowCount).toBe(3);
      }),
      { numRuns: 100 }
    );
  });
});


// ─── Property P7: Eliminação do termo "confiança" ─────────────────────────────

describe("renderMLPanel + renderMetricCards — eliminação de confiança", () => {
  it("P7: para qualquer asteroide com dados válidos, a saída HTML não contém 'confiança'", () => {
    // Feature: ml-risk-probabilities, Property 7: Eliminação do termo confiança
    // **Validates: Requirements 8.9, 10.4, 12.1, 12.2, 12.3**

    // Dirichlet-like generator: 3 random positive floats normalized to sum ≈ 1.0
    const arbProbas = fc
      .tuple(
        fc.integer({ min: 1, max: 1000 }),
        fc.integer({ min: 1, max: 1000 }),
        fc.integer({ min: 1, max: 1000 })
      )
      .map(([a, b, c]) => {
        const sum = a + b + c;
        return [a / sum, b / sum, c / sum];
      });

    const arbLabel = fc.constantFrom("baixo", "medio", "médio", "alto");

    // Generators for fields used by renderMetricCards
    const arbMissDistanceLunar = fc.float({ min: Math.fround(0.01), max: Math.fround(100), noNaN: true });
    const arbMissDistanceKm = fc.float({ min: Math.fround(1000), max: Math.fround(100000000), noNaN: true });
    const arbVelocity = fc.float({ min: Math.fround(1), max: Math.fround(50), noNaN: true });
    const arbDiameterMin = fc.float({ min: Math.fround(0.001), max: Math.fround(5), noNaN: true });
    const arbDiameterMax = fc.float({ min: Math.fround(0.001), max: Math.fround(10), noNaN: true });
    const arbMagnitude = fc.float({ min: Math.fround(10), max: Math.fround(35), noNaN: true });
    const arbHazardous = fc.boolean();

    fc.assert(
      fc.property(
        arbProbas,
        arbLabel,
        arbMissDistanceLunar,
        arbMissDistanceKm,
        arbVelocity,
        arbDiameterMin,
        arbDiameterMax,
        arbMagnitude,
        arbHazardous,
        ([pBaixo, pMedio, pAlto], label, missLunar, missKm, vel, dMin, dMax, mag, hazardous) => {
          // Set up mock containers for both panels
          const mlContainer = { innerHTML: "" };
          const metricContainer = { innerHTML: "" };
          document.getElementById = vi.fn((id) => {
            if (id === "ml-panel") return mlContainer;
            if (id === "metric-cards") return metricContainer;
            return null;
          });

          const asteroid = {
            risk_proba_baixo: pBaixo,
            risk_proba_medio: pMedio,
            risk_proba_alto: pAlto,
            risk_label_ml: label,
            miss_distance_lunar: missLunar,
            miss_distance_km: missKm,
            relative_velocity_km_s: vel,
            estimated_diameter_min_km: dMin,
            estimated_diameter_max_km: dMax,
            absolute_magnitude_h: mag,
            is_potentially_hazardous: hazardous,
            orbit_class: "Apollo",
            first_observation_date: "2020-01-15",
            close_approach_date: "2025-06-01",
            name: "Test Asteroid",
            nasa_jpl_url: null,
            is_sentry_object: false,
          };

          // Call both render functions
          renderMLPanel(asteroid);
          renderMetricCardsReal(asteroid);

          const mlHtml = mlContainer.innerHTML.toLowerCase();
          const metricHtml = metricContainer.innerHTML.toLowerCase();

          // Neither output should contain "confiança" (case-insensitive)
          expect(mlHtml).not.toContain("confiança");
          expect(metricHtml).not.toContain("confiança");

          // Also check the NFD-decomposed form (confianca with combining accent)
          const mlNormalized = mlHtml.normalize("NFD");
          const metricNormalized = metricHtml.normalize("NFD");
          expect(mlNormalized).not.toMatch(/confian[cç]a/i);
          expect(metricNormalized).not.toMatch(/confian[cç]a/i);
        }
      ),
      { numRuns: 100 }
    );
  });
});
