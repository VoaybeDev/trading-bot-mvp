import { useEffect, useState, useRef, useCallback } from "react";
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
  const style = {
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
      style={style}
      onMouseEnter={function() { setHovered(true); }}
      onMouseLeave={function() { setHovered(false); }}
    >
      <GitHubIcon />
      VoaybeDev
    </a>
  );
}

function InfoRow(props) {
  const colorMap = {
    green: "var(--accent-green)",
    red: "var(--accent-red)",
    cyan: "var(--accent-cyan)",
  };
  return (
    <div>
      <strong>{props.label}</strong>
      <span style={props.highlight ? { color: colorMap[props.highlight] } : {}}>
        {props.value !== undefined && props.value !== null ? props.value : "—"}
      </span>
    </div>
  );
}

function ConfirmModal(props) {
  return (
    <div className="modal-overlay" onClick={props.onCancel}>
      <div className="modal-box" onClick={function(e) { e.stopPropagation(); }}>
        <div className="modal-icon">⚠</div>
        <h3 className="modal-title">Confirmation requise</h3>
        <p className="modal-message">{props.message}</p>
        <div className="modal-actions">
          <button className="modal-btn cancel" onClick={props.onCancel}>Annuler</button>
          <button className="modal-btn confirm" onClick={props.onConfirm}>Confirmer</button>
        </div>
      </div>
    </div>
  );
}

function MiniChart(props) {
  const data = props.data;
  const color = props.color || "#00d4ff";
  const H = 90;
  const W = 100;

  if (!data || data.length < 2) {
    return (
      <div className="chart-empty">
        <span>En attente de donnees...</span>
      </div>
    );
  }

  const values = data.map(function(d) { return d.value; });
  const minV = Math.min.apply(null, values);
  const maxV = Math.max.apply(null, values);
  const range = maxV - minV || 1;

  const pts = data.map(function(d, i) {
    const x = (i / (data.length - 1)) * W;
    const y = H - ((d.value - minV) / range) * (H - 12) - 6;
    return x.toFixed(2) + "," + y.toFixed(2);
  });

  const lastPt = pts[pts.length - 1].split(",");
  const lastX = parseFloat(lastPt[0]);
  const lastY = parseFloat(lastPt[1]);
  const fillPts = "0," + H + " " + pts.join(" ") + " " + W + "," + H;
  const gid = "g" + color.replace(/[^a-z0-9]/gi, "");

  const first = values[0];
  const last = values[values.length - 1];
  const diff = last - first;
  const diffStr = (diff >= 0 ? "+" : "") + diff.toFixed(4);

  return (
    <div className="chart-wrap">
      <svg
        viewBox={"0 0 " + W + " " + H}
        preserveAspectRatio="none"
        style={{ width: "100%", height: H + "px", display: "block" }}
      >
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0.01" />
          </linearGradient>
        </defs>
        <polygon points={fillPts} fill={"url(#" + gid + ")"} />
        <polyline
          points={pts.join(" ")}
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <circle cx={lastX} cy={lastY} r="2.5" fill={color} />
      </svg>
      <div className="chart-labels">
        <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{first.toFixed(4)}</span>
        <span style={{ color: diff >= 0 ? "var(--accent-green)" : "var(--accent-red)", fontSize: "0.75rem", fontWeight: 600 }}>
          {diffStr}
        </span>
        <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{last.toFixed(4)}</span>
      </div>
    </div>
  );
}

function OfflineBanner(props) {
  const pct = ((5 - props.retryIn) / 5 * 100) + "%";
  return (
    <div className="offline-banner">
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
        <span className="offline-dot-pulse" />
        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#fca5a5" }}>
          API hors ligne — reconnexion dans {props.retryIn}s
        </span>
      </div>
      <div className="offline-bar">
        <div className="offline-bar-fill" style={{ width: pct }} />
      </div>
    </div>
  );
}

