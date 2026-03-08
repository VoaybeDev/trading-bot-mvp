import { useEffect, useState } from "react";
import { getStatus, startBot, stopBot, tickBot, resetBot, updateSettings } from "./api";

const defaultForm = {
  symbol: "BTCUSDT",
  interval: "1m",
  take_profit_usd: 1,
  stop_loss_usd: -1,
  initial_balance: 8,
};

function GitHubIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.385-1.335-1.755-1.335-1.755-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

function FooterLink() {
  const [hovered, setHovered] = useState(false);

  const base = {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    textDecoration: "none",
    fontSize: "0.85rem",
    fontWeight: "600",
    padding: "8px 16px",
    borderRadius: "999px",
    transition: "all 0.2s ease",
    border: hovered ? "1px solid rgba(0,212,255,0.35)" : "1px solid rgba(255,255,255,0.08)",
    background: "rgba(255,255,255,0.03)",
    color: hovered ? "var(--accent-cyan)" : "var(--text-secondary)",
    boxShadow: hovered ? "0 0 18px rgba(0,212,255,0.12)" : "none",
  };

  return (
    <a
      href="https://github.com/VoaybeDev"
      target="_blank"
      rel="noopener noreferrer"
      style={base}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <GitHubIcon />
      VoaybeDev
    </a>
  );
}

function InfoRow({ label, value, highlight }) {
  const colorMap = { green: "var(--accent-green)", red: "var(--accent-red)", cyan: "var(--accent-cyan)" };
  return (
    <div>
      <strong>{label}</strong>
      <span style={highlight ? { color: colorMap[highlight] } : {}}>{value ?? "—"}</span>
    </div>
  );
}

