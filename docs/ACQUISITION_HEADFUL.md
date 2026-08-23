# Où faire tourner l'acquisition Anna's Archive (source `annas_headful`)

Réponse courte : **dans n'importe quel conteneur sans écran**, à condition
d'y installer un *affichage virtuel*. Aucune machine de bureau, aucun écran
physique, aucune session graphique utilisateur ne sont nécessaires.

## Le point contre-intuitif

Le mode « sans interface » de Chromium **ne fonctionne pas** pour cette
source, alors qu'il franchit pourtant le challenge anti-robot :

| Étape | headless | headful sous Xvfb |
|---|---|---|
| Page `/scidb/` ou `/md5/` (DDoS-Guard) | ✅ passe | ✅ passe |
| Lien partenaire obtenu | ✅ | ✅ |
| **Téléchargement du fichier** | ❌ **502** systématique | ✅ **PDF valide** |

C'est le *serveur de fichiers partenaire* qui refuse, pas le site. Il faut
donc un navigateur réellement fenêtré — mais la fenêtre peut s'ouvrir dans
un framebuffer en mémoire (Xvfb), invisible et sans matériel graphique.

## Recette conteneur (Debian/Ubuntu)

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
      xvfb \
      libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
      libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
      libgbm1 libasound2 fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

RUN pip install playwright && playwright install chromium
```

Les noms de paquets système changent d'une version de distribution à
l'autre (`libasound2` est devenu `libasound2t64` sur les plus récentes).
Pour éviter d'avoir à suivre ces renommages, Playwright sait installer
lui-même ce dont le navigateur a besoin — il reste alors uniquement `xvfb`
à ajouter à la main :

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends xvfb \
 && rm -rf /var/lib/apt/lists/*
RUN pip install playwright && playwright install --with-deps chromium
```

Lancement (l'acquisition hebdomadaire, par exemple) :

```bash
RESEARCH_ENABLE_SHADOW_LIBS=1 \
xvfb-run -a --server-args="-screen 0 1400x1000x24" \
    python -m pipeline run --loop
```

**`RESEARCH_ENABLE_SHADOW_LIBS=1` n'est pas optionnel** : sans lui, ni cette
source ni les autres sources étendues n'entrent dans la cascade — le travail
tourne sans erreur et sans jamais utiliser le navigateur. Cf. `DISCLAIMER.md`
sur ce que cette activation engage.

`xvfb-run -a` choisit un numéro d'affichage libre : plusieurs travaux
peuvent cohabiter sans se marcher dessus.

`--retry-exhausted` (voir plus bas) est délibérément absent de cette
commande : c'est un geste ponctuel, pas un réglage de planification.

## Points d'attention en conteneur

- **`--no-sandbox`** est déjà passé par la source (obligatoire pour
  Chromium dans un conteneur non privilégié).
- **`/dev/shm`** : Docker alloue 64 Mo par défaut, ce qui fait planter
  Chromium sur des pages lourdes. Lancer avec `--shm-size=1g`.
- **Mémoire** : compter ~500 Mo pour Chromium + Xvfb en plus du pipeline.
- **Durée** : les créneaux « slow download » imposent une vingtaine de
  secondes d'attente par tentative, et la source essaie quatre créneaux
  par miroir. Compter ~2 min par référence dans le cas favorable, mais
  jusqu'au budget par référence quand les créneaux sont saturés :
  `RESEARCH_ANNAS_HEADFUL_BUDGET_S`, **600 s par défaut**. Dimensionner le
  délai du travail planifié sur ce budget multiplié par le nombre de refs
  susceptibles d'arriver jusqu'à cette source, pas sur les 2 min.
- **Contingentement** : au-delà de quelques dizaines de fichiers par
  session, les créneaux se raréfient. Une référence qui n'a rencontré que
  des indisponibilités passagères n'est pas verrouillée : elle reçoit une
  date de reprise (15 min au premier échec, doublée à chaque fois,
  plafonnée à 8 h) et le pipeline l'ignore jusque-là. Elle ne repart donc
  pas à la passe suivante, mais à la première passe postérieure à cette
  date — d'où l'intérêt d'une planification récurrente plutôt que d'une
  passe unique.
- **`--retry-exhausted`** lève les verrous d'épuisement de cascade posés
  automatiquement, pour que les références concernées soient réessayées.
  À réserver aux reprises ponctuelles — après l'ajout d'une source, par
  exemple. Dans un travail récurrent, il relance la cascade complète, à
  chaque exécution, sur des références dont l'épuisement a déjà été
  constaté ; les verrous posés par une personne ne sont pas touchés.
- **Vérification rapide** que l'environnement est bon :

Depuis la racine du plugin (aucune variable d'environnement n'est
nécessaire pour ce seul test) :

```bash
xvfb-run -a python -c "from lib.shadow.annas_headful import available; print(available())"
# attendu : (True, 'ok')
# sans affichage : (False, 'no_display_run_under_xvfb')
# sans Playwright : (False, 'playwright_not_installed')
```

Sans affichage ni Playwright, la source se déclare simplement indisponible
et la cascade continue sans elle : le pipeline reste fonctionnel, il perd
seulement cette source.

## Alternative sans conteneur graphique

Si la politique d'exploitation interdit d'installer un navigateur en
production, l'acquisition peut tourner ailleurs (poste de travail, machine
d'administration, conteneur dédié) sur le **même registre partagé** : la
source écrit les PDF dans `RESEARCH_SOURCES_PATH` et met à jour les fiches.
La production n'a alors qu'à lire le registre.
