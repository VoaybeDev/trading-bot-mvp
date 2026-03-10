"""
test_strategy.py — Tests unitaires pour app/strategy.py (multi-signal)
Placez ce fichier dans : trading-bot-mvp/tests/test_strategy.py
"""
import math
import pytest
from app.strategy import analyze, sma, ema, rsi, macd, bollinger_bands


# ─── FIXTURES ────────────────────────────────────────────────────────────────

@pytest.fixture
def prices_40():
    """40 prix oscillants avec légère tendance haussière (série réaliste)."""
    import random
    random.seed(42)
    prices, p = [], 100.0
    for _ in range(40):
        p += random.uniform(-1.0, 1.5)
        prices.append(round(p, 2))
    return prices


@pytest.fixture
def prices_flat():
    """30 prix plats — aucun signal."""
    return [100.0] * 30


# ─── TESTS SMA ───────────────────────────────────────────────────────────────

class TestSma:

    def test_retourne_none_si_pas_assez_de_donnees(self):
        assert sma([1, 2, 3], period=10) is None

    def test_retourne_none_si_liste_vide(self):
        assert sma([], period=5) is None

    def test_calcul_correct_periode_3(self):
        assert sma([10, 20, 30], period=3) == pytest.approx(20.0)

    def test_utilise_seulement_les_n_derniers(self):
        assert sma([1, 100, 200], period=2) == pytest.approx(150.0)

    def test_periode_egale_a_la_taille(self):
        assert sma([4, 6], period=2) == pytest.approx(5.0)

    def test_valeurs_identiques(self):
        assert sma([10] * 5, period=5) == pytest.approx(10.0)


# ─── TESTS EMA ───────────────────────────────────────────────────────────────

class TestEma:

    def test_retourne_none_si_pas_assez_de_donnees(self):
        assert ema([1, 2], period=5) is None

    def test_retourne_none_si_liste_vide(self):
        assert ema([], period=3) is None

    def test_ema_egale_sma_si_une_seule_valeur_apres_init(self):
        """Avec exactement `period` valeurs, l'EMA = la moyenne."""
        prices = [10.0, 20.0, 30.0]
        result = ema(prices, period=3)
        assert result == pytest.approx(20.0, rel=1e-2)

    def test_ema_pondere_les_valeurs_recentes(self):
        """L'EMA doit être plus proche de la dernière valeur que la SMA."""
        prices = [100.0] * 10 + [200.0]
        e = ema(prices, period=5)
        s = sma(prices, period=5)
        assert e > s  # EMA réagit plus vite à la hausse récente

    def test_valeurs_identiques(self):
        result = ema([50.0] * 10, period=5)
        assert result == pytest.approx(50.0)


# ─── TESTS RSI ───────────────────────────────────────────────────────────────

class TestRsi:

    def test_retourne_none_si_pas_assez_de_donnees(self):
        assert rsi([1, 2, 3], period=14) is None

    def test_retourne_none_si_liste_vide(self):
        assert rsi([], period=14) is None

    def test_rsi_100_si_que_des_gains(self):
        """Que des hausses → pas de pertes → RSI = 100."""
        prices = [100.0 + i for i in range(20)]
        assert rsi(prices, period=14) == pytest.approx(100.0)

    def test_rsi_0_si_que_des_pertes(self):
        """Que des baisses → pas de gains → RSI ≈ 0."""
        prices = [100.0 - i for i in range(20)]
        result = rsi(prices, period=14)
        assert result == pytest.approx(0.0, abs=1.0)

    def test_rsi_entre_0_et_100(self):
        """Le RSI est toujours dans [0, 100]."""
        prices = [100, 102, 98, 105, 95, 108, 93, 110, 90, 112,
                  88, 115, 85, 118, 82, 120, 79, 122]
        result = rsi(prices, period=14)
        assert result is not None
        assert 0 <= result <= 100

    def test_rsi_calcul_avec_gains_et_pertes_equilibres(self):
        """Alternance gain=2, perte=1 → RSI ≈ 66.7."""
        # 15 prix: gain de 2 puis perte de 1 en alternance
        prices = [100.0]
        for i in range(14):
            if i % 2 == 0:
                prices.append(prices[-1] + 2)
            else:
                prices.append(prices[-1] - 1)
        result = rsi(prices, period=14)
        assert result is not None
        assert 60 < result < 75  # autour de 66.7

    def test_rsi_arrondi_a_2_decimales(self):
        prices = [100.0 + i * 0.33 for i in range(20)]
        result = rsi(prices, period=14)
        if result is not None:
            assert result == round(result, 2)


