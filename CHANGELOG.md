# Changelog

All notable changes to the `paper-trail` plugin are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.11] — 2026-06-13

Retour terrain v0.3.10 : 10 refs encore ratées, dont des accès libres
qui auraient dû passer. Quatre correctifs supplémentaires sur le fetcher
HTTP et la validation page 1.

### Added

- **Override DOI dans la validation page 1.** Si le DOI attendu apparaît
  dans la page 1 (ou les 6 premières pages) du PDF téléchargé, le
  validateur accepte directement — court-circuite les checks titre /
  auteur / off-domain qui produisent des faux négatifs sur les thèses
  multilingues (titre FR, corps EN — Rodriguez 2025, Cheveigné…) et
  les publications avec auteur principal différent du registre.

### Changed

- **Fetcher HTTP basé sur `requests` avec UA browser-like.** Le `_http_get`
  utilisait `urllib` avec un UA générique, bloqué par de nombreux
  dépôts (UMass SchoolWorks, KIT, TU Darmstadt). Nouveau : `requests`
  avec User-Agent Chrome 124, Accept-Language, redirects suivis,
  cookies. Fallback `urllib` si `requests` indisponible (tests isolés).
- **Retry UA `curl` sur HTML inattendu.** Certains serveurs (JCMS, HAL,
  journaux scientifiques) servent un viewer JS aux navigateurs et le
  PDF brut aux downloaders ligne-de-commande. Le pipeline retry
  maintenant avec un UA minimaliste `curl/7.88.0` quand la première
  réponse (browser UA) est HTML et que le résolveur landing→PDF n'a
  rien trouvé. Vu sur JCMS, HAL theses, Springer link parfois.

### Fixed

- **Compatible PDF JCMS / HAL theses / OJS galleys.** Combinaison du
  retry curl UA + résolveur landing→PDF couvre maintenant Rodriguez
  2025 (HAL EN-FR thesis), Vigliensoni 2022 (JCMS galley), et tout
  serveur OJS / DSpace qui gate les navigateurs.

## [0.3.10] — 2026-06-13

Retour terrain : un agent rapportait 13/57 PDFs ratés alors que la
plupart sont en accès libre. Diagnostic : la cascade ne suivait pas
les landing pages HTML servies par les dépôts universitaires (HAL,
KIT, Darmstadt, NIME, eScholarship…), et n'offrait pas de point
d'entrée propre quand l'agent connaissait l'URL.

### Added

- **Résolveur landing→PDF universel.** Quand une source de la cascade
  reçoit du HTML au lieu d'un PDF, le pipeline parse maintenant
  automatiquement la balise `<meta name="citation_pdf_url">` (norme
  Highwire Press, supportée par la plupart des dépôts académiques),
  `og:pdf` en repli, puis les liens `<a href="...pdf">` plausibles.
  Suit le lien trouvé avec un en-tête `Referer` correct. Impact massif
  sur HAL/KIT/Darmstadt/NIME/eScholarship — landing pages auparavant
  comptées comme `no_source` deviennent maintenant des PDFs validés.
