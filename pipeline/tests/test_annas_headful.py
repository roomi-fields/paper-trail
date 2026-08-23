"""Tests de la source Anna's Archive par navigateur visible (PR #2).

L'essentiel est ici : la source ne doit rien casser quand elle n'est pas
disponible, et la borne mémoire que `pipeline run` se pose ne doit pas
empêcher le navigateur de démarrer (les rlimits sont héritées par les fils,
et Chromium réserve des dizaines de Go d'espace d'adressage virtuel).
"""
from __future__ import annotations

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
