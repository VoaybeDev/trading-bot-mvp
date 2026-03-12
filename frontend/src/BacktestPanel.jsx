// frontend/src/BacktestPanel.jsx
import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const API_KEY  = import.meta.env.VITE_API_KEY  || "";

async function runBacktest(params) {
  const resp = await fetch(`${API_BASE}/backtest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    },
    body: JSON.stringify(params),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || `Erreur ${resp.status}`);
  }
  return resp.json();
}

// ─── MINI SPARKLINE ───────────────────────────────────────────────────────────

function Sparkline({ data, color = "#00d4ff" }) {
  if (!data || data.length < 2) return null;
  const W = 100, H = 48;
  const values = data.map((d) => d.equity);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const range = maxV - minV || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = H - ((v - minV) / range) * (H - 8) - 4;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const fill = `0,${H} ${pts.join(" ")} ${W},${H}`;
  const gid  = "sparkline_bg";
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
      style={{ width: "100%", height: H, display: "block" }}>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <polygon points={fill} fill={`url(#${gid})`} />
      <polyline points={pts.join(" ")} fill="none" stroke={color}
        strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

// ─── STAT CARD ────────────────────────────────────────────────────────────────

function StatCard({ label, value, color, sub }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: "12px",
      padding: "14px 16px",
    }}>
      <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: "4px" }}>
        {label}
      </div>
      <div style={{
        fontSize: "1.15rem",
        fontWeight: 700,
        fontFamily: "monospace",
        color: color || "var(--text-primary)",
      }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "2px" }}>{sub}</div>}
    </div>
  );
}

// ─── DEFAULT DATES ────────────────────────────────────────────────────────────

function defaultDates() {
  const end   = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 7);
  const fmt = (d) => d.toISOString().slice(0, 16);
  return { start: fmt(start), end: fmt(end) };
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────

