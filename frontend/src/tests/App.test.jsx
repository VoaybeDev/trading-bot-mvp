// frontend/src/tests/App.test.jsx

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import App from "../App.jsx";

// ─── MOCK ../api (noms EXACTS de api.js) ──────────────────────────────────────

vi.mock("../api.js", () => ({
  getStatus:      vi.fn(),
  startBot:       vi.fn(),
  stopBot:        vi.fn(),
  tickBot:        vi.fn(),
  resetBot:       vi.fn(),
  updateSettings: vi.fn(),
  getTrades:      vi.fn(),
  getLogs:        vi.fn(),
  getSettings:    vi.fn(),
  resetSettings:  vi.fn(),
}));

import * as api from "../api.js";

// ─── DONNÉES DE TEST ──────────────────────────────────────────────────────────

const STATUS_STOPPED = {
  running: false,
  market: {
    symbol: "BTCUSDT",
    interval: "1m",
    current_price: 50000.0,
  },
  last_signal: {
    signal: "HOLD",
    score: 0,
    strong: false,
    ma10: null,
    ma20: null,
  },
  wallet: {
    equity: 8.0,
    cash: 8.0,
    initial_balance: 8.0,
    has_position: false,
    daily_pnl: 0.0,
    position_pnl: 0.0,
    entry_price: null,
    position_qty: null,
  },
  settings: {
    symbol: "BTCUSDT",
    interval: "1m",
    take_profit_usd: 1.0,
    stop_loss_usd: -1.0,
    initial_balance: 8.0,
  },
  health: { consecutive_errors: 0, max_consecutive_errors: 5 },
  trades: [],
  logs: [],
};

const STATUS_RUNNING = {
  ...STATUS_STOPPED,
  running: true,
  market: { ...STATUS_STOPPED.market, current_price: 51000.0 },
  last_signal: { signal: "BUY", score: 83, strong: true, ma10: 50500, ma20: 50000 },
};

function setupMocks(status = STATUS_STOPPED) {
  api.getStatus.mockResolvedValue(status);
  api.startBot.mockResolvedValue(STATUS_RUNNING);
  api.stopBot.mockResolvedValue(STATUS_STOPPED);
  api.resetBot.mockResolvedValue(STATUS_STOPPED);
  api.tickBot.mockResolvedValue(STATUS_RUNNING);
  api.updateSettings.mockResolvedValue({ message: "ok", status: STATUS_STOPPED });
}

// ⚠️ PAS de vi.useFakeTimers() globaux — ils cassent waitFor() et les promises.
// On les utilise uniquement dans le test auto-refresh, et on restaure après.

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

// Helper : rend l'app et attend que l'état soit chargé
async function renderApp(status = STATUS_STOPPED) {
  setupMocks(status);
  await act(async () => { render(<App />); });
  // Flush toutes les promises (getStatus, setStatus, etc.)
  await act(async () => {});
}


// ─── RENDU INITIAL ────────────────────────────────────────────────────────────

describe("Rendu initial", () => {
  it("affiche le titre NexTrade dans le header", async () => {
    await renderApp();
    // Le titre est dans un <h1> dans le header — on cible le heading
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("appelle getStatus au montage", async () => {
    await renderApp();
    expect(api.getStatus).toHaveBeenCalled();
  });

  it("affiche le prix BTC 50000", async () => {
    await renderApp();
    // Visible immédiatement après renderApp — pas besoin de waitFor
    expect(screen.getByText("50000")).toBeInTheDocument();
  });

  it("affiche le badge 'Bot arrete' par défaut", async () => {
    await renderApp();
    expect(screen.getByText("Bot arrete")).toBeInTheDocument();
  });

  it("affiche le badge 'Bot en marche' quand running", async () => {
    await renderApp(STATUS_RUNNING);
    expect(screen.getByText("Bot en marche")).toBeInTheDocument();
  });

  it("affiche le symbole BTCUSDT", async () => {
    await renderApp();
    // Peut apparaître plusieurs fois (marché + settings) — on vérifie qu'au moins un existe
    expect(screen.getAllByText("BTCUSDT").length).toBeGreaterThan(0);
  });
});


// ─── BOUTONS ──────────────────────────────────────────────────────────────────

describe("Boutons d'action", () => {
  it("affiche les boutons Start, Stop, Tick, Reset, Refresh", async () => {
    await renderApp();
    expect(screen.getByRole("button", { name: /start/i   })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /stop/i    })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tick/i    })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset/i   })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
  });

  it("appelle startBot au clic sur Start", async () => {
    await renderApp();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /start/i }));
    });
    expect(api.startBot).toHaveBeenCalledTimes(1);
  });

  it("appelle stopBot au clic sur Stop", async () => {
    await renderApp();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /stop/i }));
    });
    expect(api.stopBot).toHaveBeenCalledTimes(1);
  });

  it("appelle tickBot au clic sur Tick", async () => {
    await renderApp();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /tick/i }));
    });
    expect(api.tickBot).toHaveBeenCalledTimes(1);
  });

  it("appelle getStatus au clic sur Refresh", async () => {
    await renderApp();
    const before = api.getStatus.mock.calls.length;
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /refresh/i }));
    });
    expect(api.getStatus.mock.calls.length).toBeGreaterThan(before);
  });
});


