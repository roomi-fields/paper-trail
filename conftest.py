"""Pytest bootstrap : assure la présence des variables d'environnement
nécessaires pour importer `pipeline.config` au début de la session de test.

Les tests qui ont besoin d'un vault réel utilisent `tmp_path` + monkeypatch
de RESEARCH_VAULT_PATH. Ce conftest fournit juste un défaut neutre pour que
l'import du module config ne lève pas ConfigError.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _ensure_env_default(key: str, default_value: str) -> None:
    if not os.environ.get(key):
        os.environ[key] = default_value


_TEST_VAULT = Path(tempfile.gettempdir()) / "paper-trail-test-vault"
_TEST_VAULT.mkdir(parents=True, exist_ok=True)
_ensure_env_default("RESEARCH_VAULT_PATH", str(_TEST_VAULT))