export default function BacktestPanel() {
  const dates = defaultDates();
  const [form, setForm] = useState({
    symbol:          "BTCUSDT",
    interval:        "1h",
    start:           dates.start,
    end:             dates.end,
    initial_balance: 8,
    take_profit_usd: 1,
    stop_loss_usd:   -1,
  });
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");

  const intervals = ["1m","3m","5m","15m","30m","1h","2h","4h","6h","12h","1d"];

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((p) => ({ ...p, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const params = {
        symbol:          form.symbol,
        interval:        form.interval,
        start:           form.start,
        end:             form.end,
        initial_balance: Number(form.initial_balance),
        take_profit_usd: Number(form.take_profit_usd),
        stop_loss_usd:   Number(form.stop_loss_usd),
      };
      const data = await runBacktest(params);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const pnlColor = result
    ? result.total_pnl_usd > 0 ? "var(--accent-green)"
    : result.total_pnl_usd < 0 ? "var(--accent-red)"
    : "var(--text-muted)"
    : "var(--text-muted)";

  const eqColor = result && result.equity_curve.length >= 2
    ? result.equity_curve[result.equity_curve.length - 1].equity
      >= result.equity_curve[0].equity ? "#00ff88" : "#ff3b6b"
    : "#00d4ff";

  return (
    <div className="card" style={{ marginBottom: "24px" }}>

      {/* ── HEADER ── */}
      <div style={{ marginBottom: "20px" }}>
        <h2 style={{ margin: 0 }}>📊 Backtesting</h2>
        <p style={{ margin: "4px 0 0", fontSize: "0.8rem", color: "var(--text-muted)" }}>
          Teste ta stratégie sur des données historiques Binance
        </p>
      </div>

      {/* ── FORMULAIRE ── */}
      <form onSubmit={handleSubmit} style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
        gap: "12px",
        marginBottom: "20px",
      }}>
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          Symbol
          <input name="symbol" value={form.symbol} onChange={handleChange}
            style={inputStyle} placeholder="BTCUSDT" />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          Interval
          <select name="interval" value={form.interval} onChange={handleChange} style={inputStyle}>
            {intervals.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          Début
          <input type="datetime-local" name="start" value={form.start} onChange={handleChange} style={inputStyle} />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          Fin
          <input type="datetime-local" name="end" value={form.end} onChange={handleChange} style={inputStyle} />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          Capital ($)
          <input type="number" step="0.01" name="initial_balance" value={form.initial_balance} onChange={handleChange} style={inputStyle} />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          TP ($)
          <input type="number" step="0.01" name="take_profit_usd" value={form.take_profit_usd} onChange={handleChange} style={inputStyle} />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
          SL ($)
          <input type="number" step="0.01" name="stop_loss_usd" value={form.stop_loss_usd} onChange={handleChange} style={inputStyle} />
        </label>

        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <button type="submit" disabled={loading} style={{
            width: "100%",
            padding: "10px",
            background: loading ? "rgba(255,255,255,0.05)" : "var(--gradient-accent)",
            border: "none",
            borderRadius: "8px",
            color: loading ? "var(--text-muted)" : "#000",
            fontWeight: 700,
            fontSize: "0.85rem",
            cursor: loading ? "not-allowed" : "pointer",
            transition: "all 0.2s",
          }}>
            {loading ? "⏳ Calcul..." : "▶ Lancer"}
          </button>
        </div>
      </form>

      {error && <div className="alert error" style={{ marginBottom: "16px" }}>{error}</div>}

      {/* ── RÉSULTATS ── */}
      {result && (
        <div>
          {/* Stats principales */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
            gap: "10px",
            marginBottom: "16px",
          }}>
            <StatCard
              label="Capital final"
              value={`${result.final_equity} $`}
              color="var(--accent-cyan)"
            />
            <StatCard
              label="PnL total"
              value={`${result.total_pnl_usd > 0 ? "+" : ""}${result.total_pnl_usd} $`}
              color={pnlColor}
              sub={`${result.total_pnl_pct > 0 ? "+" : ""}${result.total_pnl_pct}%`}
            />
            <StatCard
              label="Trades"
              value={result.total_trades}
              sub={`${result.winning_trades}W / ${result.losing_trades}L`}
            />
            <StatCard
              label="Win rate"
              value={`${result.win_rate}%`}
              color={result.win_rate >= 50 ? "var(--accent-green)" : "var(--accent-red)"}
            />
            <StatCard
              label="Max drawdown"
              value={`${result.max_drawdown_pct}%`}
              color={result.max_drawdown_pct > 20 ? "var(--accent-red)" : "var(--text-primary)"}
            />
            <StatCard
              label="Moy. gain"
              value={`+${result.avg_win_usd} $`}
              color="var(--accent-green)"
            />
            <StatCard
              label="Moy. perte"
              value={`${result.avg_loss_usd} $`}
              color="var(--accent-red)"
            />
            <StatCard
              label="Bougies"
              value={result.klines_count}
            />
          </div>

          {/* Courbe equity */}
          {result.equity_curve.length >= 2 && (
            <div style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.07)",
              borderRadius: "12px",
              padding: "14px",
              marginBottom: "16px",
            }}>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "8px" }}>
                Courbe d'equity
              </div>
              <Sparkline data={result.equity_curve} color={eqColor} />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px" }}>
                <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                  {result.equity_curve[0].equity} $
                </span>
                <span style={{ fontSize: "0.7rem", color: eqColor, fontFamily: "monospace", fontWeight: 600 }}>
                  {result.equity_curve[result.equity_curve.length - 1].equity} $
                </span>
              </div>
            </div>
          )}

          {/* Liste des trades */}
          {result.trades.length > 0 && (
            <div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "8px" }}>
                Trades exécutés ({result.trades.length})
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Entrée</th>
                      <th>Sortie</th>
                      <th>Qty</th>
                      <th>PnL</th>
                      <th>Raison</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((t, i) => (
                      <tr key={i}>
                        <td>{i + 1}</td>
                        <td style={{ fontFamily: "monospace" }}>{t.entry_price}</td>
                        <td style={{ fontFamily: "monospace" }}>{t.exit_price}</td>
                        <td style={{ fontFamily: "monospace" }}>{t.quantity}</td>
                        <td style={{
                          color: t.pnl > 0 ? "var(--accent-green)" : "var(--accent-red)",
                          fontWeight: 600,
                          fontFamily: "monospace",
                        }}>
                          {t.pnl > 0 ? "+" : ""}{t.pnl}
                        </td>
                        <td>
                          <span style={{
                            padding: "2px 8px",
                            borderRadius: "6px",
                            fontSize: "0.7rem",
                            fontWeight: 700,
                            background: t.reason === "TP" ? "rgba(0,255,136,0.1)"
                              : t.reason === "SL" ? "rgba(255,59,107,0.1)"
                              : "rgba(255,255,255,0.05)",
                            color: t.reason === "TP" ? "var(--accent-green)"
                              : t.reason === "SL" ? "var(--accent-red)"
                              : "var(--text-muted)",
                          }}>
                            {t.reason}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {result.total_trades === 0 && (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", padding: "20px 0" }}>
              Aucun trade exécuté sur cette période — essaie un interval plus court ou une période plus longue.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

const inputStyle = {
  background: "rgba(255,255,255,0.05)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "8px",
  color: "var(--text-primary)",
  padding: "7px 10px",
  fontSize: "0.82rem",
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};