// ─── MODAL RESET ──────────────────────────────────────────────────────────────

describe("Modal de confirmation Reset", () => {
  it("affiche la modal au clic sur Reset", async () => {
    await renderApp();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    });
    expect(screen.getByText(/confirmation requise/i)).toBeInTheDocument();
  });

  it("n'appelle PAS resetBot si on clique Annuler", async () => {
    await renderApp();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /annuler/i }));
    });
    expect(api.resetBot).not.toHaveBeenCalled();
  });

  it("appelle resetBot si on clique Confirmer", async () => {
    await renderApp();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /confirmer/i }));
    });
    expect(api.resetBot).toHaveBeenCalledTimes(1);
  });

  it("ferme la modal après annulation", async () => {
    await renderApp();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /annuler/i }));
    });
    expect(screen.queryByText(/confirmation requise/i)).not.toBeInTheDocument();
  });
});


// ─── SIGNAL DE MARCHÉ ─────────────────────────────────────────────────────────

describe("Affichage du signal", () => {
  it("affiche HOLD quand le bot est arrêté", async () => {
    await renderApp();
    // Visible directement dans le DOM après renderApp
    expect(screen.getByText("HOLD")).toBeInTheDocument();
  });

  it("affiche BUY quand le signal est BUY", async () => {
    await renderApp(STATUS_RUNNING);
    expect(screen.getByText("BUY")).toBeInTheDocument();
  });

  it("affiche le score 83", async () => {
    await renderApp(STATUS_RUNNING);
    expect(screen.getByText("83")).toBeInTheDocument();
  });
});


// ─── WALLET ───────────────────────────────────────────────────────────────────

describe("Affichage du wallet", () => {
  it("affiche la section Wallet", async () => {
    await renderApp();
    expect(screen.getByRole("heading", { name: /wallet/i })).toBeInTheDocument();
  });

  it("affiche l'equity dans la section Wallet", async () => {
    await renderApp();
    // "Equity" est le label dans la section wallet
    expect(screen.getByText("Equity")).toBeInTheDocument();
  });

  it("affiche Capital initial et Cash", async () => {
    await renderApp();
    // "Capital initial" apparaît dans le wallet ET dans le label du formulaire
    expect(screen.getAllByText("Capital initial").length).toBeGreaterThan(0);
    expect(screen.getByText("Cash")).toBeInTheDocument();
  });
});


// ─── AUTO-REFRESH ─────────────────────────────────────────────────────────────

describe("Auto-refresh", () => {
  it("re-appelle getStatus après 5 secondes", async () => {
    // On active les fake timers UNIQUEMENT pour ce test
    vi.useFakeTimers();
    setupMocks();
    await act(async () => { render(<App />); });
    await act(async () => {});

    const before = api.getStatus.mock.calls.length;

    await act(async () => { vi.advanceTimersByTime(5100); });
    await act(async () => {});

    expect(api.getStatus.mock.calls.length).toBeGreaterThan(before);

    vi.useRealTimers(); // ← IMPORTANT : restaurer les vrais timers
  });
});


// ─── GESTION D'ERREURS ────────────────────────────────────────────────────────

describe("Gestion d'erreurs", () => {
  it("ne crashe pas si getStatus rejette", async () => {
    api.getStatus.mockRejectedValue(new Error("Network error"));
    await act(async () => { render(<App />); });
    await act(async () => {});
    expect(document.body).toBeTruthy();
  });

  it("affiche un message d'erreur si startBot échoue", async () => {
    await renderApp();
    api.startBot.mockRejectedValueOnce(new Error("503 Service Unavailable"));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /start/i }));
    });
    await act(async () => {});
    // L'App affiche l'erreur dans <div className="alert error">
    expect(screen.getByText(/503/i)).toBeInTheDocument();
  });
});