# ─── TESTS MACD ──────────────────────────────────────────────────────────────

class TestMacd:

    def test_retourne_none_si_pas_assez_de_donnees(self):
        assert macd([1.0] * 10) is None

    def test_retourne_none_si_liste_vide(self):
        assert macd([]) is None

    def test_retourne_les_bonnes_cles(self):
        prices = [100.0 + i * 0.5 for i in range(40)]
        result = macd(prices)
        assert result is not None
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result

    def test_histogram_positif_sur_tendance_haussiere(self):
        """
        Accélération haussière → histogram MACD > 0.

        Avec des prix LINÉAIRES, fast_ema et slow_ema croissent au même
        rythme → MACD constant → histogram = 0. Il faut une ACCÉLÉRATION
        (prix qui montent de plus en plus vite) pour que fast_ema dépasse
        slow_ema et que l'histogram soit positif.
        """
        # Phase plate puis forte accélération → fast EMA réagit avant slow EMA
        prices = [100.0] * 30 + [100.0 + i * 5 for i in range(1, 21)]
        result = macd(prices)
        assert result is not None
        assert result["histogram"] > 0

    def test_histogram_negatif_sur_tendance_baissiere(self):
        """
        Accélération baissière → histogram MACD < 0.
        Même raisonnement : il faut une décélération soudaine.
        """
        # Phase haute puis forte chute → fast EMA chute avant slow EMA
        prices = [200.0] * 30 + [200.0 - i * 5 for i in range(1, 21)]
        result = macd(prices)
        assert result is not None
        assert result["histogram"] < 0

    def test_histogram_egal_macd_moins_signal(self):
        prices = [100.0 + i * 0.5 for i in range(40)]
        result = macd(prices)
        assert result is not None
        assert result["histogram"] == pytest.approx(
            result["macd"] - result["signal"], abs=1e-3
        )


# ─── TESTS BOLLINGER BANDS ───────────────────────────────────────────────────

class TestBollingerBands:

    def test_retourne_none_si_pas_assez_de_donnees(self):
        assert bollinger_bands([1.0] * 5, period=20) is None

    def test_retourne_none_si_liste_vide(self):
        assert bollinger_bands([], period=20) is None

    def test_retourne_les_bonnes_cles(self):
        result = bollinger_bands([100.0] * 20)
        assert result is not None
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result

    def test_middle_est_la_moyenne(self):
        prices = [100.0] * 20
        result = bollinger_bands(prices)
        assert result["middle"] == pytest.approx(100.0)

    def test_upper_superieur_a_lower(self):
        prices = [100.0 + i for i in range(20)]
        result = bollinger_bands(prices)
        assert result["upper"] > result["lower"]

    def test_bandes_symetriques_autour_du_middle(self):
        prices = [100.0 + i for i in range(20)]
        result = bollinger_bands(prices)
        assert result["upper"] - result["middle"] == pytest.approx(
            result["middle"] - result["lower"], abs=0.01
        )

    def test_bandes_serrees_sur_prix_plats(self):
        """Prix constants → bandes très serrées (std = 0)."""
        prices = [100.0] * 20
        result = bollinger_bands(prices)
        assert result["upper"] == pytest.approx(100.0)
        assert result["lower"] == pytest.approx(100.0)

    def test_bandes_larges_sur_volatilite_elevee(self):
        """Prix très volatils → bandes larges."""
        prices = [100.0 if i % 2 == 0 else 200.0 for i in range(20)]
        result_vol  = bollinger_bands(prices)
        result_flat = bollinger_bands([150.0] * 20)
        assert (result_vol["upper"] - result_vol["lower"]) > \
               (result_flat["upper"] - result_flat["lower"])


