import { useEffect, useState } from "react";
import {
  getStatus,
  startBot,
  stopBot,
  tickBot,
  resetBot,
  updateSettings,
} from "./api";

const defaultForm = {
  symbol: "BTCUSDT",
  interval: "1m",
  take_profit_usd: 1,
  stop_loss_usd: -1,
  initial_balance: 8,
};

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

      if (data?.settings) {
        setForm({
          symbol: data.settings.symbol ?? "BTCUSDT",
          interval: data.settings.interval ?? "1m",
          take_profit_usd: data.settings.take_profit_usd ?? 1,
          stop_loss_usd: data.settings.stop_loss_usd ?? -1,
          initial_balance: data.settings.initial_balance ?? 8,
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
    const intervalId = setInterval(loadStatus, 5000);
    return () => clearInterval(intervalId);
  }, []);

  async function handleAction(actionFn, successText = "") {
    try {
      setActionLoading(true);
      setError("");
      setMessage("");
      const data = await actionFn();
      setStatus(data);
      if (data?.settings) {
        setForm({
          symbol: data.settings.symbol ?? "BTCUSDT",
          interval: data.settings.interval ?? "1m",
          take_profit_usd: data.settings.take_profit_usd ?? 1,
          stop_loss_usd: data.settings.stop_loss_usd ?? -1,
          initial_balance: data.settings.initial_balance ?? 8,
        });
      }
      if (successText) {
        setMessage(successText);
      }
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
      setMessage(result.message || "Paramètres mis à jour");
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  function handleInputChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  }

  const market = status?.market;
  const settings = status?.settings;
  const wallet = status?.wallet;
  const signal = status?.last_signal;
  const trades = status?.trades || [];
  const logs = status?.logs || [];

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>Trading Bot Dashboard</h1>
          <p>Frontend React du bot de trading</p>
        </div>

        <div className={`badge ${status?.running ? "running" : "stopped"}`}>
          {status?.running ? "BOT EN MARCHE" : "BOT ARRÊTÉ"}
        </div>
      </header>

      {error && <div className="alert error">{error}</div>}
      {message && <div className="alert success">{message}</div>}

      <section className="actions">
        <button onClick={() => handleAction(loadStatus, "Données actualisées")} disabled={actionLoading}>
          Refresh
        </button>
        <button onClick={() => handleAction(startBot, "Bot démarré")} disabled={actionLoading}>
          Start
        </button>
        <button onClick={() => handleAction(stopBot, "Bot arrêté")} disabled={actionLoading}>
          Stop
        </button>
        <button onClick={() => handleAction(tickBot, "Tick exécuté")} disabled={actionLoading}>
          Tick
        </button>
        <button onClick={() => handleAction(resetBot, "Bot réinitialisé")} disabled={actionLoading}>
          Reset
        </button>
      </section>

      {loading && !status ? (
        <div className="card">Chargement...</div>
      ) : (
        <>
          <section className="grid two">
            <div className="card">
              <h2>Marché</h2>
              <div className="info-list">
                <div><strong>Symbol:</strong> {market?.symbol}</div>
                <div><strong>Interval:</strong> {market?.interval}</div>
                <div><strong>Prix actuel:</strong> {market?.current_price}</div>
              </div>
            </div>

            <div className="card">
              <h2>Signal</h2>
              <div className="info-list">
                <div><strong>Signal:</strong> {signal?.signal}</div>
                <div><strong>Score:</strong> {signal?.score}</div>
                <div><strong>Strong:</strong> {String(signal?.strong)}</div>
                <div><strong>MA10:</strong> {signal?.ma10}</div>
                <div><strong>MA20:</strong> {signal?.ma20}</div>
              </div>
            </div>
          </section>

          <section className="grid two">
            <div className="card">
              <h2>Wallet</h2>
              <div className="info-list">
                <div><strong>Capital initial:</strong> {wallet?.initial_balance}</div>
                <div><strong>Cash:</strong> {wallet?.cash}</div>
                <div><strong>Position ouverte:</strong> {String(wallet?.has_position)}</div>
                <div><strong>Entry price:</strong> {wallet?.entry_price ?? "-"}</div>
                <div><strong>Position qty:</strong> {wallet?.position_qty}</div>
                <div><strong>Equity:</strong> {wallet?.equity}</div>
                <div><strong>Position PnL:</strong> {wallet?.position_pnl}</div>
                <div><strong>Daily PnL:</strong> {wallet?.daily_pnl}</div>
              </div>
            </div>

            <div className="card">
              <h2>Paramètres</h2>
              <form onSubmit={handleUpdateSettings} className="settings-form">
                <label>
                  Symbol
                  <input
                    name="symbol"
                    value={form.symbol}
                    onChange={handleInputChange}
                    placeholder="BTCUSDT"
                  />
                </label>

                <label>
                  Interval
                  <select
                    name="interval"
                    value={form.interval}
                    onChange={handleInputChange}
                  >
                    <option value="1m">1m</option>
                    <option value="3m">3m</option>
                    <option value="5m">5m</option>
                    <option value="15m">15m</option>
                    <option value="30m">30m</option>
                    <option value="1h">1h</option>
                    <option value="2h">2h</option>
                    <option value="4h">4h</option>
                    <option value="6h">6h</option>
                    <option value="8h">8h</option>
                    <option value="12h">12h</option>
                    <option value="1d">1d</option>
                  </select>
                </label>

                <label>
                  Take Profit USD
                  <input
                    type="number"
                    step="0.01"
                    name="take_profit_usd"
                    value={form.take_profit_usd}
                    onChange={handleInputChange}
                  />
                </label>

                <label>
                  Stop Loss USD
                  <input
                    type="number"
                    step="0.01"
                    name="stop_loss_usd"
                    value={form.stop_loss_usd}
                    onChange={handleInputChange}
                  />
                </label>

                <label>
                  Capital initial
                  <input
                    type="number"
                    step="0.01"
                    name="initial_balance"
                    value={form.initial_balance}
                    onChange={handleInputChange}
                  />
                </label>

                <button type="submit" disabled={actionLoading}>
                  Sauvegarder les paramètres
                </button>
              </form>

              {settings && (
                <div className="current-settings">
                  <h3>Paramètres actuels</h3>
                  <div><strong>Symbol:</strong> {settings.symbol}</div>
                  <div><strong>Interval:</strong> {settings.interval}</div>
                  <div><strong>TP:</strong> {settings.take_profit_usd}</div>
                  <div><strong>SL:</strong> {settings.stop_loss_usd}</div>
                  <div><strong>Capital:</strong> {settings.initial_balance}</div>
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
                      {trades.map((trade) => (
                        <tr key={trade.id}>
                          <td>{trade.id}</td>
                          <td>{trade.side}</td>
                          <td>{trade.entry_price}</td>
                          <td>{trade.exit_price}</td>
                          <td>{trade.quantity}</td>
                          <td>{trade.pnl}</td>
                          <td>{trade.reason}</td>
                        </tr>
                      ))}
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
                  {logs.map((log) => (
                    <div key={log.id} className="log-item">
                      <div className="log-date">{log.created_at}</div>
                      <div className="log-message">{log.message}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export default App;