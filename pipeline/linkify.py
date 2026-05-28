"""Module linkify — insère les wikilinks finaux dans un SOTA.

Pour chaque mention identifiée :
- Si la ref est validée avec PDF (state=page1_validated|sota_cited_confirmed
  ET pdf_path présent) → wikilink direct vers le PDF.
- Sinon → wikilink vers une ancre `#source-<lastname>-<year>` dans une
  section `## Statut des sources` régénérée idempotemment en bas du SOTA.

La section Statut est encadrée par les marqueurs HTML
`<!-- paper-trail:statut:begin -->` / `:end -->` pour permettre la
régénération propre (`re.DOTALL` strip + rewrite).

Phase 5 du plan refonte INGEST.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Marqueurs idempotents
STATUT_BEGIN = "<!-- paper-trail:statut:begin -->"
STATUT_END = "<!-- paper-trail:statut:end -->"
STATUT_HEADING = "## Statut des sources"

# Catégories en ordre stable
STATUT_CATEGORIES = [
    ("validated", "### Sources validées (page1 OK, PDF présent)"),
    ("in_progress", "### Sources en cours d'acquisition"),
    ("blocked", "### Sources bloquées (intervention humaine)"),
    ("retracted", "### Sources rétractées"),
    ("missing", "### Sources non créées (mention détectée, ref pas encore créée)"),
]


@dataclass
class StatutEntry:
    """Une entrée de la section ## Statut des sources."""
    slug: Optional[str]
    anchor: str
    lastname: str
    year: str
    title: str
    state: str
    reason: str
    pdf_path: Optional[str] = None
    category: str = "missing"


