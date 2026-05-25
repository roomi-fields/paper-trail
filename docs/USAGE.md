# USAGE — paper-trail

Workflows utilisateur du plugin paper-trail au quotidien.

## Sommaire

1. [Installation](#1-installation)
2. [Configuration initiale](#2-configuration-initiale)
3. [Cas A — Créer un nouveau SOTA non halluciné](#3-cas-a)
4. [Cas B — Auditer un SOTA / article existant](#4-cas-b)
5. [Travail quotidien sur le registre](#5-travail-quotidien)
6. [Shadow libraries opt-in](#6-shadow-libraries-opt-in)
7. [Hooks d'intégrité](#7-hooks)
8. [Dépannage](#8-depannage)

---

## 1. Installation

Dans une session Claude Code :

```
/plugin install file:///path/to/paper-trail
```

Ou via marketplace `roomi-fields` (une fois publié) :

```
/plugin marketplace add roomi-fields
/plugin install paper-trail
```

Vérification :

```
/plugin list   # paper-trail v0.1.0 doit apparaître
```

## 2. Configuration initiale

Variables d'environnement (à mettre dans ton shell rc ou
`<project>/.env`) :

```bash
# Chemins du vault (defaults : ~/research_vault et sous-dossiers)
export RESEARCH_VAULT_PATH=/path/to/your/vault
export RESEARCH_SOURCES_PATH=$RESEARCH_VAULT_PATH/sources
export RESEARCH_REGISTRY_PATH=$RESEARCH_SOURCES_PATH/_registry

# Layout du vault (defaults : obsidian)
export RESEARCH_VAULT_LAYOUT=obsidian   # obsidian | flat | zotero (V2)

# Shadow libraries (cf. §6) — opt-in strict
# export RESEARCH_ENABLE_SHADOW_LIBS=1   # à n'activer qu'en connaissance

# Optionnel : NotebookLM intégration
# export RESEARCH_ENABLE_NOTEBOOKLM=1

# Optionnel : skip le SessionEnd doctor (hook)
# export RESEARCH_SKIP_END_DOCTOR=1
```

MCPs externes utilisés (à configurer indépendamment dans
`~/.claude/mcp.json` ou `<project>/.mcp.json`) :

- **`paper-search`** : recherche académique multi-plateforme (utilisé
  par `sota-writer`, `researcher` agent)
- **`notebooklm`** : corpus de livres (optionnel)
- **`rtfm`** : indexation locale (optionnel)

Aucun de ces MCPs n'est inclus dans paper-trail. Le plugin fonctionne
en mode dégradé sans eux.

## 3. Cas A

### Créer un nouveau SOTA garanti sans citations hallucinées

```
/paper-trail:new-sota "Petri nets in music notation"
```

Ce qu'il se passe :

1. **Phase A — Recherche** : `researcher` sub-agent interroge
   `paper-search` MCP sur 22 plateformes, propose N refs candidates
2. **Validation humaine** : tu choisis les candidates pertinentes
3. **Phase B — Acquisition** : `pdf-cascade` skill télécharge les
   PDFs via la cascade 8 sources (ou 10 si shadow opt-in)
4. **Phase C — Lecture** : pour chaque PDF en `page1_validated`, le
   plugin écrit des notes structurées dans le markdown body du fichier
   ref (abstract verbatim, claims principaux, citations verbatim)
5. **Phase D — Rédaction** : production du SOTA citant **uniquement**
   les refs validées. Section finale « Refs écartées » liste les
   candidates rejetées avec raison.

Garde-fous mécaniques :
- Si > 30% des candidates échouent à atteindre `page1_validated`, le
  plugin **refuse d'écrire le SOTA** (signal de sujet trop flou ou
  cascade en panne)
- Le hook `PreToolUse` refuse l'écriture si une citation pointe vers
  une ref non validée

### Avec un domaine spécifique

```
/paper-trail:new-sota "GPT transformers for symbolic music" --max-candidates 20
```

### Pour aller plus loin

Cf. `skills/sota-writer/SKILL.md` pour le détail du workflow 4-phases.

## 4. Cas B

### Auditer un SOTA existant

```
/paper-trail:audit-sota path/to/SOTA_Existing.md
```

Output : rapport classifiant chaque ref citée par état (OK,
TO_VALIDATE, HALLUCINATION, UNKNOWN, INACCESSIBLE).

Avec auto-purge des hallucinations :

```
/paper-trail:audit-sota path/to/SOTA_Existing.md --purge
```

→ Retire les wikilinks vers les refs `retracted`, ajoute une note de
bas listant ce qui a été retiré, sauvegarde dans `.bak`.

### Auditer un article (LaTeX ou Markdown)

Audit par-citation contre les PDFs locaux :

```
/paper-trail:audit-article path/to/Paper.tex
```

Output : `RECEIPTS.md` adjacent au fichier source, classifiant chaque
citation comme VALID / ADJUST / INVALID / UNVERIFIABLE avec evidence.

Avec inline warnings dans `.tex.bak` :

```
/paper-trail:audit-article path/to/Paper.tex --warn
```

→ Insère `\todo[color=red]{REF AUDIT: <verdict> — <reason>}` à côté
des `\cite{key}` douteux.

### Audit local seul (no remote API)

Plus rapide, n'interroge pas `paper-search` / Crossref :

```
/paper-trail:receipts path/to/Paper.tex
```

## 5. Travail quotidien

### Vue d'ensemble du registre

```
/paper-trail:status
```

→ Compte des refs par état FSM (active, waiting, blocked, terminal).

### Audit invariants

```
/paper-trail:doctor
/paper-trail:doctor --severity error      # erreurs seulement
/paper-trail:doctor --fix --severity warn # auto-fix safe
/paper-trail:doctor --correlate-rtfm      # Couche 5 RTFM
/paper-trail:doctor --check-sha           # recompute sha256 (lent)
```

### Acquisition manuelle d'une ref

```
/paper-trail:cascade <slug>           # une ref précise
/paper-trail:cascade --state candidate --limit 50
/paper-trail:cascade --ref <slug> --dry-run
```

### Reprise OCR

Après que RTFM ait fini son indexation OCR sur les `awaiting_rtfm_ocr` :

```
/paper-trail:reactivate-ocr
```

## 6. Shadow libraries opt-in

⚠️ **Lire `DISCLAIMER.md` à la racine avant activation.**

Sci-Hub et Anna's Archive sont désactivés par défaut. Pour activer :

```bash
export RESEARCH_ENABLE_SHADOW_LIBS=1
```

Au premier load de la cascade dans la session, un disclaimer s'affiche
sur stderr.

Toutes les acquisitions via shadow sont préfixées `_optin` dans le
registre (`acquisition_attempts[].via = scihub_optin` ou
`annas_archive_optin`) pour traçabilité.

Activation valide pour la durée du shell parent. Pour désactiver :

```bash
unset RESEARCH_ENABLE_SHADOW_LIBS
```

## 7. Hooks

3 hooks intégrés au plugin :

### PreToolUse (Write|Edit) — bloque les SOTA invalides

Refuse l'écriture/édition d'un fichier `SOTA_*.md` (Obsidian layout)
ou `sotas/*.md` (flat layout) si une citation pointe vers une ref non
validée.

Reasons de blocage :
- Ref absente du registre
- Ref en `candidate`, `uid_resolved`, `pdf_acquired`,
  `needs_reacquisition`, `blocked_human:*`, ou `retracted`

Pour débloquer :
- `/paper-trail:cascade <slug>` pour acquérir la ref manquante
- Ou retirer le wikilink offending du SOTA

### PostToolUse (Write|Edit) — doctor sur ref éditée

Après chaque édit d'un fichier `_registry/refs/*.md`, le plugin lance
un mini-doctor sur cette ref et affiche les warnings en stderr (non
bloquant).

### SessionEnd — doctor final

À la fin de chaque session Claude Code, le plugin lance
`pipeline doctor --severity error` et affiche le récap en stderr.

Skip via `export RESEARCH_SKIP_END_DOCTOR=1`.

## 8. Dépannage

### `/paper-trail:cascade` lance « another pipeline session running »

Le `WorkerLock` empêche les sessions concurrentes. Vérifie qu'aucune
autre session `pipeline run` ne tourne :

```bash
ps aux | grep "pipeline run"
```

Si zombie, le lock se libère automatiquement à la prochaine tentative
(via PID liveness check).

### Le doctor reporte beaucoup d'ERROR I8

I8 = `state_history` non monotone. Probablement effet de migration ou
de mutation manuelle. Auto-fix non disponible (signal structurel).

Investigation : `pipeline doctor --json | jq '.violations[] | select(.invariant=="I8")'`

### Une ref reste en `awaiting_rtfm_ocr` depuis longtemps

RTFM OCR job pending. Vérifier :

```bash
rtfm check --slug <slug> -f json
rtfm failed -f json | jq '.failures[] | select(.filepath | contains("<slug>"))'
```

Si OCR a vraiment échoué : transition manuelle vers
`needs_reacquisition` pour relancer la cascade avec une source texte.

### Cascade tombe systématiquement sur une source

Le breaker per-source ouvre après N=5 échecs consécutifs dans une
fenêtre de 60s. Le worker continue avec les autres sources.

Pour reset : termine la session courante (les breakers sont en mémoire,
non persistés).

### Le plugin ne trouve pas le registre

Vérifier les env vars :

```bash
echo $RESEARCH_VAULT_PATH
echo $RESEARCH_SOURCES_PATH
echo $RESEARCH_REGISTRY_PATH
```

Si non set, les defaults pointent vers
`/mnt/d/Obsidian/Articles/Projets/Ontologie musicale/` (chemins de
développement du projet doctoral). Pour un autre vault, set
`RESEARCH_VAULT_PATH` au minimum.

## Cross-references

- `docs/ARCHITECTURE.md` — vue système du plugin
- `docs/LEGAL.md` — licences et attributions
- `DISCLAIMER.md` — shadow libraries
- `pipeline/USAGE.md` — CLI worker B sous-jacent
- `pipeline/ARCHITECTURE.md` — détail FSM 8 états + cascade
- `plans/PLUGIN_EXECUTION_PLAN.md` — plan de construction du plugin
