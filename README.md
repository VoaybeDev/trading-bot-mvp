# NexTrade 🤖

Bot de trading automatisé en **paper trading** (simulation sans argent réel), avec interface web en temps réel.

**Stack :** FastAPI · SQLite · React · Vite · Docker · pytest · vitest

---

## Fonctionnalités

- Stratégie multi-signal : **SMA + RSI + MACD + Bollinger Bands**
- Paper wallet simulé (capital initial configurable)
- Interface web temps réel avec graphiques equity/PnL
- Endpoint `/health` détaillé (DB, bot, wallet, marché)
- Authentification par clé API (`X-API-Key`)
- Retry automatique sur erreurs réseau Binance
- Purge automatique des logs/trades en base
- Suite de tests complète : **162 tests pytest + 47 tests vitest**

---

## Structure du projet

```
trading-bot-mvp/
├── app/
│   ├── main.py           # FastAPI — routes et endpoints
│   ├── bot.py            # Logique du bot (tick, retry, arrêt auto)
│   ├── strategy.py       # Stratégie multi-signal (SMA/RSI/MACD/BB)
│   ├── paper_wallet.py   # Wallet simulé (open/close long, PnL)
│   ├── market_data.py    # Récupération prix Binance
│   ├── db.py             # SQLite (trades, logs, wallet, purge)
│   ├── health.py         # Rapport de santé détaillé
│   └── settings.py       # Paramètres configurables
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_bot.py
│   ├── test_db.py
│   ├── test_paper_wallet.py
│   ├── test_strategy.py
│   └── test_health.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # Interface principale
│   │   ├── api.js         # Appels HTTP vers le backend
│   │   ├── styles.css
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
# Backend
API_KEY=votre_cle_secrete
BINANCE_BASE_URL=https://api.binance.com

# Frontend
VITE_API_URL=http://localhost:8000
VITE_API_KEY=votre_cle_secrete
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

- Backend : http://localhost:8000
- Frontend : http://localhost:5173
- Docs API : http://localhost:8000/docs

### Avec Docker

```bash
docker-compose up --build
```

- Frontend : http://localhost:5173
- Backend  : http://localhost:8000

---

## API

Toutes les routes (sauf `GET /`) nécessitent le header :

```
X-API-Key: votre_cle_secrete
```

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/` | Route publique — sanity check |
| `GET` | `/status` | Snapshot complet (bot, marché, wallet, logs, trades) |
| `GET` | `/health` | Rapport de santé détaillé |
| `POST` | `/start` | Démarre le bot |
| `POST` | `/stop` | Arrête le bot |
| `POST` | `/tick` | Force un tick manuel |
| `POST` | `/reset` | Réinitialise le bot et le wallet |
| `GET` | `/trades` | Liste des trades |
| `GET` | `/logs` | Liste des logs |
| `GET` | `/settings` | Paramètres actuels |
| `POST` | `/settings/update` | Met à jour les paramètres |
| `POST` | `/settings/reset` | Remet les paramètres par défaut |

### Exemple — lancer le bot

```bash
curl -X POST http://localhost:8000/start \
  -H "X-API-Key: votre_cle_secrete"
```

### Exemple — mettre à jour les paramètres

```bash
curl -X POST http://localhost:8000/settings/update \
  -H "X-API-Key: votre_cle_secrete" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "ETHUSDT", "take_profit_usd": 2.0, "stop_loss_usd": -1.5}'
```

---

## Stratégie multi-signal

La stratégie combine 4 indicateurs avec un système de votes pondérés (6 points max) :

| Indicateur | Poids | Signal BUY | Signal SELL |
|---|---|---|---|
| SMA 10/20 | 1 | MA10 > MA20 | MA10 < MA20 |
| RSI | 2 | RSI < 30 (survente) | RSI > 70 (surachat) |
| MACD | 2 | Histogramme > 0 | Histogramme < 0 |
| Bollinger Bands | 1 | Prix < bande basse | Prix > bande haute |

**Seuil d'entrée :** score ≥ 4/6 (signal "strong") → ordre exécuté.

Le score est normalisé en pourcentage dans la réponse API (`score: 83` = 83%).

---

## Paramètres configurables

| Paramètre | Défaut | Description |
|---|---|---|
| `symbol` | `BTCUSDT` | Paire de trading Binance |
| `interval` | `1m` | Intervalle des bougies |
| `take_profit_usd` | `1.0` | Gain cible en USD |
| `stop_loss_usd` | `-1.0` | Perte maximale en USD |
| `initial_balance` | `8.0` | Capital initial du wallet simulé |

---

## Tests

### Backend (pytest)

```bash
# Depuis la racine du projet
source .venv/bin/activate
pytest

# Avec couverture
pytest --cov=app --cov-report=html
```

**Résultat attendu : 162/162 tests ✅**

```
tests/test_api.py          22 tests  — Routes FastAPI, auth
tests/test_bot.py          20 tests  — Logique bot, retry, tick
tests/test_db.py           14 tests  — SQLite, purge, stats
tests/test_paper_wallet.py 28 tests  — Wallet, open/close, PnL
tests/test_strategy.py     50 tests  — SMA, EMA, RSI, MACD, Bollinger
tests/test_health.py       28 tests  — Endpoint /health
```

### Frontend (vitest)

```bash
cd frontend
npm test

# Mode watch
npm run test:watch

# Avec couverture
npm run test:coverage
```

**Résultat attendu : 47/47 tests ✅**

```
api.test.js    23 tests  — Fonctions API (fetch, erreurs, headers)
App.test.jsx   24 tests  — Composant React (rendu, boutons, modal, signal)
```

### Total : 209 tests

---

## Santé du bot — `/health`

```json
{
  "status": "ok",
  "timestamp": "2026-03-11T11:00:00",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "ok",
      "latency_ms": 0.42,
      "trades_count": 5,
      "logs_count": 128,
      "size_kb": 64
    },
    "bot": {
      "status": "running",
      "consecutive_errors": 0,
      "error_rate": 0.0,
      "current_price": 50234.5,
      "symbol": "BTCUSDT"
    },
    "wallet": {
      "equity": 8.73,
      "daily_pnl_usd": 0.73,
      "daily_pnl_pct": 9.1,
      "has_position": false
    },
    "market": {
      "signal": "BUY",
      "score": 83,
      "current_price": 50234.5
    }
  }
}
```

**Statuts possibles :**
- `ok` — tout fonctionne normalement
- `degraded` — 3+ erreurs consécutives réseau
- `error` — base de données inaccessible

---

## Variables d'environnement

| Variable | Exemple | Description |
|---|---|---|
| `API_KEY` | `my-secret-key` | Clé d'authentification backend |
| `BINANCE_BASE_URL` | `https://api.binance.com` | URL de l'API Binance |
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

*NexTrade v1 — Paper trading uniquement. Aucune transaction réelle.*