# ─── TESTS ANALYZE ───────────────────────────────────────────────────────────

class TestAnalyze:

    # ── Structure et cas limites ─────────────────────────

    def test_hold_si_liste_vide(self):
        result = analyze([])
        assert result["signal"] == "HOLD"
        assert result["score"]  == 0
        assert result["strong"] is False

    def test_hold_si_un_seul_prix(self):
        result = analyze([100.0])
        assert result["signal"] == "HOLD"

    def test_retourne_toutes_les_cles_attendues(self, prices_40):
        result = analyze(prices_40)
        expected_keys = {"signal", "score", "strong", "ma10", "ma20",
                         "rsi", "macd", "bollinger"}
        assert set(result.keys()) == expected_keys

    def test_signal_valide(self, prices_40):
        result = analyze(prices_40)
        assert result["signal"] in ("BUY", "SELL", "HOLD")

    def test_score_entre_0_et_100(self, prices_40):
        result = analyze(prices_40)
        assert 0 <= result["score"] <= 100

    def test_strong_coherent_avec_score(self, prices_40):
        result = analyze(prices_40)
        if result["score"] >= 70:
            assert result["strong"] is True
        else:
            assert result["strong"] is False

    def test_score_0_si_hold(self):
        result = analyze([100.0] * 30)
        assert result["score"] == 0
        assert result["strong"] is False

    def test_score_minimum_50_si_signal_non_hold(self, prices_40):
        result = analyze(prices_40)
        if result["signal"] != "HOLD":
            assert result["score"] >= 50

    def test_ma10_et_ma20_presents_si_assez_de_donnees(self, prices_40):
        result = analyze(prices_40)
        assert result["ma10"]  is not None
        assert result["ma20"]  is not None

    def test_rsi_present_si_assez_de_donnees(self, prices_40):
        result = analyze(prices_40)
        assert result["rsi"] is not None

    def test_macd_present_si_assez_de_donnees(self, prices_40):
        result = analyze(prices_40)
        assert result["macd"] is not None

    def test_bollinger_present_si_assez_de_donnees(self, prices_40):
        result = analyze(prices_40)
        assert result["bollinger"] is not None

    def test_indicateurs_none_si_pas_assez_de_prix(self):
        result = analyze([100.0, 101.0])
        assert result["ma10"] is None
        assert result["ma20"] is None

    # ── Tests directionnels (via monkeypatch) ────────────

    def test_signal_buy_quand_tous_indicateurs_acheteurs(self, monkeypatch):
        """Tous les indicateurs BUY → signal BUY fort."""
        import app.strategy as strat
        # SMA: ma10 > ma20 → BUY
        monkeypatch.setattr(strat, "sma",
            lambda p, period: 110.0 if period == 10 else 100.0)
        # RSI: 25 → survente → BUY
        monkeypatch.setattr(strat, "rsi",
            lambda p, period=14: 25.0)
        # MACD: histogram > 0 → BUY
        monkeypatch.setattr(strat, "macd",
            lambda p, **kw: {"macd": 1.0, "signal": 0.5, "histogram": 0.5})
        # BB: prix (49) < lower (51) → BUY
        monkeypatch.setattr(strat, "bollinger_bands",
            lambda p, **kw: {"upper": 200.0, "middle": 100.0, "lower": 51.0})

        result = strat.analyze([49.0] * 40)
        assert result["signal"] == "BUY"
        assert result["score"]  == 100
        assert result["strong"] is True

    def test_signal_sell_quand_tous_indicateurs_vendeurs(self, monkeypatch):
        """Tous les indicateurs SELL → signal SELL fort."""
        import app.strategy as strat
        # SMA: ma10 < ma20 → SELL
        monkeypatch.setattr(strat, "sma",
            lambda p, period: 90.0 if period == 10 else 100.0)
        # RSI: 80 → surachat → SELL
        monkeypatch.setattr(strat, "rsi",
            lambda p, period=14: 80.0)
        # MACD: histogram < 0 → SELL
        monkeypatch.setattr(strat, "macd",
            lambda p, **kw: {"macd": -1.0, "signal": -0.5, "histogram": -0.5})
        # BB: prix (201) > upper (200) → SELL
        monkeypatch.setattr(strat, "bollinger_bands",
            lambda p, **kw: {"upper": 200.0, "middle": 100.0, "lower": 50.0})

        result = strat.analyze([201.0] * 40)
        assert result["signal"] == "SELL"
        assert result["score"]  == 100
        assert result["strong"] is True

    def test_signal_hold_si_indicateurs_en_conflit(self, monkeypatch):
        """SMA BUY + RSI SELL + MACD BUY + BB SELL → conflit → HOLD."""
        import app.strategy as strat
        monkeypatch.setattr(strat, "sma",
            lambda p, period: 110.0 if period == 10 else 100.0)   # BUY  (1)
        monkeypatch.setattr(strat, "rsi",
            lambda p, period=14: 80.0)                              # SELL (2)
        monkeypatch.setattr(strat, "macd",
            lambda p, **kw: {"macd": 1.0, "signal": 0.5, "histogram": 0.5})  # BUY (2)
        monkeypatch.setattr(strat, "bollinger_bands",
            lambda p, **kw: {"upper": 50.0, "middle": 100.0, "lower": 150.0})  # prix 201 > upper → SELL (1)

        result = strat.analyze([201.0] * 40)
        # BUY: 1+2=3, SELL: 2+1=3 → égalité → HOLD
        assert result["signal"] == "HOLD"
        assert result["score"]  == 0

    def test_rsi_seul_buy_sans_autres_indicateurs(self, monkeypatch):
        """RSI oversold + SMA neutre (identiques) + pas de MACD/BB → BUY."""
        import app.strategy as strat
        monkeypatch.setattr(strat, "sma",
            lambda p, period: 100.0)   # ma10 == ma20 → neutre
        monkeypatch.setattr(strat, "rsi",
            lambda p, period=14: 20.0)  # survente → BUY (poids 2)
        monkeypatch.setattr(strat, "macd",
            lambda p, **kw: None)       # pas assez de données
        monkeypatch.setattr(strat, "bollinger_bands",
            lambda p, **kw: None)       # pas assez de données

        result = strat.analyze([100.0] * 40)
        assert result["signal"] == "BUY"

    # ── Tests de cohérence des indicateurs dans le résultat ──

    def test_macd_dans_result_contient_les_bonnes_cles(self, prices_40):
        result = analyze(prices_40)
        if result["macd"] is not None:
            assert "macd"      in result["macd"]
            assert "signal"    in result["macd"]
            assert "histogram" in result["macd"]

    def test_bollinger_dans_result_contient_les_bonnes_cles(self, prices_40):
        result = analyze(prices_40)
        if result["bollinger"] is not None:
            assert "upper"  in result["bollinger"]
            assert "middle" in result["bollinger"]
            assert "lower"  in result["bollinger"]

    def test_ma10_et_ma20_arrondis_a_2_decimales(self, prices_40):
        result = analyze(prices_40)
        if result["ma10"] is not None:
            assert result["ma10"] == round(result["ma10"], 2)
            assert result["ma20"] == round(result["ma20"], 2)