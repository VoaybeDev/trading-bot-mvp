# NexTrade 🤖

Bot de trading automatisé avec **paper trading** et **trading réel Binance** (testnet + production), interface web temps réel et notifications Telegram.

**Stack :** FastAPI · SQLite · React · Vite · Docker · pytest · vitest

---

## Fonctionnalités

- Stratégie multi-signal : **SMA + RSI + MACD + Bollinger Bands**
- **Mode paper trading** (simulation) et **mode réel Binance** (testnet / production)
- Taille des ordres configurable en % du capital disponible
- Paper wallet simulé (capital initial configurable)
- Interface web temps réel avec graphiques equity/PnL
- **Dashboard santé** détaillé (DB, bot, wallet, marché)
- **Backtesting** sur données historiques Binance
- **Notifications Telegram** : BUY, SELL, TP, SL, erreurs, start/stop
- Authentification par clé API (`X-API-Key`)
- Retry automatique sur erreurs réseau Binance (3 tentatives)
- Arrêt automatique après 5 erreurs consécutives
- Purge automatique des logs/trades en base
- Suite de tests complète : **248 tests pytest + 49 tests vitest**

---

## Structure du projet

```
trading-bot-mvp/
├── app/
│   ├── main.py           # FastAPI — routes et endpoints
│   ├── bot.py            # Logique du bot (paper + réel, retry, arrêt auto)
│   ├── exchange.py       # Client Binance (ordres réels, HMAC, step size)
│   ├── strategy.py       # Stratégie multi-signal (SMA/RSI/MACD/BB)
│   ├── paper_wallet.py   # Wallet simulé (open/close long, PnL)
│   ├── market_data.py    # Récupération prix Binance
│   ├── backtest.py       # Moteur de backtesting historique
│   ├── db.py             # SQLite (trades, logs, wallet, purge)
│   ├── health.py         # Rapport de santé détaillé
│   ├── notifier.py       # Notifications Telegram
│   └── settings.py       # Paramètres configurables
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_backtest.py
│   ├── test_bot.py
│   ├── test_db.py
│   ├── test_exchange.py
│   ├── test_health.py
│   ├── test_notifier.py
│   ├── test_paper_wallet.py
│   └── test_strategy.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── HealthDashboard.jsx
│   │   ├── BacktestPanel.jsx
│   │   ├── api.js
│   │   └── tests/
│   │       ├── setup.js
│   │       ├── api.test.js
│   │       └── App.test.jsx
│   ├── vitest.config.js
│   └── package.json
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── pytest.ini
```

---

## Prérequis

- Python 3.12+
- Node.js 18+
- (Optionnel) Docker + Docker Compose

---

## Installation

### 1. Cloner le projet

```bash
git clone https://github.com/VoaybeDev/trading-bot-mvp.git
cd trading-bot-mvp
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditer `.env` :

```env
# Authentification backend
API_KEY=votre_cle_secrete

# Binance (laisser vide pour le paper trading)
BINANCE_BASE_URL=https://api.binance.com
BINANCE_API_KEY=
BINANCE_SECRET_KEY=

# Telegram (optionnel)
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
```

Créer `frontend/.env` :

```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=votre_cle_secrete
```

### 3. Backend

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Frontend

```bash
cd frontend
npm install
```

---

## Lancement

### Sans Docker

```bash
# Terminal 1 — Backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

- Backend  : http://localhost:8000
- Frontend : http://localhost:5173
- Docs API : http://localhost:8000/docs

### Avec Docker

```bash
docker-compose up --build
```

---

## API

Toutes les routes (sauf `GET /`) nécessitent le header :

```
X-API-Key: votre_cle_secrete
```

| Méthode | Route | Description |
|---|---|---|
| `GET`  | `/`                | Sanity check public |
| `GET`  | `/status`          | Snapshot complet |
| `GET`  | `/health`          | Rapport de santé détaillé |
| `GET`  | `/balance`         | Solde Binance (USDT + asset) |
| `POST` | `/start`           | Démarre le bot |
| `POST` | `/stop`            | Arrête le bot |
| `POST` | `/tick`            | Force un tick manuel |
| `POST` | `/reset`           | Réinitialise le bot et le wallet |
| `GET`  | `/trades`          | Liste des trades |
| `GET`  | `/logs`            | Liste des logs |
| `GET`  | `/settings`        | Paramètres actuels |
| `POST` | `/settings/update` | Met à jour les paramètres |
| `POST` | `/settings/reset`  | Remet les paramètres par défaut |
| `POST` | `/backtest`        | Lance un backtest historique |

---

## Modes de trading

### Paper trading (défaut)

Simulation sans argent réel. Le bot utilise un wallet virtuel.

```bash
curl -X POST http://localhost:8000/settings/update \
  -H "X-API-Key: votre_cle" \
  -H "Content-Type: application/json" \
  -d '{"trading_mode": "paper"}'
```

### Trading réel — Testnet Binance

Ordres réels sur le testnet Binance (fonds fictifs, 0 risque).

1. Créer un compte sur https://testnet.binance.vision
2. Générer une clé HMAC-SHA-256
3. Ajouter dans `.env` :

```env
BINANCE_API_KEY=votre_cle_testnet
BINANCE_SECRET_KEY=votre_secret_testnet
```

4. Activer le mode réel testnet :

