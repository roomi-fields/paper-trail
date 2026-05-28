"""Module paper_search_acquire — tier complémentaire à la cascade.

P6.1 du plan refonte INGEST. Étend acquire en exploitant paper-search MCP
(13 plateformes additionnelles non couvertes par `pipeline/cascade.py`) :

    dblp, Semantic Scholar, PMC, Europe PMC, biorxiv, medrxiv, OpenAIRE,
    CiteSeerX, DOAJ, BASE, Zenodo, SSRN, IACR

Invoqué en fallback par `pipeline/acquire.py::run_acquire_for_sota` quand
les transitions standards du worker B (cascade interne) n'ont pas obtenu
de PDF pour une ref candidate/uid_resolved. Valide page 1
anti-homonymie via `pipeline/ingest.py::_try_validate_page1` avant
d'accepter le PDF.

Le DOI resolution (paper-search MCP appelé dans `_identify_doi`, H2) reste
distinct de cette étape : ici on télécharge des PDF.
"""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional


_PAPER_SEARCH_PROJECT = "/home/romi/dev/mcp/paper-search-mcp"
# Sources supplémentaires (non couvertes par pipeline/cascade.py).
# On omet : crossref (déjà), openalex (déjà), unpaywall (déjà), arxiv (déjà),
# hal (déjà), core (déjà), sci_hub/anna_archive (opt-in séparé).
_EXTRA_SOURCES = (
    "dblp,semantic,pmc,europepmc,biorxiv,medrxiv,"
    "openaire,citeseerx,doaj,base,zenodo,ssrn,iacr"
)
_SEARCH_TIMEOUT_S = 60
_DOWNLOAD_TIMEOUT_S = 180


def _extract_lastname(author: str) -> str:
    if not author:
        return ""
    # Premier auteur, avant la virgule ou " et al."
    first = author.split(",")[0].split(" et al.")[0]
    # Premier mot capitalisé
    parts = first.split()
    return parts[0].lower() if parts else ""


def try_paper_search_download(
    author: str,
    year: str,
    title: str,
    dest_dir: Path,
) -> Optional[tuple[Path, str]]:
    """Tente de télécharger un PDF via paper-search MCP.

    Args:
        author, year, title : métadonnées de la ref pour la recherche
        dest_dir : dossier où sauvegarder le PDF si téléchargé

    Returns:
        (pdf_path, source) si succès, None sinon.
    """
    if not title or not Path(_PAPER_SEARCH_PROJECT).exists():
        return None

    query_parts = [title.strip()]
    if author:
        query_parts.append(author.strip())
    if year:
        query_parts.append(year.strip())
    query = " ".join(query_parts)

    # 1. Search sur les sources additionnelles
    cmd_search = [
        "uv", "run", "--project", _PAPER_SEARCH_PROJECT,
        "python", "-m", "paper_search_mcp.cli", "search", query,
        "-s", _EXTRA_SOURCES, "-n", "5",
    ]
    try:
        proc = subprocess.run(
            cmd_search, capture_output=True, text=True,
            timeout=_SEARCH_TIMEOUT_S,
        )
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout)
    except Exception:
        return None

    expected_lastname = _extract_lastname(author)
    expected_year = (year or "").strip()

    # 2. Filtre + tentative de download par source
    dest_dir.mkdir(parents=True, exist_ok=True)
    for paper in data.get("papers", []):
        # Filtre auteur lastname
        authors_field = str(paper.get("authors") or "").lower()
        if expected_lastname and expected_lastname not in authors_field:
            continue
        # Filtre année si fournie
        pdate = str(paper.get("published_date") or "")
        pyear = pdate[:4] if pdate else ""
        if expected_year and pyear and pyear != expected_year:
            continue
        # Doit avoir un pdf_url ou un paper_id téléchargeable
        if not paper.get("pdf_url") and not paper.get("paper_id"):
            continue

        source = paper.get("source")
        paper_id = paper.get("paper_id")
        if not source or not paper_id:
            continue

        # 3. Download
        cmd_dl = [
            "uv", "run", "--project", _PAPER_SEARCH_PROJECT,
            "python", "-m", "paper_search_mcp.cli", "download",
            source, paper_id, "-o", str(dest_dir),
        ]
        try:
            proc_dl = subprocess.run(
                cmd_dl, capture_output=True, text=True,
                timeout=_DOWNLOAD_TIMEOUT_S,
            )
            if proc_dl.returncode != 0:
                continue
            dl_data = json.loads(proc_dl.stdout)
            if dl_data.get("status") != "ok":
                continue
            pdf_path_str = dl_data.get("path")
            if not pdf_path_str:
                continue
            pdf_path = Path(pdf_path_str)
            if not pdf_path.exists() or pdf_path.stat().st_size < 1000:
                continue
            return (pdf_path, source)
        except Exception:
            continue

    return None
