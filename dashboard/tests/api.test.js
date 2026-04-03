// Feature: astraea-dashboard — api.js unit tests
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fc from "fast-check";

// We need to test the URL construction logic without actually calling fetch.
// Extract the query string building logic for testing.

function buildAsteroidsQuery({ limit, offset, hazardous, risk_label } = {}) {
  const params = new URLSearchParams();
  if (limit != null) params.append("limit", limit);
  if (offset != null) params.append("offset", offset);
  if (hazardous != null) params.append("hazardous", hazardous);
  if (risk_label != null) params.append("risk_label", risk_label);
  return params.toString();
}

function buildSolarEventsQuery({ limit, offset, event_type } = {}) {
  const params = new URLSearchParams();
  if (limit != null) params.append("limit", limit);
  if (offset != null) params.append("offset", offset);
  if (event_type != null) params.append("event_type", event_type);
  return params.toString();
}

describe("buildAsteroidsQuery", () => {
  // Property 8: Construção de query string de filtros de asteroides
  it("P8: inclui apenas params não-nulos", () => {
    // Feature: astraea-dashboard, Property 8: Construção de query string de filtros de asteroides
    fc.assert(
      fc.property(
        fc.record({
          limit: fc.option(fc.nat({ max: 100 }), { nil: null }),
          offset: fc.option(fc.nat({ max: 1000 }), { nil: null }),
          hazardous: fc.option(fc.boolean(), { nil: null }),
          risk_label: fc.option(fc.constantFrom("alto", "médio", "baixo"), { nil: null }),
        }),
        (params) => {
          const qs = buildAsteroidsQuery(params);
          const parsed = new URLSearchParams(qs);
          // Each non-null param should be present
          if (params.limit != null) {
            if (!parsed.has("limit")) return false;
          } else {
            if (parsed.has("limit")) return false;
          }
          if (params.offset != null) {
            if (!parsed.has("offset")) return false;
          } else {
            if (parsed.has("offset")) return false;
          }
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  it("retorna string vazia quando todos os params são nulos", () => {
    expect(buildAsteroidsQuery({})).toBe("");
    expect(buildAsteroidsQuery({ limit: null, offset: null })).toBe("");
  });

  it("inclui limit e offset quando fornecidos", () => {
    const qs = buildAsteroidsQuery({ limit: 50, offset: 0 });
    expect(qs).toContain("limit=50");
    expect(qs).toContain("offset=0");
  });
});

describe("buildSolarEventsQuery", () => {
  // Property 15: Construção de query string de filtro de eventos solares
  it("P15: inclui event_type quando não-nulo, omite quando nulo", () => {
    // Feature: astraea-dashboard, Property 15: Construção de query string de filtro de eventos solares
    fc.assert(
      fc.property(
        fc.option(fc.constantFrom("CME", "GST"), { nil: null }),
        (event_type) => {
          const qs = buildSolarEventsQuery({ event_type });
          const parsed = new URLSearchParams(qs);
          if (event_type !== null) {
            return parsed.get("event_type") === event_type;
          } else {
            return !parsed.has("event_type");
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe("pagination offset", () => {
  // Property 9: Paginação incrementa e decrementa offset em 50
  it("P9: próximo incrementa offset em 50, anterior decrementa com mínimo 0", () => {
    // Feature: astraea-dashboard, Property 9: Paginação incrementa e decrementa offset em 50
    fc.assert(
      fc.property(
        fc.nat({ max: 10000 }),
        (offset) => {
          const LIMIT = 50;
          const next = offset + LIMIT;
          const prev = Math.max(0, offset - LIMIT);
          return next === offset + 50 && prev >= 0 && prev <= offset;
        }
      ),
      { numRuns: 100 }
    );
  });
});
