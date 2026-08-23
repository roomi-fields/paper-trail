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

Lancement (l'acquisition hebdomadaire, par exemple) :

```bash
xvfb-run -a --server-args="-screen 0 1400x1000x24" \
    python -m pipeline run --loop --retry-exhausted
```

`xvfb-run -a` choisit un numéro d'affichage libre : plusieurs travaux
peuvent cohabiter sans se marcher dessus.

## Points d'attention en conteneur

- **`--no-sandbox`** est déjà passé par la source (obligatoire pour
  Chromium dans un conteneur non privilégié).
- **`/dev/shm`** : Docker alloue 64 Mo par défaut, ce qui fait planter
  Chromium sur des pages lourdes. Lancer avec `--shm-size=1g`.
- **Mémoire** : compter ~500 Mo pour Chromium + Xvfb en plus du pipeline.
- **Durée** : les créneaux « slow download » imposent une vingtaine de
  secondes d'attente par tentative ; prévoir ~2 min par référence et un
  délai généreux pour un travail planifié.
- **Contingentement** : au-delà de quelques dizaines de fichiers par
  session, les créneaux se raréfient. Avec le correctif `retry_after`,
  les refs concernées repartent d'elles-mêmes à la passe suivante — d'où
  l'intérêt d'une planification récurrente plutôt que d'une passe unique.
- **Vérification rapide** que l'environnement est bon :

```bash
xvfb-run -a python -c "from lib.shadow.annas_headful import available; print(available())"
# attendu : (True, 'ok')
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