@dataclass
class LinkifyResult:
    sota_path: Path
    n_pdf_wikilinks: int = 0
    n_anchor_wikilinks: int = 0
    statut_entries: list[StatutEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def total_substitutions(self) -> int:
        return self.n_pdf_wikilinks + self.n_anchor_wikilinks


def _make_anchor(lastname: str, year: str) -> str:
    """Génère une ancre stable pour la section Statut.

    Idempotent : même (lastname, year) → même ancre.
    """
    lname = re.sub(r"[^a-z0-9]", "", (lastname or "").lower()) or "unknown"
    yr = re.sub(r"[^0-9]", "", year or "")[:4] or "0000"
    return f"source-{lname}-{yr}"


def _classify_entry(state: Optional[str]) -> str:
    """Classe une entrée dans une des 5 catégories Statut."""
    if not state or state == "not_yet_created":
        return "missing"
    if state == "retracted":
        return "retracted"
    if state in ("page1_validated", "sota_cited_confirmed"):
        return "validated"
    if state.startswith("blocked_human"):
        return "blocked"
    # candidate, uid_resolved, pdf_acquired, awaiting_rtfm_ocr, needs_reacquisition
    return "in_progress"


def _strip_existing_statut(text: str) -> str:
    """Retire la section Statut existante (entre marqueurs) si présente."""
    pattern = re.compile(
        re.escape(STATUT_BEGIN) + r".*?" + re.escape(STATUT_END),
        flags=re.DOTALL,
    )
    return pattern.sub("", text).rstrip() + "\n"


def build_statut_section(entries: list[StatutEntry]) -> str:
    """Génère le markdown de la section Statut. Ordre stable par catégorie."""
    lines = [STATUT_BEGIN, "", STATUT_HEADING, ""]
    lines.append(
        "_Section générée automatiquement par `/paper-trail:linkify`. "
        "Ne pas éditer manuellement entre les marqueurs._"
    )
    lines.append("")

    by_cat: dict[str, list[StatutEntry]] = {c: [] for c, _ in STATUT_CATEGORIES}
    for e in entries:
        by_cat.setdefault(e.category, []).append(e)

    for cat_key, heading in STATUT_CATEGORIES:
        es = sorted(
            by_cat.get(cat_key, []),
            key=lambda x: (x.lastname.lower(), x.year),
        )
        if not es:
            continue
        lines.append(heading)
        lines.append("")
        for e in es:
            if e.pdf_path:
                ref_link = (
                    f"[[{Path(e.pdf_path).name}|"
                    f"{e.lastname.lower()}_{e.year}]]"
                )
            elif e.slug:
                ref_link = f"[[{e.slug}]]"
            else:
                ref_link = f"`{e.lastname.lower()}_{e.year}`"
            title_short = (e.title or "")[:80]
            lines.append(
                f'- <a id="{e.anchor}"></a> **{e.lastname} ({e.year})** '
                f'— {title_short} · state=`{e.state}` · {e.reason} · '
                f'{ref_link}'
            )
        lines.append("")

    lines.append(STATUT_END)
    return "\n".join(lines)


def _substitute_with_anchor(
    sota_path: Path, citation, anchor: str,
    lastname: str, year: str,
) -> bool:
    """Substitue dans le SOTA un wikilink `[[#anchor|lastname_year]]` devant
    le raw de la citation (Tier 1 strict uniquement — si raw n'est pas
    littéral, on rate ; mais avec citation-parser v2 c'est OK).
    """
    from .ingest import _line_already_has_lastname_wikilink

    try:
        text = sota_path.read_text(encoding="utf-8")
    except OSError:
        return False

    raw = (citation.raw or "").strip()
    if not raw or raw not in text:
        return False

    wikilink = f"[[#{anchor}|{lastname.lower()}_{year or '0000'}]]"
    lastname_anorm = re.sub(r"[^a-z0-9]", "", (lastname or "").lower())

    new_lines = []
    any_subst = False
    for line in text.split("\n"):
        if (raw in line and not _line_already_has_lastname_wikilink(
                line, lastname_anorm)):
            new_lines.append(line.replace(raw, f"{wikilink} — {raw}", 1))
            any_subst = True
        else:
            new_lines.append(line)
    if any_subst:
        sota_path.write_text("\n".join(new_lines), encoding="utf-8")
        return True
    return False


def linkify_sota(
    sota_path: Path, identify_report, apply: bool = False,
) -> LinkifyResult:
    """Insère les wikilinks finaux + régénère la section Statut.

    Args:
        sota_path: chemin du SOTA
        identify_report: IdentifyReport produit par identify.identify_sota
        apply: True = mute le SOTA, False = compte uniquement (dry-run)
    """
    from .ingest import (
        ParsedCitation, _substitute_to_wikilink,
        _extract_first_author_lastname,
    )
    from .registry import load_ref
    from .config import REFS

    result = LinkifyResult(sota_path=sota_path)
    entries_by_anchor: dict[str, StatutEntry] = {}

    for mention in identify_report.mentions:
        if mention.action_recommended == "skipped_low_confidence":
            continue
        slug = mention.matched_slug or mention.would_create_slug
        if not slug:
            continue

        ref = None
        ref_path = REFS / f"{slug}.md"
        if ref_path.exists():
            ref = load_ref(ref_path)

        state = ref.frontmatter.get("state") if ref else None
        has_pdf = bool(ref and ref.frontmatter.get("pdf_path"))
        pdf_path = ref.frontmatter.get("pdf_path") if ref else None
        is_validated = state in ("page1_validated", "sota_cited_confirmed")

        cit = ParsedCitation(
            author=mention.author, year=mention.year,
            title=mention.title, raw=mention.raw,
            confidence=mention.confidence,
        )

        if is_validated and has_pdf:
            # Cas A : wikilink direct PDF
            if apply and _substitute_to_wikilink(sota_path, cit, slug):
                result.n_pdf_wikilinks += 1
        else:
            # Cas B : wikilink vers ancre Statut + entry
            lastname = (
                _extract_first_author_lastname(mention.author).capitalize()
                or "Unknown"
            )
            anchor = _make_anchor(lastname, mention.year)
            reason = "ref pas encore créée"
            if state == "retracted" and ref:
                rr = ref.frontmatter.get("retracted_reason", "") or ""
                reason = f"retracted: {rr}" if rr else "retracted"
            elif state and state.startswith("blocked_human"):
                br = (ref.frontmatter.get("blocked_reason", "")
                      if ref else "")
                reason = (f"{state.split(':', 1)[-1]} — {br}"
                          if br else state)
            elif state == "awaiting_rtfm_ocr":
                reason = "OCR RTFM en attente"
            elif state:
                reason = f"state={state}"

            entry = StatutEntry(
                slug=slug if ref else None,
                anchor=anchor,
                lastname=lastname,
                year=mention.year or "0000",
                title=mention.title or "",
                state=state or "not_yet_created",
                reason=reason,
                pdf_path=pdf_path,
                category=_classify_entry(state),
            )
            entries_by_anchor[anchor] = entry  # dedup par ancre

            if apply:
                if _substitute_with_anchor(
                    sota_path, cit, anchor, lastname, mention.year
                ):
                    result.n_anchor_wikilinks += 1

    result.statut_entries = list(entries_by_anchor.values())

    if apply and result.statut_entries:
        try:
            text = sota_path.read_text(encoding="utf-8")
            text = _strip_existing_statut(text)
            statut_md = build_statut_section(result.statut_entries)
            text = text.rstrip() + "\n\n" + statut_md + "\n"
            sota_path.write_text(text, encoding="utf-8")
        except OSError as e:
            result.errors.append(f"write statut: {e}")

    return result
