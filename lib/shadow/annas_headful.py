"""Anna's Archive via navigateur *visible* — source d'acquisition opt-in.

Pourquoi cette source en plus de `annas_archive.py` : sur le terrain
(2026-08, cf. issue #1), la voie `cloudscraper` échoue en deux temps.

| Étape                         | cloudscraper | Playwright headless | Playwright **headful** |
|-------------------------------|--------------|---------------------|------------------------|
| Page `/scidb/` ou `/md5/`     | 403 DDoS-Guard | passe             | passe                  |
| Lien partenaire `*.xyz/dN/…`  | —            | obtenu              | obtenu                 |
| Téléchargement du PDF         | —            | **502** systématique | **PDF valide**        |

Le challenge anti-robot tombe en headless, mais le serveur de fichiers
partenaire refuse tant que le navigateur est invisible. Un Chromium
fenêtré dans un affichage virtuel obtient le fichier normalement :

    xvfb-run -a --server-args="-screen 0 1400x1000x24" python -m pipeline run

Deux détails de protocole découverts au passage :
  - la page `/md5/<md5>` n'expose ses liens `slow_download` qu'avec le
    paramètre `?&check=1` ;
  - le lien partenaire n'apparaît sur la page du créneau qu'après ~20 s ;
    les créneaux (`/0/0` … `/0/3`) sont contingentés, on les essaie en série.

Activation : `RESEARCH_ENABLE_SHADOW_LIBS=1` **et** Playwright installé
(`pip install playwright && playwright install chromium`) **et** un
affichage disponible (`$DISPLAY`, typiquement fourni par `xvfb-run`).
Sinon la source se déclare indisponible et la cascade continue —
aucun comportement existant n'est modifié.

L'utilisation d'Anna's Archive peut violer le droit d'auteur dans votre
juridiction. Cf. DISCLAIMER.md à la racine du plugin.

Anti-homonymie : garantie comme pour toute source par la validation
page 1 de `_save_and_validate`.
"""
from __future__ import annotations

import contextlib
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

from pipeline.registry import Ref

from .mirrors import get_aa_mirrors

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36")
CHALLENGE = ("DDoS", "Just a moment", "Attention Required")
PARTNER_LINK = re.compile(r'href="(https://[a-z0-9]+\.[a-z]{2,4}/d\d[^"]+)"')
SLOTS = (0, 1, 2, 3)
# Les créneaux contingentés se sondent lentement (4 créneaux × 9 sondes × 8 s
# par miroir). Sans borne, une seule ref peut occuper la passe une demi-heure.
BUDGET_S = int(os.environ.get("RESEARCH_ANNAS_HEADFUL_BUDGET_S") or 600)


@contextlib.contextmanager
def _address_space_unbounded():
    """Lève le temps du lancement la borne d'espace d'adressage du process.

    `pipeline run` se borne à 1,5 Go pour ne pas figer la machine, et les
    rlimits sont héritées par les processus fils. Chromium réserve des
    dizaines de Go d'adressage virtuel : sous cette borne il meurt au
    démarrage. On remonte la limite douce au niveau de la limite dure le
    temps du lancement, puis on la remet.
    """
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    except (ImportError, OSError):
        yield
        return
    if soft == hard:
        yield  # rien à lever (limite dure déjà au même niveau)
        return
    try:
        resource.setrlimit(resource.RLIMIT_AS, (hard, hard))
    except (ValueError, OSError):
        yield
        return
    try:
        yield
    finally:
        with contextlib.suppress(ValueError, OSError):
            resource.setrlimit(resource.RLIMIT_AS, (soft, hard))


def available() -> tuple[bool, str]:
    """La source est-elle utilisable ici ? (Playwright + affichage)"""
    if not os.environ.get("DISPLAY"):
        return False, "no_display_run_under_xvfb"
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False, "playwright_not_installed"
    return True, "ok"


def _content(pg, tries: int = 3) -> str:
    """`page.content()` échoue si la page navigue — on retente."""
    for _ in range(tries):
        try:
            return pg.content()
        except Exception:
            pg.wait_for_timeout(2500)
    return ""


def _load(pg, url: str, tries: int = 7, wait: int = 4000) -> str:
    """Charge une page et patiente tant que le challenge anti-robot s'affiche."""
    try:
        pg.goto(url, timeout=90000, wait_until="load")
    except Exception:
        return ""
    for _ in range(tries):
        pg.wait_for_timeout(wait)
        html = _content(pg)
        try:
            title = pg.title()
        except Exception:
            continue
        if html and not any(c in title for c in CHALLENGE):
            return html
    return ""


