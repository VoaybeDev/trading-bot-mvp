// frontend/src/HealthDashboard.jsx
import { useState, useEffect, useCallback } from "react";
import { getHealth } from "./api";

// ─── HELPERS ──────────────────────────────────────────────────────────────────

function statusColor(s) {
  if (s === "ok" || s === "running") return "var(--accent-green)";
  if (s === "degraded")             return "#f59e0b";
  if (s === "stopped")              return "var(--text-muted)";
  return "var(--accent-red)";
}

function statusBg(s) {
  if (s === "ok" || s === "running") return "rgba(0,255,136,0.08)";
  if (s === "degraded")              return "rgba(245,158,11,0.08)";
  if (s === "stopped")               return "rgba(255,255,255,0.04)";
  return "rgba(255,59,107,0.08)";
}

function StatusBadge({ value }) {
  return (
    <span style={{
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: "999px",
      fontSize: "0.72rem",
      fontWeight: 700,
      letterSpacing: "0.05em",
      textTransform: "uppercase",
      color: statusColor(value),
      background: statusBg(value),
      border: `1px solid ${statusColor(value)}33`,
    }}>
      {value}
    </span>
  );
}

function Metric({ label, value, unit = "", highlight }) {
  return (
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "6px 0",
      borderBottom: "1px solid rgba(255,255,255,0.05)",
    }}>
      <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>{label}</span>
      <span style={{
        fontFamily: "monospace",
        fontWeight: 600,
        fontSize: "0.85rem",
        color: highlight || "var(--text-primary)",
      }}>
        {value !== null && value !== undefined ? `${value}${unit}` : "—"}
      </span>
    </div>
  );
}

