# ARCHITECTURE — paper-trail

Vue d'ensemble de l'architecture du plugin Claude Code paper-trail.

## 1. Système global

```mermaid
flowchart TB
    subgraph User["Utilisateur — recherche académique"]
        U["Tape /paper-trail:* ou trigger naturel"]
    end

    subgraph Plugin["paper-trail (plugin Claude Code)"]
        direction TB

        subgraph UX["Couche UX"]
            CMD["9 commands /paper-trail:*"]
            HOOKS["3 hooks<br/>PreToolUse / PostToolUse / SessionEnd"]
        end

        subgraph Skills["6 skills"]
            SW["sota-writer"]
            SA["sota-auditor"]
            CR["citation-receipts"]
            PW["paper-writer"]
            PC["pdf-cascade"]
            RD["registry-doctor"]
        end

        subgraph Agents["4 sub-agents (isolation contexte)"]
            RES["researcher"]
            CC["claim-checker"]
            CR_AGENT["cascade-runner"]
            P1V["page1-validator"]
        end

        subgraph WB["Worker B (moteur Python)"]
            FSM["FSM 8 états + cascade 10 niveaux"]
            DOC["Doctor 19 invariants I1-I19"]
            LOCK["WorkerLock fcntl"]
            BREAK["Circuit-breakers per-source"]
            EVT["Events JSONL"]
        end

        subgraph Lib["Helpers Python"]
            OA["lib/oa_finder.py (Crossref)"]
            S2["lib/s2_resolver.py (Semantic Scholar)"]
            AO["lib/archive_org_helper.py"]
            VPC["lib/validate_pdf_content.py<br/>(anti-homonymie)"]
            SHADOW["lib/shadow/scihub.py<br/>lib/shadow/annas_archive.py<br/>(opt-in via env)"]
        end

        subgraph Adapt["3 adapters layout vault"]
            OBS["obsidian (default)"]
            FLAT["flat"]
            ZOT["zotero (stub V2)"]
        end
    end

    subgraph External["Ressources externes (configurées par l'utilisateur)"]
        MCP_PS["MCP paper-search<br/>(22 plateformes)"]
        MCP_NB["MCP notebooklm (optionnel)"]
        MCP_RTFM["MCP rtfm (optionnel)"]
    end

    subgraph Storage["Données"]
        REG["Registre YAML<br/>$RESEARCH_REGISTRY_PATH/refs/*.md"]
        PDFS["PDFs locaux<br/>$RESEARCH_SOURCES_PATH/**/Sources/*.pdf"]
        SOTAS["SOTAs / Papers<br/>$RESEARCH_VAULT_PATH/SOTA_*.md / sotas/"]
    end

    U --> CMD
    CMD --> Skills
    HOOKS -.surveille.-> SOTAS
    HOOKS -.surveille.-> REG

    SW --> RES
    SW --> PC
    SA --> RD
    CR --> CC
    CR --> PC
    PW --> CR
    PW --> SW

    PC --> WB
    RD --> WB
    CR_AGENT --> WB

    WB --> Lib
    WB --> Adapt
    Adapt --> REG
    Adapt --> SOTAS
    WB <--> REG
    Lib --> PDFS

    RES --> MCP_PS
    RES --> MCP_NB
    WB --> MCP_RTFM

    style WB fill:#d4edda,stroke:#2d6a4f
    style Skills fill:#cce5ff
    style Agents fill:#fff3cd
    style External fill:#e2e3e5
    style Storage fill:#f8d7da
    style Lib fill:#d4edda
```