// ─── MAIN APP ───────────────────────────────────────────────────────────────
function App() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState(defaultForm);
  const [isOffline, setIsOffline] = useState(false);
  const [retryIn, setRetryIn] = useState(0);
  const [showResetModal, setShowResetModal] = useState(false);
  const [equityHistory, setEquityHistory] = useState([]);
  const [pnlHistory, setPnlHistory] = useState([]);
  const retryRef = useRef(null);

  function syncForm(s) {
    if (!s) return;
    setForm({
      symbol: s.symbol || "BTCUSDT",
      interval: s.interval || "1m",
      take_profit_usd: s.take_profit_usd || 1,
      stop_loss_usd: s.stop_loss_usd || -1,
      initial_balance: s.initial_balance || 8,
    });
  }

  function pushHistory(data) {
    if (!data || !data.wallet) return;
    const now = Date.now();
    const eq = parseFloat(data.wallet.equity);
    const pnl = parseFloat(data.wallet.daily_pnl);
    if (!isNaN(eq)) {
      setEquityHistory(function(p) { return p.concat([{ ts: now, value: eq }]).slice(-60); });
    }
    if (!isNaN(pnl)) {
      setPnlHistory(function(p) { return p.concat([{ ts: now, value: pnl }]).slice(-60); });
    }
  }

  function startCountdown() {
    let count = 5;
    setRetryIn(count);
    if (retryRef.current) clearInterval(retryRef.current);
    retryRef.current = setInterval(function() {
      count -= 1;
      setRetryIn(count);
      if (count <= 0) {
        clearInterval(retryRef.current);
        retryRef.current = null;
      }
    }, 1000);
  }

  // FIX 1 : useCallback pour stabiliser la reference de loadStatus
  // FIX 2 : catch sans variable (err etait defini mais non utilise)
  const loadStatus = useCallback(async function() {
    try {
      setLoading(true);
      const data = await getStatus();
      setStatus(data);
      setIsOffline(false);
      setError("");
      syncForm(data && data.settings);
      pushHistory(data);
    } catch {
      // err supprime car non utilise — on gere juste le state offline
      setIsOffline(true);
      startCountdown();
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // FIX 3 : loadStatus dans le tableau de dependances de useEffect
  useEffect(function() {
    loadStatus();
    const id = setInterval(loadStatus, 5000);
    return function() {
      clearInterval(id);
      if (retryRef.current) clearInterval(retryRef.current);
    };
  }, [loadStatus]);

  async function handleAction(actionFn, successText) {
    try {
      setActionLoading(true);
      setError("");
      setMessage("");
      const data = await actionFn();
      setStatus(data);
      syncForm(data && data.settings);
      pushHistory(data);
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
    const name = e.target.name;
    const value = e.target.value;
    setForm(function(p) { return Object.assign({}, p, { [name]: value }); });
  }

  const market   = status && status.market;
  const settings = status && status.settings;
  const wallet   = status && status.wallet;
  const signal   = status && status.last_signal;
  const trades   = (status && status.trades) || [];
  const logs     = (status && status.logs) || [];

  const pnlHL = wallet && wallet.daily_pnl > 0 ? "green" : wallet && wallet.daily_pnl < 0 ? "red" : null;
  const sigHL = signal && signal.signal === "BUY" ? "green" : signal && signal.signal === "SELL" ? "red" : null;

  const eqLast  = equityHistory.length >= 2 ? equityHistory[equityHistory.length - 1].value : null;
  const eqFirst = equityHistory.length >= 2 ? equityHistory[0].value : null;
  const eqColor = eqLast !== null && eqLast >= eqFirst ? "#00ff88" : "#ff3b6b";

  const pnlLast  = pnlHistory.length >= 2 ? pnlHistory[pnlHistory.length - 1].value : 0;
  const pnlColor = pnlLast >= 0 ? "#00ff88" : "#ff3b6b";

  const intervals = ["1m","3m","5m","15m","30m","1h","2h","4h","6h","8h","12h","1d"];

  return (
    <div className="page">

      {showResetModal && (
        <ConfirmModal
          message="Etes-vous sur de vouloir reinitialiser le bot ? Toutes les positions et l'historique seront perdus."
          onConfirm={function() {
            setShowResetModal(false);
            setEquityHistory([]);
            setPnlHistory([]);
            handleAction(resetBot, "Bot reinitialise");
          }}
          onCancel={function() { setShowResetModal(false); }}
        />
      )}

      {/* ── HEADER ── */}
      <header className="header">
        <div className="header-brand">
          <h1>
            <span style={{ fontStyle: "italic" }}>Nex</span>
            <span style={{ background: "var(--gradient-accent)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>Trade</span>
            <sup style={{ fontSize: "0.45em", color: "var(--accent-purple)", fontWeight: 400, marginLeft: "4px" }}>v1</sup>
          </h1>
          <p>Surveillance et Controle en temps reel</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          {isOffline && (
            <div className="status-offline">
              <span className="offline-dot-pulse" />
              API hors ligne
            </div>
          )}
          <div className={status && status.running ? "badge running" : "badge stopped"}>
            {status && status.running ? "Bot en marche" : "Bot arrete"}
          </div>
        </div>
      </header>

      {isOffline  && <OfflineBanner retryIn={retryIn} />}
      {error      && <div className="alert error">{error}</div>}
      {message    && <div className="alert success">{message}</div>}

      {/* ── ACTIONS ── */}
      <section className="actions">
        <button onClick={function() { handleAction(loadStatus, "Donnees actualisees"); }} disabled={actionLoading}>Refresh</button>
        <button onClick={function() { handleAction(startBot,   "Bot demarre");         }} disabled={actionLoading}>Start</button>
        <button onClick={function() { handleAction(stopBot,    "Bot arrete");          }} disabled={actionLoading}>Stop</button>
        <button onClick={function() { handleAction(tickBot,    "Tick execute");        }} disabled={actionLoading}>Tick</button>
        <button className="btn-danger" onClick={function() { setShowResetModal(true); }} disabled={actionLoading}>Reset</button>
      </section>

      {loading && !status ? (
        <div className="card loading-state">
          <span className="spinner" />
          Chargement...
        </div>
      ) : (
        <div>

          {/* ── CHARTS ── */}
          <section className="grid two">
            <div className="card">
              <h2>Equity en temps reel</h2>
              <MiniChart data={equityHistory} color={eqColor} />
              {wallet && (
                <div style={{ marginTop: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>Equity actuelle</span>
                  <span style={{ color: "var(--accent-cyan)", fontFamily: "monospace", fontWeight: 600 }}>{wallet.equity}</span>
                </div>
              )}
            </div>

            <div className="card">
              <h2>PnL Journalier</h2>
              <MiniChart data={pnlHistory} color={pnlColor} />
              {wallet && (
                <div style={{ marginTop: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>Daily PnL</span>
                  <span style={{ color: wallet.daily_pnl >= 0 ? "var(--accent-green)" : "var(--accent-red)", fontFamily: "monospace", fontWeight: 600 }}>
                    {wallet.daily_pnl}
                  </span>
                </div>
              )}
            </div>
          </section>

          {/* ── MARCHE + SIGNAL ── */}
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
                <InfoRow label="Signal" value={signal && signal.signal} highlight={sigHL} />
                <InfoRow label="Score"  value={signal && signal.score} />
                <InfoRow label="Strong" value={signal ? String(signal.strong) : "—"} />
                <InfoRow label="MA10"   value={signal && signal.ma10} />
                <InfoRow label="MA20"   value={signal && signal.ma20} />
              </div>
            </div>
          </section>

          {/* ── WALLET + PARAMS ── */}
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
                <InfoRow label="Position PnL"     value={wallet && wallet.position_pnl}    highlight={pnlHL} />
                <InfoRow label="Daily PnL"        value={wallet && wallet.daily_pnl}       highlight={pnlHL} />
              </div>
            </div>

            <div className="card">
              <h2>Parametres</h2>
              <form onSubmit={handleUpdateSettings} className="settings-form">
                <label>Symbol
                  <input name="symbol" value={form.symbol} onChange={handleInputChange} placeholder="BTCUSDT" />
                </label>
                <label>Interval
                  <select name="interval" value={form.interval} onChange={handleInputChange}>
                    {intervals.map(function(v) { return <option key={v} value={v}>{v}</option>; })}
                  </select>
                </label>
                <label>Take Profit USD
                  <input type="number" step="0.01" name="take_profit_usd" value={form.take_profit_usd} onChange={handleInputChange} />
                </label>
                <label>Stop Loss USD
                  <input type="number" step="0.01" name="stop_loss_usd" value={form.stop_loss_usd} onChange={handleInputChange} />
                </label>
                <label>Capital initial
                  <input type="number" step="0.01" name="initial_balance" value={form.initial_balance} onChange={handleInputChange} />
                </label>
                <button type="submit" disabled={actionLoading}>Sauvegarder les parametres</button>
              </form>

              {settings && (
                <div className="current-settings">
                  <h3>Parametres actifs</h3>
                  <div><strong>Symbol</strong>  <span>{settings.symbol}</span></div>
                  <div><strong>Interval</strong><span>{settings.interval}</span></div>
                  <div><strong>TP</strong>       <span>{settings.take_profit_usd}</span></div>
                  <div><strong>SL</strong>       <span>{settings.stop_loss_usd}</span></div>
                  <div><strong>Capital</strong> <span>{settings.initial_balance}</span></div>
                </div>
              )}
            </div>
          </section>

          {/* ── TRADES + LOGS ── */}
          <section className="grid two">
            <div className="card">
              <h2>Trades</h2>
              {trades.length === 0 ? (
                <p>Aucun trade pour le moment.</p>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr><th>ID</th><th>Side</th><th>Entry</th><th>Exit</th><th>Qty</th><th>PnL</th><th>Reason</th></tr>
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

      {/* ── FOOTER ── */}
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