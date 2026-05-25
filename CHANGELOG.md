# Changelog — paper-trail

All notable changes to the paper-trail plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-25

First release. Plugin Claude Code anti-hallucination pour la recherche
scientifique. Workflow inversé (research → acquire → read → write),
machine d'état stricte (FSM 8 états + 19 invariants), cascade
d'acquisition PDF 8 sources (10 avec shadow libs opt-in), audit
par-citation, publication multi-domaine.

### Added

#### Worker B — moteur d'acquisition et validation (Couches 1-5 livrées)

- **FSM 8 états** : `candidate`, `uid_resolved`, `pdf_acquired`,
  `awaiting_rtfm_ocr`, `needs_reacquisition`, `page1_validated`,
  `sota_cited_confirmed`, `retracted` (+ variants `blocked_human:*`)
- **Cascade 8 sources légales** (Crossref OA, arXiv, OpenAlex,
  Unpaywall, HAL, CORE, archive.org, WebSearch queue) + **2 sources
  shadow opt-in** (Sci-Hub, Anna's Archive via
  `RESEARCH_ENABLE_SHADOW_LIBS=1`)
- **Page 1 validation anti-homonymie** obligatoire (auteur, titre,
  zéro keywords off-domain) avant acceptation d'un PDF
- **19 invariants doctor** I1-I19 avec auto-fix sur les invariants
  safe (I4, I6, I9, I5/I7 semi)
- **WorkerLock fcntl** pour empêcher les sessions concurrentes
- **Circuit-breakers per-source** avec ouverture après N échecs
- **Post-write validation** sur tous les `save_ref()` (rejet immédiat
  si YAML corrompu)
- **Events JSONL** + commande `pipeline events --since DATE --to STATE`
  pour audit trail
- **RTFM bridge** pour OCR + corrélation des échecs (Couche 5
  invariants I16-I19)

#### Plugin Claude Code

- **6 skills** : `pdf-cascade`, `registry-doctor`, `sota-writer`,
  `sota-auditor`, `citation-receipts`, `paper-writer`
- **9 commands** : `/paper-trail:status`, `:cascade`, `:doctor`,
  `:reactivate-ocr`, `:new-sota`, `:audit-sota`, `:audit-article`,
  `:receipts`, `:new-paper`
- **4 sub-agents** : `cascade-runner`, `page1-validator`,
  `researcher`, `claim-checker`
- **3 hooks** : `PreToolUse` (refuse l'écriture d'un SOTA citant des
  refs non validées), `PostToolUse` (doctor sur ref éditée),
  `SessionEnd` (doctor final)
- **3 adapters** : `obsidian` (default), `flat`, `zotero` (stub V2)
- **5 outils Python** : `reset_registry.py`, `reinject_legacy_blocked.py`,
  `identify_pdfs.py`, `citation_audit.py`,
  `precheck_sota_wikilinks.py`
- **Configuration par env vars** : `RESEARCH_VAULT_PATH`,
  `RESEARCH_SOURCES_PATH`, `RESEARCH_REGISTRY_PATH`,
  `RESEARCH_VAULT_LAYOUT`, `RESEARCH_ENABLE_SHADOW_LIBS`,
  `RESEARCH_ENABLE_NOTEBOOKLM`, `RESEARCH_SKIP_END_DOCTOR`

#### Sécurité et légalité

- **Anna's Archive et Sci-Hub désactivés par défaut**, activation
  opt-in strict via variable d'environnement
- **DISCLAIMER.md** documentant les implications juridictionnelles
- **Disclaimer stderr** au premier appel de session quand shadow
  activé
- **Traçabilité** : toutes les acquisitions via shadow sont préfixées
  `_optin` dans `acquisition_attempts[].via`

### Migrated from upstream projects

- `skills/sota-writer/` migré depuis `~/musicology-phd/.claude/skills/sota-writer/`
  (220 LOC, généralisé multi-domaines)
- `skills/sota-auditor/` migré depuis `sota-curator/` (249 LOC,
  renommé pour cohérence)
- `skills/citation-receipts/` migré depuis `citation-verification/`
  (171 LOC, enrichi format RECEIPTS.md inspiré du plugin receipts MIT)
- `skills/paper-writer/` migré (67 LOC, généralisé)
- `agents/researcher.md` dérivé de `corpus-explorer/` (skill → agent)
- `tools/notebooklm-integration.md` dérivé de `notebooklm-manager/`
- `tools/citation_audit.py` généralisation de
  `~/musicology-phd/scripts/verify_claims.py` +
  `validate_claims_s2.py` (paramétrable par fichier source .tex ou .md)
- `lib/oa_finder.py`, `lib/s2_resolver.py`, `lib/archive_org_helper.py`,
  `lib/validate_pdf_content.py`, `lib/download_books.py` copiés depuis
  le plugin source-collector pour self-containment

Cf. `NOTICE.md` pour les attributions détaillées.

### Inspiration patterns (no code copied)

- [`paper-fetch`](https://github.com/Agents365-ai/paper-fetch) (MIT) :
  format de sortie JSON, convention de nommage fichier
- [`receipts`](https://github.com/JamesWeatherhead/receipts) (MIT) :
  pattern audit local PDF↔claim, format RECEIPTS.md
- [`phd-skills`](https://github.com/fcakyon/phd-skills) (MIT) : hooks
  d'intégrité PostToolUse/PreToolUse/SessionEnd
- [`claude-knowledge-vault`](https://github.com/Psypeal/claude-knowledge-vault)
  (MIT) : YAML frontmatter Obsidian, Sci-Hub opt-in pattern
- [`academic-research-skills`](https://github.com/Imbad0202/academic-research-skills)
  (CC BY-NC 4.0) : pipeline 10-stages writing **(concept only, no code
  copied)**

### Known limitations

- **Adapter Zotero** : stub V2, lève `NotImplementedError` clean
- **Pipeline writing complet à la ARS** : sota-writer livre l'essentiel
  (research → acquire → read → write inversé), mais le pipeline 10-stages
  avec review/revision/finalize d'ARS n'est pas implémenté en V0.1
- **`paper-search` MCP** : référencé dans les skills mais doit être
  configuré par l'utilisateur dans son `~/.claude/mcp.json` (pas
  inclus dans le plugin)
- **WSL2 drvfs** : performances I/O moyennes sur `/mnt/d/` (latence
  notable lors des audits massifs)

### Roadmap V0.2

- Pipeline writing 10-stages complet (review + revision + finalize)
- Adapter Zotero implémenté
- MCP server paper-trail custom (alternative à paper-search externe)
- I16-I19 enrichis (corrélation RTFM ocr_failure_reason via `rtfm check --slug`)
- Tests E2E automatisés sur fixtures plus exhaustives

---

[0.1.0]: https://github.com/roomi-fields/paper-trail/releases/tag/v0.1.0
