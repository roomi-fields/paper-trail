"""Adapter Obsidian — layout par défaut.

Conventions :
- SOTAs : `SOTA_*.md` co-localisés sous le vault (récursif). Convention
  observée sur les vaults de recherche (`10_SOURCES/<biblio>/SOTA_*.md`,
  `40_OUTPUT/Papers/<P*>/SOTA_*.md`).
- Papers : `Paper_*.md` ou `P*_*.md` (pattern P9alpha_v1_FR, etc.).
- Citations : wikilinks Obsidian `[[slug]]`.
- Index complet : tous les `.md` du vault (rglob), pour vérifier
  l'existence d'un nom cité.
"""
from __future__ import annotations
import re
from pathlib import Path

from .base import Adapter


_WIKILINK_RE = re.compile(r"\[\[([a-z0-9_]+)\]\]")


class ObsidianAdapter(Adapter):
    """Adapter pour vault Obsidian (layout par défaut)."""

    def index_md_files(self) -> set[str]:
        """Rglob tous les .md du vault, retourne l'ensemble des stems."""
        names: set[str] = set()
        if not self.vault_root.exists():
            return names
        for p in self.vault_root.rglob("*.md"):
            names.add(p.stem)
        return names

    def find_sotas(self) -> list[Path]:
        """Rglob SOTA_*.md et Paper_*.md."""
        if not self.vault_root.exists():
            return []
        results: list[Path] = []
        for pattern in ("SOTA_*.md", "Paper_*.md"):
            results.extend(self.vault_root.rglob(pattern))
        return results

    def parse_citations(self, sota_path: Path) -> list[str]:
        """Extrait les `[[slug]]` du body markdown du SOTA."""
        try:
            body = sota_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        return [m.group(1) for m in _WIKILINK_RE.finditer(body)]

    def sota_output_path(self, topic_slug: str) -> Path:
        """Par défaut, place à la racine du vault (l'utilisateur peut
        ensuite déplacer le SOTA dans son dossier biblio approprié).
        """
        return self.vault_root / f"SOTA_{topic_slug}.md"

    def format_citation(self, slug: str) -> str:
        """Wikilink Obsidian."""
        return f"[[{slug}]]"