def _md5_for(pg, ref: Ref) -> tuple[str | None, str]:
    """MD5 via le champ déjà connu, sinon `/scidb/<doi>`, sinon recherche."""
    fm = ref.frontmatter
    if fm.get("annas_md5"):
        return fm["annas_md5"], "cached_md5"

    from pipeline.cascade import _doi
    doi = _doi(ref)
    mirrors = get_aa_mirrors()

    if doi:
        for mirror in mirrors:
            found = re.findall(r"/md5/([0-9a-f]{32})",
                               _load(pg, f"https://{mirror}/scidb/{quote(doi, safe=':/')}"))
            if found:
                return found[0], f"scidb:{mirror}"

    title = (fm.get("title") or "").strip().strip("'\"")
    author = (fm.get("author") or "").split(",")[0].strip()
    if not title:
        return None, "no_title_for_search"
    words = [w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]{6,}", title)][:4]
    for mirror in mirrors:
        html = _load(pg, f"https://{mirror}/search?q={quote(f'{title} {author}')}")
        if not html:
            continue
        # un mot distinctif du titre doit apparaître dans le bloc du résultat
        for block in re.split(r'(?=<a[^>]+href="/md5/)', html):
            m = re.search(r'href="/md5/([0-9a-f]{32})"', block)
            if m and any(w in block.lower() for w in words):
                return m.group(1), f"search:{mirror}"
    return None, "no_md5_found"


def _download(pg, mirror: str, md5: str, patience: int = 9,
              deadline: float | None = None) -> tuple[bytes | None, str]:
    """Parcourt les créneaux `slow_download` jusqu'à obtenir le fichier."""
    for slot in SLOTS:
        if deadline and time.monotonic() > deadline:
            return None, "budget_exhausted"
        slot_url = f"https://{mirror}/slow_download/{md5}/0/{slot}"
        try:
            pg.goto(slot_url, timeout=90000, wait_until="load")
        except Exception:
            continue
        link = None
        for _ in range(patience):
            if deadline and time.monotonic() > deadline:
                return None, "budget_exhausted"
            pg.wait_for_timeout(8000)
            html = _content(pg)
            m = PARTNER_LINK.search(html)
            if m:
                link = m.group(1)
                break
            low = html.lower()
            if "waitlist" in low or "too many" in low:
                break  # créneau contingenté : passer au suivant
        if not link:
            continue
        try:
            with pg.expect_download(timeout=300000) as dl:
                pg.click(f'a[href="{link}"]')
            data = Path(dl.value.path()).read_bytes()
            if data[:4] == b"%PDF":
                return data, f"slow_slot{slot}"
        except Exception:
            pass
    return None, "no_slot_delivered"


def try_annas_headful(ref: Ref) -> tuple[str, dict]:
    """Source de cascade : Anna's Archive piloté par un navigateur visible."""
    ok, why = available()
    if not ok:
        return "no_source", {"reason": why}

    from playwright.sync_api import sync_playwright
    from pipeline.cascade import _save_and_validate

    mirrors = get_aa_mirrors()
    deadline = time.monotonic() + BUDGET_S
    with sync_playwright() as pw, _address_space_unbounded():
        browser = pw.chromium.launch(
            headless=False,  # invisible ⇒ 502 côté serveur de fichiers
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        try:
            ctx = browser.new_context(user_agent=UA, locale="en-US",
                                      viewport={"width": 1360, "height": 900},
                                      accept_downloads=True)
            pg = ctx.new_page()
            md5, via = _md5_for(pg, ref)
            if not md5:
                return "no_source", {"reason": via}
            ref.frontmatter.setdefault("annas_md5", md5)
            for mirror in mirrors:
                if time.monotonic() > deadline:
                    return "failed", {"reason": "budget_exhausted_retry_later",
                                      "md5": md5, "via": via}
                data, how = _download(pg, mirror, md5, deadline=deadline)
                if data:
                    verdict, info = _save_and_validate(data, ref)
                    info.setdefault("via", f"{via}/{how}@{mirror}")
                    return verdict, info
            return "failed", {"reason": "all_mirrors_no_slot", "md5": md5, "via": via}
        finally:
            browser.close()
