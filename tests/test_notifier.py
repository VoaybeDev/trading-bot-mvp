"""
test_notifier.py — Tests du module de notifications Telegram.
Placez ce fichier dans : trading-bot-mvp/tests/test_notifier.py
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.notifier import (
    send_message,
    notify_bot_started,
    notify_bot_stopped,
    notify_buy,
    notify_sell,
    notify_take_profit,
    notify_stop_loss,
    notify_error,
    notify_bot_auto_stopped,
    _is_configured,
)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def make_ok_response():
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    return resp


def make_error_response():
    resp = MagicMock()
    resp.raise_for_status = MagicMock(side_effect=Exception("HTTP 400"))
    return resp


def mock_httpx_ok():
    """Context manager mock qui retourne une réponse 200."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=make_ok_response())
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=False)
    return patch("app.notifier.httpx.AsyncClient", return_value=mock_client)


def mock_httpx_error():
    """Context manager mock qui lève une exception réseau."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__  = AsyncMock(return_value=False)
    return patch("app.notifier.httpx.AsyncClient", return_value=mock_client)


# ─── _is_configured ───────────────────────────────────────────────────────────

class TestIsConfigured:

    def test_false_si_token_vide(self):
        with patch("app.notifier.TELEGRAM_TOKEN", ""), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            assert _is_configured() is False

    def test_false_si_chat_id_vide(self):
        with patch("app.notifier.TELEGRAM_TOKEN", "abc:xyz"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", ""):
            assert _is_configured() is False

    def test_true_si_les_deux_presents(self):
        with patch("app.notifier.TELEGRAM_TOKEN", "abc:xyz"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123456"):
            assert _is_configured() is True


# ─── send_message ─────────────────────────────────────────────────────────────

class TestSendMessage:

    @pytest.mark.asyncio
    async def test_retourne_false_si_non_configure(self):
        result = await send_message("test", token="", chat_id="")
        assert result is False

    @pytest.mark.asyncio
    async def test_retourne_true_si_succes(self):
        with mock_httpx_ok():
            result = await send_message("test", token="tok", chat_id="123")
        assert result is True

    @pytest.mark.asyncio
    async def test_retourne_false_si_erreur_reseau(self):
        with mock_httpx_error():
            result = await send_message("test", token="tok", chat_id="123")
        assert result is False

    @pytest.mark.asyncio
    async def test_ne_leve_jamais_exception(self):
        """send_message ne doit jamais propager une exception."""
        with mock_httpx_error():
            try:
                await send_message("test", token="tok", chat_id="123")
            except Exception:
                pytest.fail("send_message a levé une exception")

    @pytest.mark.asyncio
    async def test_appelle_bonne_url(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client):
            await send_message("test", token="mytoken", chat_id="42")

        call_url = mock_client.post.call_args[0][0]
        assert "mytoken" in call_url
        assert "sendMessage" in call_url

    @pytest.mark.asyncio
    async def test_envoie_parse_mode_html(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client):
            await send_message("<b>test</b>", token="tok", chat_id="123")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_envoie_le_bon_texte(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client):
            await send_message("bonjour monde", token="tok", chat_id="123")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["text"] == "bonjour monde"

    @pytest.mark.asyncio
    async def test_utilise_token_env_si_pas_fourni(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.TELEGRAM_TOKEN", "env_token"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "env_chat"), \
             patch("app.notifier.httpx.AsyncClient", return_value=mock_client):
            result = await send_message("test")

        assert result is True
        call_url = mock_client.post.call_args[0][0]
        assert "env_token" in call_url


# ─── notify_bot_started ───────────────────────────────────────────────────────

class TestNotifyBotStarted:

    @pytest.mark.asyncio
    async def test_retourne_true_si_succes(self):
        with mock_httpx_ok(), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            result = await notify_bot_started("BTCUSDT", "1m")
        assert result is True

    @pytest.mark.asyncio
    async def test_message_contient_symbol(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            await notify_bot_started("ETHUSDT", "5m")

        text = mock_client.post.call_args[1]["json"]["text"]
        assert "ETHUSDT" in text
        assert "5m" in text


# ─── notify_bot_stopped ───────────────────────────────────────────────────────

class TestNotifyBotStopped:

    @pytest.mark.asyncio
    async def test_retourne_true_si_succes(self):
        with mock_httpx_ok(), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            result = await notify_bot_stopped("Manuel")
        assert result is True

    @pytest.mark.asyncio
    async def test_message_contient_raison(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            await notify_bot_stopped("Erreur réseau")

        text = mock_client.post.call_args[1]["json"]["text"]
        assert "Erreur réseau" in text


# ─── notify_buy ───────────────────────────────────────────────────────────────

class TestNotifyBuy:

    @pytest.mark.asyncio
    async def test_retourne_true_si_succes(self):
        with mock_httpx_ok(), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            result = await notify_buy("BTCUSDT", 50000.0, 0.00016, 83)
        assert result is True

    @pytest.mark.asyncio
    async def test_message_contient_prix_et_score(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            await notify_buy("BTCUSDT", 50000.0, 0.00016, 83)

        text = mock_client.post.call_args[1]["json"]["text"]
        assert "50000" in text
        assert "83" in text
        assert "BTCUSDT" in text


# ─── notify_sell ──────────────────────────────────────────────────────────────

class TestNotifySell:

    @pytest.mark.asyncio
    async def test_retourne_true_si_succes(self):
        with mock_httpx_ok(), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            result = await notify_sell("BTCUSDT", 51000.0, 0.5, "SELL")
        assert result is True

    @pytest.mark.asyncio
    async def test_message_positif_contient_plus(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            await notify_sell("BTCUSDT", 51000.0, 0.5, "SELL")

        text = mock_client.post.call_args[1]["json"]["text"]
        assert "+" in text

    @pytest.mark.asyncio
    async def test_message_negatif_sans_plus(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            await notify_sell("BTCUSDT", 49000.0, -0.5, "SL")

        text = mock_client.post.call_args[1]["json"]["text"]
        assert "-0.5" in text


# ─── notify_take_profit ───────────────────────────────────────────────────────

class TestNotifyTakeProfit:

    @pytest.mark.asyncio
    async def test_retourne_true_si_succes(self):
        with mock_httpx_ok(), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            result = await notify_take_profit("BTCUSDT", 51000.0, 1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_message_contient_tp(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            await notify_take_profit("BTCUSDT", 51000.0, 1.0)

        text = mock_client.post.call_args[1]["json"]["text"]
        assert "Take Profit" in text
        assert "51000" in text


# ─── notify_stop_loss ─────────────────────────────────────────────────────────

class TestNotifyStopLoss:

    @pytest.mark.asyncio
    async def test_retourne_true_si_succes(self):
        with mock_httpx_ok(), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            result = await notify_stop_loss("BTCUSDT", 49000.0, -1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_message_contient_sl(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            await notify_stop_loss("BTCUSDT", 49000.0, -1.0)

        text = mock_client.post.call_args[1]["json"]["text"]
        assert "Stop Loss" in text
        assert "49000" in text


# ─── notify_error ─────────────────────────────────────────────────────────────

class TestNotifyError:

    @pytest.mark.asyncio
    async def test_retourne_true_si_succes(self):
        with mock_httpx_ok(), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            result = await notify_error("Connection timeout", 3)
        assert result is True

    @pytest.mark.asyncio
    async def test_message_contient_erreur_et_compteur(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            await notify_error("Timeout", 5)

        text = mock_client.post.call_args[1]["json"]["text"]
        assert "Timeout" in text
        assert "5" in text


# ─── notify_bot_auto_stopped ──────────────────────────────────────────────────

class TestNotifyBotAutoStopped:

    @pytest.mark.asyncio
    async def test_retourne_true_si_succes(self):
        with mock_httpx_ok(), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            result = await notify_bot_auto_stopped(10)
        assert result is True

    @pytest.mark.asyncio
    async def test_message_contient_nb_erreurs(self):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=make_ok_response())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__  = AsyncMock(return_value=False)

        with patch("app.notifier.httpx.AsyncClient", return_value=mock_client), \
             patch("app.notifier.TELEGRAM_TOKEN", "tok"), \
             patch("app.notifier.TELEGRAM_CHAT_ID", "123"):
            await notify_bot_auto_stopped(10)

        text = mock_client.post.call_args[1]["json"]["text"]
        assert "10" in text