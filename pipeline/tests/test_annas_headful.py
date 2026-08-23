"""Tests de la source Anna's Archive par navigateur visible (PR #2).

L'essentiel est ici : la source ne doit rien casser quand elle n'est pas
disponible, et la borne mémoire que `pipeline run` se pose ne doit pas
empêcher le navigateur de démarrer (les rlimits sont héritées par les fils,
et Chromium réserve des dizaines de Go d'espace d'adressage virtuel).
"""
from __future__ import annotations

import os
import resource
import sys
from pathlib import Path

import pytest

PROJ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJ))

from lib.shadow import annas_headful as ah  # noqa: E402
from pipeline.cli import _set_memory_limit  # noqa: E402
from pipeline.transitions import _only_transient_failures  # noqa: E402


# ─── Disponibilité ──────────────────────────────────────────────────────────

def test_sans_affichage_la_source_se_declare_indisponible(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    assert ah.available() == (False, "no_display_run_under_xvfb")


def test_sans_playwright_la_source_se_declare_indisponible(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":99")
    import builtins
    vrai_import = builtins.__import__

    def _refuse(name, *a, **k):
        if name == "playwright":
            raise ImportError("playwright absent")
        return vrai_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _refuse)
    assert ah.available() == (False, "playwright_not_installed")


def test_source_indisponible_ne_tente_rien(monkeypatch):
    """Verdict `no_source` immédiat : la cascade continue, rien n'est modifié."""
    monkeypatch.delenv("DISPLAY", raising=False)
    from pipeline.registry import Ref
    ref = Ref(slug="t", path=Path("/nonexistent/t.md"),
              frontmatter={"slug": "t", "state": "uid_resolved"}, body="\n")
    verdict, info = ah.try_annas_headful(ref)
    assert verdict == "no_source"
    assert info["reason"] == "no_display_run_under_xvfb"


# ─── Borne d'espace d'adressage ─────────────────────────────────────────────

def test_run_preserve_la_limite_dure():
    """`pipeline run` ne doit pas verrouiller la limite dure : sinon la borne
    est irréversible et aucun navigateur ne peut plus démarrer."""
    soft0, hard0 = resource.getrlimit(resource.RLIMIT_AS)
    try:
        _set_memory_limit(1.5)
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        assert hard == hard0, "la limite dure d'origine doit être préservée"
        assert soft <= 1.5 * 1024 ** 3
    finally:
        resource.setrlimit(resource.RLIMIT_AS, (soft0, hard0))


def test_borne_levee_puis_retablie():
    soft0, hard0 = resource.getrlimit(resource.RLIMIT_AS)
    borne = 1536 * 1024 * 1024
    if hard0 != resource.RLIM_INFINITY and hard0 <= borne:
        pytest.skip("limite dure déjà basse dans cet environnement")
    resource.setrlimit(resource.RLIMIT_AS, (borne, hard0))
    try:
        with ah._address_space_unbounded():
            dedans, _ = resource.getrlimit(resource.RLIMIT_AS)
            assert dedans == hard0, "la borne doit être levée pour le lancement"
        apres, _ = resource.getrlimit(resource.RLIMIT_AS)
        assert apres == borne, "la borne doit être rétablie après le lancement"
    finally:
        resource.setrlimit(resource.RLIMIT_AS, (soft0, hard0))


# ─── Épuisement du budget = attente, pas verrou ─────────────────────────────

def test_budget_epuise_est_un_echec_passager():
    attempts = [{"verdict": "failed", "reason": "budget_exhausted_retry_later"}]
    assert _only_transient_failures(attempts) is True


def test_test_denvironnement_sans_config_de_vault():
    """Le test d'environnement documenté dans `docs/ACQUISITION_HEADFUL.md`
    doit tourner dans un conteneur nu, avant toute configuration du vault :
    importer le module ne doit donc tirer aucune dépendance de configuration.
    """
    import subprocess
    code = ("import sys; sys.path.insert(0, %r);"
            "from lib.shadow.annas_headful import available; print(available())"
            % str(PROJ))
    env = {k: v for k, v in os.environ.items()
           if k not in ("RESEARCH_VAULT_PATH", "DISPLAY")}
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, env=env, timeout=60)
    assert r.returncode == 0, r.stderr[-400:]
    assert "no_display_run_under_xvfb" in r.stdout


# ─── Issue #6 : le pilote du navigateur naît hors de la borne mémoire ───────

def _fausse_playwright(monkeypatch, a_l_ouverture):
    """Installe un faux paquet `playwright` dont l'ouverture est instrumentée.

    L'ouverture de `sync_playwright()` est le moment où le pilote node est
    lancé — c'est *là* que la borne d'espace d'adressage doit déjà être levée.
    """
    import types

    class _Abandon(Exception):
        """Interrompt la source une fois la mesure prise."""

    class _Session:
        def __enter__(self):
            a_l_ouverture()
            raise _Abandon
        def __exit__(self, *a):
            return False

    paquet = types.ModuleType("playwright")
    api = types.ModuleType("playwright.sync_api")
    api.sync_playwright = lambda: _Session()
    paquet.sync_api = api
    monkeypatch.setitem(sys.modules, "playwright", paquet)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", api)
    return _Abandon