function App() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState(defaultForm);

  async function loadStatus() {
    try {
      setLoading(true);
      setError("");
      const data = await getStatus();
      setStatus(data);
      if (data && data.settings) {
        setForm({
          symbol: data.settings.symbol || "BTCUSDT",
          interval: data.settings.interval || "1m",
          take_profit_usd: data.settings.take_profit_usd || 1,
          stop_loss_usd: data.settings.stop_loss_usd || -1,
          initial_balance: data.settings.initial_balance || 8,
        });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStatus();
    const id = setInterval(loadStatus, 5000);
    return () => clearInterval(id);
  }, []);

  async function handleAction(actionFn, successText) {
    try {
      setActionLoading(true);
      setError("");
      setMessage("");
      const data = await actionFn();
      setStatus(data);
      if (data && data.settings) {
        setForm({
          symbol: data.settings.symbol || "BTCUSDT",
          interval: data.settings.interval || "1m",
          take_profit_usd: data.settings.take_profit_usd || 1,
          stop_loss_usd: data.settings.stop_loss_usd || -1,
          initial_balance: data.settings.initial_balance || 8,
        });
      }
      if (successText) setMessage(successText);
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleUpdateSettings(e) {
    e.preventDefault();
    try {
      setActionLoading(true);
      setError("");
      setMessage("");
      const payload = {
        symbol: form.symbol,
        interval: form.interval,
        take_profit_usd: Number(form.take_profit_usd),
        stop_loss_usd: Number(form.stop_loss_usd),
        initial_balance: Number(form.initial_balance),
      };
      const result = await updateSettings(payload);
      setStatus(result.status);
      setMessage(result.message || "Parametres mis a jour");
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  function handleInputChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  const market = status && status.market;
  const settings = status && status.settings;
  const wallet = status && status.wallet;
  const signal = status && status.last_signal;
  const trades = (status && status.trades) || [];
  const logs = (status && status.logs) || [];

  const pnlHighlight = wallet && wallet.daily_pnl > 0 ? "green" : wallet && wallet.daily_pnl < 0 ? "red" : null;
  const signalHighlight = signal && signal.signal === "BUY" ? "green" : signal && signal.signal === "SELL" ? "red" : null;

  const actionButtons = [
    { label: "Refresh", fn: () => handleAction(loadStatus, "Donnees actualisees") },
    { label: "Start",   fn: () => handleAction(startBot,   "Bot demarre") },
    { label: "Stop",    fn: () => handleAction(stopBot,    "Bot arrete") },
    { label: "Tick",    fn: () => handleAction(tickBot,    "Tick execute") },
    { label: "Reset",   fn: () => handleAction(resetBot,   "Bot reinitialise") },
  ];

  const intervals = ["1m","3m","5m","15m","30m","1h","2h","4h","6h","8h","12h","1d"];

  return (
    <div className="page">

      <header className="header">
        <div className="header-brand">
          <h1>
            <span style={{ fontStyle: "italic" }}>Nex</span>
            <span style={{ background: "var(--gradient-accent)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>Trade</span>
            <sup style={{ fontSize: "0.45em", color: "var(--accent-purple)", fontWeight: 400, marginLeft: "4px" }}>v1</sup>
          </h1>
          <p>Surveillance et Controle en temps reel</p>
        </div>
        <div className={status && status.running ? "badge running" : "badge stopped"}>
          {status && status.running ? "Bot en marche" : "Bot arrete"}
        </div>
      </header>

      {error   && <div className="alert error">  {error}   </div>}
      {message && <div className="alert success"> {message} </div>}

      <section className="actions">
        {actionButtons.map(function(item) {
          return (
            <button key={item.label} onClick={item.fn} disabled={actionLoading}>
              {item.label}
            </button>
          );
        })}
      </section>

      {loading && !status ? (
        <div className="card loading-state">
          <span className="spinner" />
          Chargement...
        </div>
      ) : (
        <div>
          <section className="grid two">
            <div className="card">
              <h2>Marche</h2>
              <div className="info-list">
                <InfoRow label="Symbol"      value={market && market.symbol}        highlight="cyan" />
                <InfoRow label="Interval"    value={market && market.interval} />
                <InfoRow label="Prix actuel" value={market && market.current_price} highlight="cyan" />
              </div>
            </div>

            <div className="card">
              <h2>Signal</h2>
              <div className="info-list">
                <InfoRow label="Signal" value={signal && signal.signal} highlight={signalHighlight} />
                <InfoRow label="Score"  value={signal && signal.score} />
                <InfoRow label="Strong" value={signal ? String(signal.strong) : "—"} />
                <InfoRow label="MA10"   value={signal && signal.ma10} />
                <InfoRow label="MA20"   value={signal && signal.ma20} />
              </div>
            </div>
          </section>

          <section className="grid two">
            <div className="card">
              <h2>Wallet</h2>
              <div className="info-list">
                <InfoRow label="Capital initial"  value={wallet && wallet.initial_balance} />
                <InfoRow label="Cash"             value={wallet && wallet.cash}            highlight="cyan" />
                <InfoRow label="Position ouverte" value={wallet ? String(wallet.has_position) : "—"} />
                <InfoRow label="Entry price"      value={wallet && wallet.entry_price} />
                <InfoRow label="Position qty"     value={wallet && wallet.position_qty} />
                <InfoRow label="Equity"           value={wallet && wallet.equity}          highlight="cyan" />
                <InfoRow label="Position PnL"     value={wallet && wallet.position_pnl}    highlight={pnlHighlight} />
                <InfoRow label="Daily PnL"        value={wallet && wallet.daily_pnl}       highlight={pnlHighlight} />
              </div>
            </div>

            <div className="card">
              <h2>Parametres</h2>
              <form onSubmit={handleUpdateSettings} className="settings-form">
                <label>
                  Symbol
                  <input name="symbol" value={form.symbol} onChange={handleInputChange} placeholder="BTCUSDT" />
                </label>
                <label>
                  Interval
                  <select name="interval" value={form.interval} onChange={handleInputChange}>
                    {intervals.map(function(v) { return <option key={v} value={v}>{v}</option>; })}
                  </select>
                </label>
                <label>
                  Take Profit USD
                  <input type="number" step="0.01" name="take_profit_usd" value={form.take_profit_usd} onChange={handleInputChange} />
                </label>
                <label>
                  Stop Loss USD
                  <input type="number" step="0.01" name="stop_loss_usd" value={form.stop_loss_usd} onChange={handleInputChange} />
                </label>
                <label>
                  Capital initial
                  <input type="number" step="0.01" name="initial_balance" value={form.initial_balance} onChange={handleInputChange} />
                </label>
                <button type="submit" disabled={actionLoading}>
                  Sauvegarder les parametres
                </button>
              </form>

              {settings && (
                <div className="current-settings">
                  <h3>Parametres actifs</h3>
                  <div><strong>Symbol</strong>   <span>{settings.symbol}</span></div>
                  <div><strong>Interval</strong> <span>{settings.interval}</span></div>
                  <div><strong>TP</strong>        <span>{settings.take_profit_usd}</span></div>
                  <div><strong>SL</strong>        <span>{settings.stop_loss_usd}</span></div>
                  <div><strong>Capital</strong>  <span>{settings.initial_balance}</span></div>
                </div>
              )}
            </div>
          </section>

          <section className="grid two">
            <div className="card">
              <h2>Trades</h2>
              {trades.length === 0 ? (
                <p>Aucun trade pour le moment.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Side</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Qty</th>
                        <th>PnL</th>
                        <th>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.map(function(t) {
                        return (
                          <tr key={t.id}>
                            <td>{t.id}</td>
                            <td style={{ color: t.side === "BUY" ? "var(--accent-green)" : "var(--accent-red)", fontWeight: 600 }}>{t.side}</td>
                            <td>{t.entry_price}</td>
                            <td>{t.exit_price}</td>
                            <td>{t.quantity}</td>
                            <td style={{ color: t.pnl >= 0 ? "var(--accent-green)" : "var(--accent-red)", fontWeight: 600 }}>{t.pnl}</td>
                            <td>{t.reason}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="card">
              <h2>Logs</h2>
              {logs.length === 0 ? (
                <p>Aucun log pour le moment.</p>
              ) : (
                <div className="logs-box">
                  {logs.map(function(log) {
                    return (
                      <div key={log.id} className="log-item">
                        <div className="log-date">{log.created_at}</div>
                        <div className="log-message">{log.message}</div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        </div>
      )}

      <footer style={{ marginTop: "40px", paddingTop: "24px", borderTop: "1px solid var(--glass-border)", display: "flex", justifyContent: "center", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>Built by</span>
        <FooterLink />
        <span style={{ color: "var(--text-muted)", fontSize: "0.72rem", fontFamily: "monospace" }}>
          NexTrade v1 &copy; {new Date().getFullYear()}
        </span>
      </footer>

    </div>
  );
}

export default App;