function ComponentCard({ title, icon, data, children }) {
  const s = data?.status || "unknown";
  return (
    <div style={{
      background: "var(--glass-bg)",
      border: `1px solid ${statusColor(s)}33`,
      borderRadius: "16px",
      padding: "20px",
      display: "flex",
      flexDirection: "column",
      gap: "12px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "1.1rem" }}>{icon}</span>
          <h3 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 700, color: "var(--text-primary)" }}>
            {title}
          </h3>
        </div>
        <StatusBadge value={s} />
      </div>
      <div>{children}</div>
    </div>
  );
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────

export default function HealthDashboard() {
  const [health, setHealth]     = useState(null);
  const [loading, setLoading]   = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError]       = useState("");

  const load = useCallback(async () => {
    try {
      const data = await getHealth();
      setHealth(data);
      setLastUpdate(new Date().toLocaleTimeString());
      setError("");
    } catch  {
      setError("Impossible de joindre /health");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  const db     = health?.components?.database;
  const bot    = health?.components?.bot;
  const wallet = health?.components?.wallet;
  const market = health?.components?.market;

  const globalStatus = health?.status || "unknown";
  const globalColor  = statusColor(globalStatus);

  return (
    <div className="card" style={{ marginBottom: "24px" }}>

      {/* ── HEADER ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <h2 style={{ margin: 0 }}>Health</h2>
          {!loading && <StatusBadge value={globalStatus} />}
          {loading && (
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>chargement...</span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {lastUpdate && (
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
              màj {lastUpdate}
            </span>
          )}
          <button
            onClick={load}
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              color: "var(--text-secondary)",
              fontSize: "0.75rem",
              padding: "4px 10px",
              cursor: "pointer",
            }}
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* ── BARRE GLOBALE ── */}
      {health && (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "12px 16px",
          borderRadius: "12px",
          background: statusBg(globalStatus),
          border: `1px solid ${globalColor}33`,
          marginBottom: "20px",
        }}>
          <div style={{
            width: "10px", height: "10px", borderRadius: "50%",
            background: globalColor,
            boxShadow: `0 0 8px ${globalColor}`,
            flexShrink: 0,
          }} />
          <span style={{ fontSize: "0.85rem", color: globalColor, fontWeight: 600 }}>
            Système {globalStatus === "ok" ? "opérationnel" : globalStatus === "degraded" ? "dégradé" : "en erreur"}
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginLeft: "auto", fontFamily: "monospace" }}>
            v{health.version} · {health.timestamp}
          </span>
        </div>
      )}

      {error && (
        <div className="alert error" style={{ marginBottom: "16px" }}>{error}</div>
      )}

      {/* ── 4 CARTES ── */}
      {health && (
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "16px",
        }}>

          {/* DATABASE */}
          <ComponentCard title="Base de données" icon="🗄️" data={db}>
            <Metric label="Latence"      value={db?.latency_ms}   unit=" ms"  highlight="var(--accent-cyan)" />
            <Metric label="Taille"       value={db?.size_kb}      unit=" KB" />
            <Metric label="Trades"       value={db?.trades_count} />
            <Metric label="Logs"         value={db?.logs_count} />
            <Metric label="Max trades"   value={db?.max_trades} />
            <Metric label="Max logs"     value={db?.max_logs} />
          </ComponentCard>

          {/* BOT */}
          <ComponentCard title="Bot" icon="🤖" data={bot}>
            <Metric label="Statut"       value={bot?.status} highlight={statusColor(bot?.status)} />
            <Metric label="Symbol"       value={bot?.symbol}       highlight="var(--accent-cyan)" />
            <Metric label="Prix actuel"  value={bot?.current_price} unit=" $" highlight="var(--accent-cyan)" />
            <Metric label="Erreurs consécutives" value={bot?.consecutive_errors}
              highlight={bot?.consecutive_errors >= 3 ? "var(--accent-red)" : undefined} />
            <Metric label="Taux d'erreur" value={bot?.error_rate !== undefined ? (bot.error_rate * 100).toFixed(1) : null} unit="%" />
          </ComponentCard>

          {/* WALLET */}
          <ComponentCard title="Wallet" icon="💰" data={{ status: "ok" }}>
            <Metric label="Equity"      value={wallet?.equity}        unit=" $" highlight="var(--accent-cyan)" />
            <Metric label="PnL journalier"
              value={wallet?.daily_pnl_usd !== undefined ? (wallet.daily_pnl_usd >= 0 ? "+" : "") + wallet.daily_pnl_usd : null}
              unit=" $"
              highlight={wallet?.daily_pnl_usd > 0 ? "var(--accent-green)" : wallet?.daily_pnl_usd < 0 ? "var(--accent-red)" : undefined}
            />
            <Metric label="PnL %"
              value={wallet?.daily_pnl_pct !== undefined ? (wallet.daily_pnl_pct >= 0 ? "+" : "") + wallet.daily_pnl_pct?.toFixed(2) : null}
              unit="%"
              highlight={wallet?.daily_pnl_pct > 0 ? "var(--accent-green)" : wallet?.daily_pnl_pct < 0 ? "var(--accent-red)" : undefined}
            />
            <Metric label="Position ouverte"
              value={wallet?.has_position !== undefined ? (wallet.has_position ? "Oui" : "Non") : null}
              highlight={wallet?.has_position ? "var(--accent-green)" : undefined}
            />
          </ComponentCard>

          {/* MARKET */}
          <ComponentCard title="Marché" icon="📈" data={{ status: "ok" }}>
            <Metric label="Signal"
              value={market?.signal}
              highlight={
                market?.signal === "BUY"  ? "var(--accent-green)" :
                market?.signal === "SELL" ? "var(--accent-red)"   : undefined
              }
            />
            <Metric label="Score"       value={market?.score}         unit="%" />
            <Metric label="Prix"        value={market?.current_price} unit=" $" highlight="var(--accent-cyan)" />
            <Metric label="MA10"        value={market?.ma10} />
            <Metric label="MA20"        value={market?.ma20} />
          </ComponentCard>

        </div>
      )}
    </div>
  );
}