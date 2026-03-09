"""
test_strategy.py — Tests unitaires pour app/strategy.py
Placez ce fichier dans : trading-bot-mvp/tests/test_strategy.py
"""
import pytest
from app.strategy import analyze, sma


# ─── TESTS SMA ────────────────────────────────────────────────────────────────

class TestSma:
    def test_retourne_none_si_pas_assez_de_donnees(self):
        assert sma([1, 2, 3], period=10) is None

    def test_retourne_none_si_liste_vide(self):
        assert sma([], period=5) is None

    def test_calcul_correct_periode_3(self):
        result = sma([10, 20, 30], period=3)
        assert result == pytest.approx(20.0)

    def test_utilise_seulement_les_n_derniers(self):
        # Seuls les 2 derniers comptent pour period=2
        result = sma([1, 100, 200], period=2)
        assert result == pytest.approx(150.0)

    def test_periode_egale_a_la_taille(self):
        result = sma([4, 6], period=2)
        assert result == pytest.approx(5.0)

    def test_valeurs_identiques(self):
        result = sma([10, 10, 10, 10, 10], period=5)
        assert result == pytest.approx(10.0)


# ─── TESTS ANALYZE ────────────────────────────────────────────────────────────

class TestAnalyze:

    def test_hold_si_pas_assez_de_prix(self):
        result = analyze([100, 200])
        assert result["signal"] == "HOLD"
        assert result["score"] == 0
        assert result["strong"] is False
        assert result["ma10"] is None
        assert result["ma20"] is None

    def test_hold_si_liste_vide(self):
        result = analyze([])
        assert result["signal"] == "HOLD"

    def test_signal_buy_quand_ma10_superieur_ma20(self):
        # Prix croissants : MA10 récente > MA20 plus ancienne
        prices = list(range(1, 31))  # [1, 2, ..., 30]
        result = analyze(prices)
        assert result["signal"] == "BUY"

    def test_signal_sell_quand_ma10_inferieur_ma20(self):
        # Prix décroissants : MA10 récente < MA20 plus ancienne
        prices = list(range(30, 0, -1))  # [30, 29, ..., 1]
        result = analyze(prices)
        assert result["signal"] == "SELL"

    def test_score_minimum_50_quand_signal_non_hold(self):
        prices = list(range(1, 31))
        result = analyze(prices)
        assert result["score"] >= 50

    def test_strong_true_quand_score_superieur_70(self):
        # Tendance haussière forte avec momentum et distance suffisante
        base = 100.0
        prices = [base + i * 5 for i in range(30)]
        result = analyze(prices)
        if result["score"] >= 70:
            assert result["strong"] is True
        else:
            assert result["strong"] is False

    def test_strong_false_quand_score_inferieur_70(self):
        # Tous les prix identiques → signal HOLD, score 0
        prices = [100.0] * 30
        result = analyze(prices)
        assert result["strong"] is False
        assert result["score"] == 0

    def test_ma10_et_ma20_sont_arrondis(self):
        prices = [i * 1.123456789 for i in range(1, 31)]
        result = analyze(prices)
        if result["ma10"] is not None:
            # Vérifie que les valeurs sont arrondies à 4 décimales
            assert result["ma10"] == round(result["ma10"], 4)
            assert result["ma20"] == round(result["ma20"], 4)

    def test_retourne_toutes_les_cles_attendues(self):
        prices = list(range(1, 31))
        result = analyze(prices)
        assert set(result.keys()) == {"signal", "score", "strong", "ma10", "ma20"}

    def test_score_100_tendance_forte(self):
        # Prix fortement croissants → tous les bonus actifs
        prices = [100.0 + i * 10 for i in range(30)]
        result = analyze(prices)
        assert result["signal"] == "BUY"
        assert result["score"] == 100
        assert result["strong"] is True