Couleurs :
- **Vert** : moteur worker B (Python, déterministe)
- **Bleu** : skills Claude Code (orchestration)
- **Jaune** : sub-agents (isolation contexte pour tâches lourdes)
- **Gris** : ressources externes (MCPs configurés par l'utilisateur)
- **Rouge** : données persistées (registre, PDFs, SOTAs)

## 2. Flux principaux

### 2.1 Cas A — Créer un SOTA non halluciné

```mermaid
flowchart LR
    U["Toi : /paper-trail:new-sota 'X'"] --> SW[sota-writer]
    SW -->|Phase A| RES[researcher]
    RES -->|paper-search MCP| LIST["Liste candidates"]
    LIST -->|Choix humain| INGEST["Ingest as candidate refs"]
    INGEST -->|Phase B| PC[pdf-cascade]
    PC --> WB["Worker B :<br/>cascade DL + page 1 validation"]
    WB --> P1[page1_validated refs]
    P1 -->|Phase C| READ["Notes en markdown body de chaque ref"]
    READ -->|Phase D| WRITE["Rédaction SOTA<br/>(wikilinks vers page1_validated)"]
    WRITE -->|Hook PreToolUse| GATE{Tous validés ?}
    GATE -->|oui| OUT["SOTA produit"]
    GATE -->|non| BLOCK["Write bloqué,<br/>refs manquantes signalées"]
```

### 2.2 Cas B — Auditer un SOTA existant

```mermaid
flowchart LR
    U["Toi : /paper-trail:audit-sota ..."] --> SA[sota-auditor]
    SA -->|extrait wikilinks| ADAPTER[Adapter]
    ADAPTER --> CITED["Liste slugs cités"]
    CITED --> REG[(Registre)]
    REG --> CLASS{Classification}
    CLASS -->|sota_cited_confirmed| OK[OK]
    CLASS -->|page1_validated| TV[TO_VALIDATE]
    CLASS -->|retracted| HAL[HALLUCINATION]
    CLASS -->|blocked_human| INACC[INACCESSIBLE]
    CLASS -->|absent| UNK[UNKNOWN]
    HAL -.si --purge.-> PURGE["Retire wikilinks<br/>(dans .bak)"]
    TV -.optionnel.-> CR[citation-receipts]
    CR --> REC["RECEIPTS.md par-citation"]
```

### 2.3 Cas B — Auditer un article (per-citation)

```mermaid
flowchart LR
    U["Toi : /paper-trail:audit-article paper.tex"] --> CR[citation-receipts]
    CR -->|parse| CITES["Liste citations (cite, wikilinks)"]
    CITES --> CC[claim-checker agent]
    CC -->|pdftotext + grep| PDFS[(PDFs locaux)]
    CC -->|match keywords| VERDICT{Verdict}
    VERDICT --> V[VALID]
    VERDICT --> A[ADJUST]
    VERDICT --> I[INVALID]
    VERDICT --> UV[UNVERIFIABLE]
    V --> REC
    A --> REC
    I --> REC
    UV --> REC
    REC[RECEIPTS.md]
    REC -.si --warn.-> BAK["paper.tex.bak<br/>avec todo inline"]
```

## 3. FSM worker B (8 états)

Voir `pipeline/ARCHITECTURE.md` pour le diagramme détaillé. Résumé :

```
candidate → uid_resolved → pdf_acquired → page1_validated → sota_cited_confirmed
                              ↓                                  ↑
                          awaiting_rtfm_ocr ──────────────────→
                              ↓
                          needs_reacquisition → uid_resolved (retry)

* → blocked_human:* (à n'importe quel niveau, décision humaine requise)
* → retracted (terminal, hallucination confirmée)
```

## 4. Cascade d'acquisition (10 sources)

```
1. Crossref OA       — DOI-based, métadonnées OA
2. arXiv             — preprints CS/math/physics/etc.
3. OpenAlex          — agrégateur cross-domaine
4. Unpaywall         — OA discovery
5. HAL               — Hyper Articles en Ligne (French academic)
6. CORE              — UK-based open repository aggregator
7. archive.org       — digitized books
(7.5 Sci-Hub_optin   — opt-in via RESEARCH_ENABLE_SHADOW_LIBS=1)
(7.6 AA_optin        — opt-in via RESEARCH_ENABLE_SHADOW_LIBS=1)
8. WebSearch queue   — fallback manuel
```

Chaque source retourne `success` / `page1_failed` / `failed` /
`no_source`. La cascade s'arrête au premier `success` ou au `failed`
final (toutes sources épuisées).

Page 1 validation anti-homonymie obligatoire avant `success` :
- Auteur attendu présent
- Similarité titre ≥ 0.3 (keywords distinctifs)
- Zéro keywords off-domain

## 5. Doctor — 19 invariants

| Catégorie | Invariants |
|---|---|
| Frontmatter formel | I1 (state valid), I2 (slug unique), I3 (uid prefix) |
| Cohérence PDF | I4 (pdf_path normalisé), I5 (PDF existe), I6 (sha256 valide), I18 (sha drift, Couche 5) |
| Cohérence FSM | I7 (page1 log), I8 (state_history monotonique), I14 (no exit terminal) |
| Audit | I9 (attempts num), I10 (blocked reason), I15 (OCR overdue) |
| Cohérence SOTAs | I11 (cited_in existe), I12 (réciprocité) |
| Doublons | I13 (sha256 unique) |
| RTFM (Couche 5) | I16 (RTFM failure miroir), I17 (PDF format défectueux), I19 (PDF image-only) |

Auto-fix : I4, I6, I9 (cosmétique) + I5, I7 semi (transition vers
`needs_reacquisition`).

## 6. Adapter pattern

L'adapter résout les conventions vault-spécifiques sans hardcoder
Obsidian dans le code.

```python
class Adapter(ABC):
    def index_md_files(self) -> set[str]: ...    # pour I11
    def find_sotas(self) -> list[Path]: ...      # pour I12
    def parse_citations(self, sota_path) -> list[str]: ...
    def sota_output_path(self, topic_slug) -> Path: ...
    def format_citation(self, slug) -> str: ...
```

3 implémentations :
- **Obsidian** (default) : wikilinks `[[slug]]`, SOTAs en `SOTA_*.md`
- **Flat** : Markdown links `[text](refs/slug.md)`, SOTAs sous `sotas/`
- **Zotero** : stub V2

Switch via `RESEARCH_VAULT_LAYOUT=obsidian|flat|zotero`.

## 7. Hooks d'intégrité

| Hook | Matcher | Action |
|---|---|---|
| `PreToolUse` Write\|Edit | SOTA files | Refuse l'écriture si refs cités non validés |
| `PostToolUse` Write\|Edit | `**/refs/*.md` | Mini-doctor sur ref éditée (warn-level) |
| `SessionEnd` | (toutes) | `pipeline doctor --severity error` |

Tous non-bloquants sauf le `PreToolUse` SOTA (philosophie
anti-hallucination du plugin).

## 8. Configuration

Variables d'environnement (par-priorité, voir `pipeline/config.py`) :

| Var | Défaut | Usage |
|---|---|---|
| `RESEARCH_VAULT_PATH` | `~/research_vault` | Racine vault |
| `RESEARCH_SOURCES_PATH` | `$VAULT/sources` | Dossier PDFs |
| `RESEARCH_REGISTRY_PATH` | `$SOURCES/_registry` | Registre YAML |
| `RESEARCH_VAULT_LAYOUT` | `obsidian` | Adapter |
| `RESEARCH_ENABLE_SHADOW_LIBS` | (non) | AA + Sci-Hub |
| `RESEARCH_ENABLE_NOTEBOOKLM` | (non) | NotebookLM dans sota-writer phase A |
| `RESEARCH_SKIP_END_DOCTOR` | (non) | Skip SessionEnd hook |

## 9. Cross-references

- `pipeline/ARCHITECTURE.md` — détail worker B (FSM, cascade, doctor)
- `plans/PLUGIN_EXECUTION_PLAN.md` — plan de construction
- `plans/SYSTEM_ARCHITECTURE.md` — vision système doctorale
- `NOTICE.md` — attributions
- `DISCLAIMER.md` — shadow libraries