- **Champ frontmatter `oa_url:`.** Permet d'injecter une URL OA connue
  (page d'auteur, dépôt uni, NIME) quand la cascade automatique ne
  trouve pas le bon PDF. Nouvelle source `manual_oa_url` placée en
  TÊTE de cascade — essayée en premier, bénéficie du résolveur
  landing→PDF.
- **Commande `/paper-trail:inject-url <slug> <url>`.** Met `oa_url`
  dans le frontmatter, débloque la ref si elle l'était, relance la
  cascade ciblée. Évite à un agent de bricoler manuellement (téléchargement
  hors pipeline, dépôt direct, perte de la métrique).
- **Pistes actionnables sur cascade épuisée.** Quand la cascade
  s'épuise, écrit `_hints/<slug>.md` à côté du registre listant les
  deux points d'entrée propres : injecter `oa_url` ou poser le PDF
  localement avec `pdf_path`. Le tableau « ce qui a été tenté » montre
  exactement ce qui a échoué et pourquoi.

### Changed

- **HAL : fallback `/document`.** Si `fileMain_s` retourné par l'API
  HAL renvoie du HTML, le pipeline réessaie sur l'URL canonique
  `https://hal.science/<halId>/document` qui force la sortie PDF.
  Couvre les cas où la première URL pointe vers un viewer.

## [0.3.9] — 2026-06-13

Retour terrain d'une session fraîche : friction d'installation et
MCP `paper-search`. Sept améliorations UX pour un démarrage propre
dans un nouveau projet.

### Added

- **`pipeline preflight`.** Nouvelle sous-commande qui vérifie
  l'environnement avant de lancer une session : vault path,
  permissions, dépendances Python, présence du binaire `git`,
  enregistrement du MCP `paper-search` dans Claude Code, variables
  optionnelles. Tourne **sans** `RESEARCH_VAULT_PATH` (c'est
  précisément ce qu'elle diagnostique). Sortie texte humain ou
  `--json`. Chaque erreur/warning imprime la commande exacte pour
  corriger.
- **Config globale `~/.config/paper-trail/env`.** Chargée
  automatiquement à l'import de `pipeline.config` (XDG-aware). Les
  variables shell/projet gardent la priorité. Permet de définir une
  fois `S2_API_KEY`, `RESEARCH_CONTACT_EMAIL`, `RESEARCH_VAULT_PATH`
  et de les voir s'appliquer à tous les projets sans recopier dans
  chaque `.env`.

### Changed

- **`INSTALL.md` réécrit.** Section explicite « Install the
  `paper-search` MCP » avec la commande exacte (`uv venv` + git URL +
  `claude mcp add`) et un avertissement contre PyPI obsolète (13 outils
  au lieu de 63 sur git HEAD). Section troubleshooting (No executables,
  ModuleNotFoundError pypdf, TypeError max_results, MCP non listé).
  Section config globale `~/.config/paper-trail/env` pour secrets
  réutilisables.
- **`README.md`.** Tableau MCP refondu : paper-search marqué
  **Required**, lien direct vers la recette d'install. Section Quick
  start mise à jour avec la config globale et la commande de vérif
  `pipeline preflight`.
- **Skill `sota-writer`.** Étape pré-vol mandatoire avant phase A.
  Signatures correctes documentées (`max_results_per_source`, pas
  `max_results`) pour éviter le TypeError au premier appel.
- **Commande `/paper-trail:new-sota`.** Étape 0 ajoutée : invoque
  `pipeline preflight` avant de lancer le sota-writer ; halte +
  recette si le MCP n'est pas enregistré.
- **`ConfigError` plus utile.** Le message liste les trois options
  (shell, `~/.config/paper-trail/env`, `.env` de projet) au lieu de la
  seule variable shell.

## [0.3.8] — 2026-06-06

Retours terrain d'un projet tiers utilisant le plugin sur un layout flat
non-Obsidian : six bugs corrigés (portabilité, robustesse cascade,
validation page 1, UX).

### Fixed

- **I21 + hook pre-save : compatibles layout flat.** La détection de
  citation texte libre ne reconnaissait que les wikilinks Obsidian
  `[[slug]]` et levait à tort sur les SOTAs flat (citations légitimes
  au format `[texte](refs/slug.md)`). La regex accepte maintenant les
  deux formes.
- **`sota_sync` hors repo git.** `arbitrate` échouait à chaque appel
  avec « git backup pre-flight failed » quand le vault n'était pas
  versionné. Par défaut : skip propre avec WARN ; comportement strict
  opt-in via `RESEARCH_REQUIRE_GIT=1`.
- **`arbitrate reject-pdf` cohérent avec I5/I6.** La transition met la
  fiche en `needs_reacquisition` après avoir effacé `pdf_path`/`pdf_sha256`,
  mais ce state était dans `STATES_WITH_PDF` → I5/I6 levaient ensuite.
  Retiré du set : ce state signifie « PDF inutilisable, en attente de
  réacquisition », pas de PDF actif attendu.
- **Page 1 anti-homonymie plus discriminante.** Cinq cas remontés
  d'homonymes acceptés dans le même domaine (Dudley 1939 Vocoder vs
  Morise 2016 WORLD, Schwarz 2007 vs Einbond 2016…). Seuil distinctif
  adaptatif (1 hit pour 1-2 mots, 2 pour 3-4, 3 pour 5+) ; gate
  secondaire 60 % au lieu de 50 % pour les titres ≥5 mots distinctifs.
- **Couvertures de livre.** Roads *Microsound* rejeté car la page 1
  est une couverture sans auteur ni keywords. Fallback : relire jusqu'à
  6 pages avant de conclure à « author_not_in_page1 and no_domain_keywords ».
- **CORE `AttributeError`.** `r.get("fullText", {}).get("url")` cassait
  quand l'API renvoyait `fullText: null`. Remplacé par `r.get("fullText") or {}`.
- **Anna's Archive `md5_found_but_no_dl`.** Cascade DL étoffée :
  pattern d'extraction étendu (`get/?…` en plus de `get.php?…`),
  diagnostic granulaire (`dl_unreachable` vs `dl_validation_failed`),
  fallback `annas-archive.org/md5/<md5>` avant `library.lol`.

### Changed

- **`pipeline run` (mode mono-passe)** suggère explicitement
  `pipeline run --loop` quand au moins une transition a été effectuée,
  pour éviter d'avoir à relancer pour enchaîner les étapes suivantes
  (uid_resolved → pdf_acquired → page1_validated).

### Added

- **`INSTALL.md`** : section listant les MCPs optionnels
  (paper-search, NotebookLM, RTFM) et clarifiant que le plugin
  fonctionne sans, via le fallback REST déjà actif.

## [0.3.7] — 2026-06-06

Sécurité + portabilité : suppression de tout chemin hardcodé et de la
clé API leakée dans le code. Le plugin est désormais utilisable sur
n'importe quelle machine après configuration des variables
d'environnement.

### Security

- **Clé Semantic Scholar retirée du code source.** `lib/s2_resolver.py`
  exposait une clé en clair (commit public). Désormais lue depuis
  `S2_API_KEY` (env var). **La clé précédente doit être révoquée côté
  Semantic Scholar.**

### Changed (breaking pour les installations existantes)

- **`pipeline/config.py`** : suppression de `_DEFAULT_VAULT` (le chemin
  `/mnt/d/Obsidian/Articles/Projets/Ontologie musicale`). Si
  `RESEARCH_VAULT_PATH` n'est pas défini, le plugin lève `ConfigError`
  avec un message d'aide explicite au lieu de retomber silencieusement
  sur un chemin tiers.
- **`lib/s2_resolver.py`** : `STATUS_JSON`, `MD_PATH`, `OBSIDIAN_ROOT`
  dérivés du vault configuré au lieu d'être hardcodés. `EMAIL`
  paramétrable via `RESEARCH_CONTACT_EMAIL`.
- **`PROJECT_AUTHORS`** : whitelist musicology-spécifique externalisée
  vers `~/.config/paper-trail/project_authors.txt` (vide par défaut).
- **`RTFM_DB`** : devient optionnel (env var `RESEARCH_RTFM_DB`). Les
  modules consommateurs (`rtfm_failures`, `ingest`) ignorent
  proprement son absence.
- **`pipeline/tests/test_f1_negative.py`** : test rendu portable
  (skip si la ref de référence n'existe pas, override possible via
  `RESEARCH_F1_NEGATIVE_REF`).

### Added

- **`conftest.py`** à la racine — fournit un défaut neutre
  (`/tmp/paper-trail-test-vault`) pour `RESEARCH_VAULT_PATH` pendant
  pytest, sans contaminer un vault réel.
- **`INSTALL.md`** — documentation complète des variables
  d'environnement, du fichier de whitelist optionnel et de la
  procédure de vérification.

## [0.2.0] — 2026-05-28

Major rework of the INGEST pipeline : split into 4 orthogonal passes
(identify / purge / acquire / linkify) + chronic SOTA ↔ registry
coherence guarantee. Breaking semantic change in the `citation-parser`
sub-agent contract.

### Added

- **`pipeline/sota_sync.py`** — central utility for propagating slug
  mutations (retract, merge) to all SOTAs in the vault. Replaces the
  silent desynchronization where `cmd_arbitrate retract` or
  `cmd_resolve_textbooks merge_into` mutated the registry without
  updating the wikilinks in SOTAs.

- **Automatic sync hook** : `cmd_arbitrate decision=retract`,
  `cmd_resolve_textbooks action=merge_into`, and
  `cmd_retract_uncited --apply` now trigger `update_wikilinks_in_sotas`
  automatically. Invariants I22/I23 become self-healing for future
  mutations.

- **Test suites** : `pipeline/tests/test_sota_sync.py` (9/9 unit),
  `pipeline/tests/test_p2_sync_branchements.py` (2/2 integration).

### Changed

- **`agents/citation-parser.md` v2** (breaking semantic) :
  - Rule 10 (NEW) : `raw` must be a strict literal substring of
    `input_text`. Enrichment of `year`/`title` from context is OK
    but `raw` stays the local short mention.
  - Rule 11 (NEW) : multiple mentions of the same work produce
    multiple records, NOT one. Replaces the old destructive dedup
    rule 3.last ("return ONE record with the most complete mention").
  - Consequence : table cells like `| Younger 1967 |` now produce a
    record with `raw="Younger 1967"` (instead of being absorbed by the
    full citation), enabling wikilink substitution in tables.

- **`pipeline/ingest.py::ingest_citations`** : added validation that
  `cit.raw` is a literal substring of the SOTA text. Mismatch is logged
  in `IngestResult.errors` (not blocking — Tier 2 anchoring still
  catches via fuzzy match).

### Plan refonte INGEST — phases restantes

See `plans/compressed-painting-squid.md` for details.

- P4 — `pipeline/purge.py` + `/paper-trail:purge` (cleanup wikilinks
  invalides : retracted, `_0000_*` orphans, ugly suffixes `_2_3_4`,
  technical paths `20_ATLAS/`, `.canvas`).
- P5 — `pipeline/identify.py` + `pipeline/linkify.py` + idempotent
  `## Statut des sources` section at the bottom of each SOTA.
- P6 — `pipeline/acquire.py` (targeted cascade wrapper).
- P7 — Auto-fix I22/I23 in `pipeline doctor --fix`.
- P8 — `/paper-trail:registry-cleanup` + global invariance tests.

## [0.1.0] — 2026-05-25

First release. Anti-hallucination Claude Code plugin for academic
research. Research-first workflow, strict state machine, 10-source
acquisition cascade, page 1 anti-homonymy validation, per-citation
audit.

### Added

#### Acquisition and validation engine

- **State machine (8 states)**: `candidate`, `uid_resolved`,
  `pdf_acquired`, `awaiting_rtfm_ocr`, `needs_reacquisition`,
  `page1_validated`, `sota_cited_confirmed`, `retracted` (plus
  `blocked_human:*` variants)
- **Acquisition cascade (8 legal sources)**: Crossref OA, arXiv,
  OpenAlex, Unpaywall, HAL, CORE, archive.org, WebSearch queue
- **Two shadow libraries opt-in**: Sci-Hub and Anna's Archive
  activated only via `RESEARCH_ENABLE_SHADOW_LIBS=1` (see
  `DISCLAIMER.md`)
- **Page 1 anti-homonymy validation**: required before accepting any
  downloaded PDF (expected author, title similarity ≥ 0.3, zero
  off-domain keywords)
- **19 mechanical invariants** (I1-I19) with safe auto-fix for
  cosmetic drift (I4, I6, I9, plus I5/I7 semi)
- **WorkerLock** (`fcntl`) to prevent concurrent mutating sessions
- **Per-source circuit breakers** with open-after-N-failures logic
- **Post-write validation** on every registry save (immediate
  rejection if YAML corrupts)
- **JSONL event log** with `pipeline events --since DATE --to STATE`
- **RTFM bridge** for OCR integration and failure correlation

#### Claude Code plugin layer

- **6 skills**: `pdf-cascade`, `registry-doctor`, `sota-writer`,
  `sota-auditor`, `citation-receipts`, `paper-writer`
- **9 slash commands**: `/paper-trail:status`, `:cascade`, `:doctor`,
  `:reactivate-ocr`, `:new-sota`, `:audit-sota`, `:audit-article`,
  `:receipts`, `:new-paper`
- **4 sub-agents**: `cascade-runner`, `page1-validator`, `researcher`,
  `claim-checker`
- **3 hooks**: `PreToolUse` (refuses writing a SOTA citing
  unvalidated references), `PostToolUse` (mini consistency check on
  edited reference), `SessionEnd` (full consistency sweep)
- **3 vault adapters**: `obsidian` (default), `flat`, `zotero` (V2
  stub)
- **5 Python utilities**: `reset_registry.py`, `identify_pdfs.py`,
  `citation_audit.py`, `precheck_sota_wikilinks.py`,
  `reinject_legacy_blocked.py`
- **Mechanical coverage guard** (`assert_coverage.py`) refuses to
  ship a new version without explicit test evidence for each
  component (4 fixes + 19 invariants + 6 skills)
- **Configuration via environment variables**: `RESEARCH_VAULT_PATH`,
  `RESEARCH_SOURCES_PATH`, `RESEARCH_REGISTRY_PATH`,
  `RESEARCH_VAULT_LAYOUT`, `RESEARCH_ENABLE_SHADOW_LIBS`,
  `RESEARCH_ENABLE_NOTEBOOKLM`, `RESEARCH_SKIP_END_DOCTOR`

#### Documentation

- README with quick start and architecture overview
- `docs/USAGE.md` — daily workflows
- `docs/ARCHITECTURE.md` — system diagrams (Mermaid)
- `docs/LEGAL.md` — licensing and attribution detail
- `DISCLAIMER.md` — shadow libraries opt-in policy and jurisdictional
  responsibilities
- `NOTICE.md` — third-party attribution
- `CHANGELOG.md`

### Inspiration patterns (no code copied)

- [`paper-fetch`](https://github.com/Agents365-ai/paper-fetch) (MIT):
  stable JSON output format, file naming convention
- [`receipts`](https://github.com/JamesWeatherhead/receipts) (MIT):
  local PDF↔claim audit pattern, `RECEIPTS.md` format
- [`phd-skills`](https://github.com/fcakyon/phd-skills) (MIT):
  integrity hooks (PreToolUse, PostToolUse, SessionEnd)
- [`claude-knowledge-vault`](https://github.com/Psypeal/claude-knowledge-vault)
  (MIT): YAML frontmatter for Obsidian, Sci-Hub opt-in pattern
- [`academic-research-skills`](https://github.com/Imbad0202/academic-research-skills)
  (CC BY-NC 4.0): research-write-review-revise pipeline architecture
  (**concept only, no code copied**)

See `NOTICE.md` for full attribution.

### Known limitations

- **Zotero adapter**: stub, raises `NotImplementedError`. Planned
  for V0.2.
- **Full ARS-style writing pipeline**: `sota-writer` covers the
  essential research-first workflow but the 10-stage pipeline with
  reviewer/revision/finalize stages is not implemented in V0.1.
- **`paper-search` MCP**: referenced by `sota-writer` and `researcher`
  agent but must be configured by the user in `~/.claude/mcp.json`
  (not bundled with the plugin).
- **WSL2 drvfs**: I/O performance on `/mnt/d/` is noticeably slower
  than native filesystems during large audits.

### Roadmap V0.2

- Full ARS-style writing pipeline (review + revision + finalize)
- Zotero adapter implementation
- Optional bundled `paper-search` MCP alternative
- Enriched RTFM correlation invariants (use `rtfm check --slug -f json`
  for persistent failure flags)
- Automated E2E test suite on representative fixtures

---

[0.1.0]: https://github.com/roomi-fields/paper-trail/releases/tag/v0.1.0