```bash
curl -X POST http://localhost:8000/settings/update \
  -H "X-API-Key: votre_cle" \
  -H "Content-Type: application/json" \
  -d '{"trading_mode": "real", "use_testnet": true, "order_size_pct": 50}'
```

### Trading réel — Production Binance

⚠️ **Utilise de vrais fonds. Tester d'abord sur le testnet.**

```bash
curl -X POST http://localhost:8000/settings/update \
  -H "X-API-Key: votre_cle" \
  -H "Content-Type: application/json" \
  -d '{"trading_mode": "real", "use_testnet": false, "order_size_pct": 10}'
```

---

## Paramètres configurables

| Paramètre | Défaut | Description |
|---|---|---|
| `symbol` | `BTCUSDT` | Paire de trading Binance |
| `interval` | `1m` | Intervalle des bougies |
| `take_profit_usd` | `1.0` | Gain cible en USD |
| `stop_loss_usd` | `-1.0` | Perte maximale en USD |
| `initial_balance` | `8.0` | Capital initial du wallet simulé |
| `trading_mode` | `paper` | `paper` ou `real` |
| `order_size_pct` | `100.0` | % du capital engagé par ordre (1–100) |
| `use_testnet` | `true` | `true` = testnet · `false` = production |

---

## Stratégie multi-signal

Système de votes pondérés (6 points max) :

| Indicateur | Poids | Signal BUY | Signal SELL |
|---|---|---|---|
| SMA 10/20 | 1 | MA10 > MA20 | MA10 < MA20 |
| RSI | 2 | RSI < 30 (survente) | RSI > 70 (surachat) |
| MACD | 2 | Histogramme > 0 | Histogramme < 0 |
| Bollinger Bands | 1 | Prix < bande basse | Prix > bande haute |

**Seuil d'entrée :** score ≥ 4/6 → signal "strong" → ordre exécuté.

---

## Notifications Telegram

| Événement | Description |
|---|---|
| 🟢 Bot démarré | Symbol + interval |
| 🔴 Bot arrêté | Raison (manuel / auto) |
| 📈 BUY exécuté | Prix, quantité, score |
| 🎯 Take Profit | Prix de sortie, PnL |
| 🛑 Stop Loss | Prix de sortie, PnL |
| ⚠️ Erreur réseau | Message, nb erreurs consécutives |
| 🚨 Arrêt automatique | Trop d'erreurs consécutives |

**Configuration :**

1. Créer un bot via **@BotFather** → `/newbot` → copier le token
2. Envoyer un message au bot puis ouvrir :
   `https://api.telegram.org/bot<TOKEN>/getUpdates` → copier le `chat.id`
3. Ajouter dans `.env` :

```env
TELEGRAM_TOKEN=votre_token
TELEGRAM_CHAT_ID=votre_chat_id
```

---

## Backtesting

```bash
curl -X POST http://localhost:8000/backtest \
  -H "X-API-Key: votre_cle" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start": "2026-03-01T00:00",
    "end": "2026-03-10T00:00",
    "initial_balance": 100.0,
    "take_profit_usd": 5.0,
    "stop_loss_usd": -3.0
  }'
```

---

## Tests

### Backend (pytest)

```bash
pytest
pytest --cov=app --cov-report=html
```

**Résultat attendu : 248/248 tests ✅**

```
tests/test_api.py            22 tests  — Routes FastAPI, auth
tests/test_backtest.py       29 tests  — Moteur de backtesting
tests/test_bot.py            28 tests  — Logique bot, paper + réel, retry
tests/test_db.py             14 tests  — SQLite, purge, stats
tests/test_exchange.py       31 tests  — Client Binance, ordres, HMAC
tests/test_health.py         28 tests  — Endpoint /health
tests/test_notifier.py       28 tests  — Notifications Telegram
tests/test_paper_wallet.py   28 tests  — Wallet simulé
tests/test_strategy.py       50 tests  — SMA, EMA, RSI, MACD, Bollinger
```

### Frontend (vitest)

```bash
cd frontend && npm test
```

**Résultat attendu : 49/49 tests ✅**

---

## Variables d'environnement

| Variable | Exemple | Description |
|---|---|---|
| `API_KEY` | `my-secret-key` | Clé d'authentification backend |
| `BINANCE_BASE_URL` | `https://api.binance.com` | URL de l'API Binance |
| `BINANCE_API_KEY` | `abc123...` | Clé API Binance |
| `BINANCE_SECRET_KEY` | `xyz789...` | Clé secrète Binance |
| `TELEGRAM_TOKEN` | `123456:ABC...` | Token bot Telegram |
| `TELEGRAM_CHAT_ID` | `123456789` | ID du chat Telegram |
| `VITE_API_URL` | `http://localhost:8000` | URL du backend (frontend) |
| `VITE_API_KEY` | `my-secret-key` | Clé API côté frontend |

> ⚠️ Ne jamais committer `.env` ou `frontend/.env` — ils sont dans `.gitignore`.

---

## Contribuer

1. Fork le projet
2. Créer une branche : `git checkout -b feature/ma-feature`
3. Committer : `git commit -m "feat: ma feature"`
4. Pousser : `git push origin feature/ma-feature`
5. Ouvrir une Pull Request

---

## Auteur

**VoaybeDev** — [github.com/VoaybeDev](https://github.com/VoaybeDev)

---

*NexTrade v2 — Paper trading + Trading réel Binance (testnet & production)*