def _ref_test():
    from pipeline.registry import Ref
    return Ref(slug="t", path=Path("/nonexistent/t.md"),
               frontmatter={"slug": "t", "state": "uid_resolved"}, body="\n")


def test_le_pilote_du_navigateur_nait_hors_de_la_borne(monkeypatch):
    """Régression issue #6.

    `pipeline run` borne l'espace d'adressage à 1,5 Go. Le pilote node hérite
    de la borne en vigueur à sa naissance, et c'est *lui* qui lance Chromium.
    Si la garde qui lève la borne est imbriquée après `sync_playwright()`,
    le navigateur meurt au démarrage. On mesure donc la borne au moment exact
    de l'ouverture de la session Playwright.
    """
    soft0, hard0 = resource.getrlimit(resource.RLIMIT_AS)
    borne = 1536 * 1024 * 1024
    if hard0 != resource.RLIM_INFINITY and hard0 <= borne:
        pytest.skip("limite dure déjà basse dans cet environnement")

    monkeypatch.setenv("DISPLAY", ":99")
    vu = {}
    abandon = _fausse_playwright(
        monkeypatch,
        lambda: vu.__setitem__("soft", resource.getrlimit(resource.RLIMIT_AS)[0]))

    resource.setrlimit(resource.RLIMIT_AS, (borne, hard0))
    try:
        with pytest.raises(abandon):
            ah.try_annas_headful(_ref_test())
    finally:
        resource.setrlimit(resource.RLIMIT_AS, (soft0, hard0))

    assert vu["soft"] == hard0, (
        "la borne doit déjà être levée quand le pilote est lancé, "
        "sinon le pilote en hérite et Chromium meurt au démarrage")


# ─── Issue #7 : le budget est une garantie, pas une intention ──────────────

def test_le_budget_coupe_une_attente_non_bornee(monkeypatch):
    """Régression issue #7.

    L'attente de fin de téléchargement n'accepte aucun délai côté Playwright.
    Le garde-fou dur doit rendre la main malgré tout, avec un échec passager.
    """
    import time as _t
    import types

    class _Session:
        def __enter__(self):
            _t.sleep(60)   # attente non bornée, comme un transfert qui se tait
        def __exit__(self, *a):
            return False

    paquet = types.ModuleType("playwright")
    api = types.ModuleType("playwright.sync_api")
    api.sync_playwright = lambda: _Session()
    paquet.sync_api = api
    monkeypatch.setitem(sys.modules, "playwright", paquet)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", api)
    monkeypatch.setenv("DISPLAY", ":99")
    monkeypatch.setattr(ah, "BUDGET_S", 1)
    monkeypatch.setattr(ah, "GUARD_GRACE_S", 0)

    depart = _t.monotonic()
    verdict, info = ah.try_annas_headful(_ref_test())
    ecoule = _t.monotonic() - depart

    assert verdict == "failed"
    assert info["reason"] == "budget_exhausted_retry_later"
    assert ecoule < 15, f"le budget n'a pas coupé : {ecoule:.0f}s"
    assert _only_transient_failures([{"verdict": verdict, "reason": info["reason"]}])


def test_le_garde_fou_restaure_l_alarme_precedente():
    """Le garde-fou ne doit pas laisser d'alarme derrière lui."""
    import signal
    avant = signal.getsignal(signal.SIGALRM)
    with ah._wall_clock_guard(300):
        pass
    assert signal.getsignal(signal.SIGALRM) is avant
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0


# ─── Échéance consultée avant chaque attente du navigateur ─────────────────

class _PageMuette:
    """Page factice : enregistre les appels, n'attend jamais."""
    def __init__(self):
        self.appels = []
    def goto(self, *a, **k):
        self.appels.append("goto")
    def wait_for_timeout(self, ms):
        self.appels.append(("wait", ms))
    def content(self):
        return "<html></html>"
    def title(self):
        return "ok"


def test_millisecondes_restantes_ne_sont_jamais_negatives():
    import time as _t
    assert ah._left_ms(_t.monotonic() - 10, 90000) == 0
    assert ah._left_ms(_t.monotonic() + 1000, 90000) == 90000


def test_echeance_depassee_aucune_navigation(monkeypatch):
    """Aucune attente du navigateur ne doit démarrer après l'échéance —
    et surtout aucune avec un délai nul, que Playwright lit « jamais »."""
    import time as _t
    echu = _t.monotonic() - 1
    pg = _PageMuette()

    assert ah._load(pg, "https://x/", echu) == ""
    assert ah._download(pg, "x", "0" * 32, echu) == (None, "budget_exhausted")
    assert ah._md5_for(pg, _ref_test(), echu) == (None, "budget_exhausted")
    assert pg.appels == [], f"le navigateur a été sollicité après l'échéance : {pg.appels}"
