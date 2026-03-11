// frontend/src/tests/api.test.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getStatus,
  getTrades,
  getLogs,
  getSettings,
  startBot,
  stopBot,
  tickBot,
  resetBot,
  resetSettings,
  updateSettings,
  getHealth,
} from "../api.js";

// ─── MOCK global fetch (vi.stubGlobal évite le warning TypeScript) ────────────

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  };
}


// ─── getStatus ────────────────────────────────────────────────────────────────

describe("getStatus", () => {
  it("appelle GET /status", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ running: false }));
    await getStatus();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/status"),
      expect.anything()
    );
  });

  it("retourne les données JSON", async () => {
    const data = { running: true, wallet: { equity: 8.0 } };
    mockFetch.mockResolvedValueOnce(mockResponse(data));
    expect(await getStatus()).toEqual(data);
  });

  it("lance une erreur si 403", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({}, 403));
    await expect(getStatus()).rejects.toThrow();
  });

  it("lance une erreur si 500", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({}, 500));
    await expect(getStatus()).rejects.toThrow();
  });

  it("lance une erreur si réseau down", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));
    await expect(getStatus()).rejects.toThrow("Network error");
  });
});


// ─── startBot ─────────────────────────────────────────────────────────────────

describe("startBot", () => {
  it("appelle POST /start", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ running: true }));
    await startBot();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/start"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("retourne le snapshot du bot", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ running: true }));
    expect((await startBot()).running).toBe(true);
  });
});


// ─── stopBot ──────────────────────────────────────────────────────────────────

describe("stopBot", () => {
  it("appelle POST /stop", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ running: false }));
    await stopBot();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/stop"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("retourne running: false", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ running: false }));
    expect((await stopBot()).running).toBe(false);
  });
});


// ─── tickBot ──────────────────────────────────────────────────────────────────

describe("tickBot", () => {
  it("appelle POST /tick", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({}));
    await tickBot();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/tick"),
      expect.objectContaining({ method: "POST" })
    );
  });
});


// ─── resetBot ─────────────────────────────────────────────────────────────────

describe("resetBot", () => {
  it("appelle POST /reset", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({}));
    await resetBot();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/reset"),
      expect.objectContaining({ method: "POST" })
    );
  });
});


// ─── getTrades ────────────────────────────────────────────────────────────────

describe("getTrades", () => {
  it("appelle GET /trades", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse([]));
    await getTrades();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/trades"),
      expect.anything()
    );
  });

  it("retourne un tableau de trades", async () => {
    const trades = [{ id: 1, pnl: 1.5, side: "BUY", entry_price: 50000 }];
    mockFetch.mockResolvedValueOnce(mockResponse(trades));
    const result = await getTrades();
    expect(result).toHaveLength(1);
    expect(result[0].pnl).toBe(1.5);
  });

  it("retourne un tableau vide", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse([]));
    expect(await getTrades()).toEqual([]);
  });
});


// ─── getLogs ──────────────────────────────────────────────────────────────────

describe("getLogs", () => {
  it("appelle GET /logs", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse([]));
    await getLogs();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/logs"),
      expect.anything()
    );
  });

  it("retourne un tableau de logs", async () => {
    const logs = [{ id: 1, message: "Bot démarré", created_at: "2026-03-09" }];
    mockFetch.mockResolvedValueOnce(mockResponse(logs));
    expect((await getLogs())[0].message).toBe("Bot démarré");
  });
});


// ─── getSettings ──────────────────────────────────────────────────────────────

describe("getSettings", () => {
  it("appelle GET /settings", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({}));
    await getSettings();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/settings"),
      expect.anything()
    );
  });

  it("retourne les paramètres", async () => {
    const settings = { symbol: "BTCUSDT", interval: "1m", initial_balance: 8.0 };
    mockFetch.mockResolvedValueOnce(mockResponse(settings));
    expect((await getSettings()).symbol).toBe("BTCUSDT");
  });
});


// ─── updateSettings ───────────────────────────────────────────────────────────

describe("updateSettings", () => {
  it("appelle POST /settings/update avec les données", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ message: "ok" }));
    await updateSettings({ symbol: "ETHUSDT" });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/settings/update"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ symbol: "ETHUSDT" }),
      })
    );
  });

  it("envoie Content-Type: application/json", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({}));
    await updateSettings({ take_profit_usd: 2.0 });
    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers["Content-Type"]).toBe("application/json");
  });
});


// ─── resetSettings ────────────────────────────────────────────────────────────

describe("resetSettings", () => {
  it("appelle POST /settings/reset", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({}));
    await resetSettings();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/settings/reset"),
      expect.objectContaining({ method: "POST" })
    );
  });
});


// ─── Messages d'erreur ────────────────────────────────────────────────────────

describe("Messages d'erreur", () => {
  it("erreur 403 mentionne la clé API", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({}, 403));
    await expect(getStatus()).rejects.toThrow(/cle API|403|refuse/i);
  });

  it("utilise le champ detail de l'API si présent", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Valeur invalide" }),
    });
    await expect(updateSettings({})).rejects.toThrow("Valeur invalide");
  });
});
describe("getHealth", () => {
  it("appelle GET /health", async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ status: "ok" }));
    await getHealth();
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/health"),
      expect.anything()
    );
  });

  it("retourne le rapport de santé", async () => {
    const health = { status: "ok", version: "1.0.0",
      components: { database: { status: "ok" } } };
    mockFetch.mockResolvedValueOnce(mockResponse(health));
    const result = await getHealth();
    expect(result.status).toBe("ok");
    expect(result.components.database.status).toBe("ok");
  });
});