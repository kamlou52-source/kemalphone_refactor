
# EL Kémal Phone Solutions

Application Flask simple pour collecter des demandes de réparation de smartphones (Android / iOS), visualiser des **statistiques**, offrir une **connexion rapide par QR code** et un **assistant virtuel** qui présente ce README progressivement.

## Fonctionnalités
- Formulaires Android/iOS avec validation front/back.
- Stockage SQLite via SQLAlchemy (`userinput`).
- Page d'**historique** des demandes.
- **Statistiques** (Chart.js) : modèles et problèmes fréquents.
- **Contact** + QR code pointant vers une URL de connexion rapide.
- **Assistant** : tableau qui déroule le README ligne par ligne + mini coach IT.

## Structure du projet au commencement
```
kemalphone_refactor/
├── app.py
├── README.md
├── templates/
│   ├── base.html
│   ├── indexkemalphones.html
│   ├── androidapp.html
│   ├── iOSapp.html
│   ├── userinput.html
│   ├── stats.html
│   └── contactus.html
└── static/
    ├── css/
    │   └── style.css
    ├── js/
    │   └── main.js
    └── img/
```
### Structure après débuggue du projet
kemalphone_refactor/
├─ app.py                        # App Flask (routes, modèles, i18n, mail, PDF…)
├─ requirements.txt              # Dépendances Python
├─ README.md                     # Guide (install, debug, routes)
├─ .env                          # Variables d'env (DATABASE_URL, SECRET_KEY, MAIL_*)
├─ .flaskenv                     # (optionnel) FLASK_APP=app.py, FLASK_ENV=development
├─ .gitignore                    # (recommandé) ignore .venv, __pycache__, etc.
├─ docker-compose.yml            # (optionnel) services db, mailhog, adminer, app
├─ Dockerfile                    # (optionnel) image de l’app Flask
│
# EL Kémal Phone Solutions — Guide pédagogique & Déploiement

Ce dépôt contient une application Flask pour collecter des demandes de réparation de smartphones (Android / iOS), gérer la facturation et fournir un mini-assistant qui lit le README.

Ce document met l'accent sur : installation pas-à-pas, aspects pédagogiques (explications pour apprentis), bonnes pratiques de sécurité, et automatisation du déploiement vers GitHub / GHCR.

**But pédagogique** : permettre à un développeur junior de comprendre l'architecture d'une application Flask simple, de la config locale à l'automatisation CI/CD, tout en appliquant des règles de sécurité réutilisables pour d'autres projets.

**À propos de l'intégration `anthropics/security-guidance`**
- **Option recommandée (sous-module)** : on conserve la copie officielle et les mises à jour séparément.
   - Ajouter comme sous-module git :
      ```bash
      git submodule add https://github.com/anthropics/security-guidance third_party/security-guidance
      git submodule update --init --remote
      ```
   - Consulter les recommandations sous `third_party/security-guidance/` et intégrer les checklists dans votre pipeline de revue.

**Structure concise du projet**
Voir l'arborescence du dépôt (racine) :
```
app.py
requirements.txt
README.md
.env.example
Dockerfile
docker-compose.yml
templates/
static/
sql/
tests/
```

**1) Prérequis & installation (pas-à-pas)**
- **Système** : Linux / macOS recommandé pour la facilité.
- **Python** : 3.10+ (3.11 recommandé)

Installation locale :
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
export FLASK_APP=app.py
flask run
# Visiter: http://127.0.0.1:5000
```

Base de données (option SQLite par défaut, ou PostgreSQL en prod) : adapter `DATABASE_URL` dans `.env`.

**2) Sécurité — checklist pédagogique**
- **Secrets** : ne jamais committer `.env` ni le `SECRET_KEY`. Utiliser GitHub Secrets pour CI/CD.
- **Validation** : valider côté serveur toutes les données reçues depuis les formulaires.
- **Authentification QR** : utiliser des tokens signés (ex : JWT ou sa signature HMAC) et expirés.
- **HTTPS** : forcer TLS en production (reverse proxy ou plateforme).
- **Dépendances** : auditer avec `pip-audit` ou `safety` (voir automatisation ci-dessous).

Installation rapide des outils d'audit (optionnel) :
```bash
pip install pip-audit safety
pip-audit
```

**3) Intégration de `anthropics/security-guidance`**
- Après l'ajout en sous-module, lire la checklist et appliquer les règles suivantes dans votre CI :
   - Scans statiques (bandit/flawfinder), linting (flake8), tests unitaires.
   - Exiger review et tests verts avant merge.

**4) Tests & qualité**
```bash
pip install -r requirements.txt
pip install pytest
pytest -q
```
Recommandé : ajouter `pre-commit` et règles (black, isort, flake8).

**5) Automatisation GitHub — CI & publication**
Deux workflows exemplaires sont fournis :
- `CI` : tests, lint, sécurité légère
- `publish-ghcr` : build Docker image et push vers GHCR (GitHub Container Registry)

Ces workflows utilisent les secrets GitHub suivants (à définir dans le dépôt cible `https://github.com/Kamilou52/<repo>`):
- `GHCR_PAT` (optionnel) — token pour publier sur `ghcr.io` (GITHUB_TOKEN peut suffire pour actions dans le même repo)
- `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` (optionnel) — pour Docker Hub

Exemple : créer le remote et pousser vers votre compte GitHub
```bash
# Remplacez <repo> par le nom du repo souhaité
git remote add origin https://github.com/Kamilou52/<repo>.git
git branch -M main
git push -u origin main
```

**6) Template d'automatisation pour l'ensemble des projets**
- Centraliser un dossier `devops/` dans chaque projet contenant :
   - `devops/ci.yml` (base CI)
   - `devops/publish.yml` (build & publish)
   - `devops/README_AUTOMATION.md` (notes et checklist)
- Réutiliser le même `third_party/security-guidance` comme sous-module pour tous les projets.

**7) Notes pour le déploiement vers `https://github.com/Kamilou52`**
- Créer un dépôt sur GitHub (nom du repo), ajouter en remote et push (commande ci‑dessus).
- Activer Actions & ajouter les secrets nécessaires dans Settings → Secrets and variables → Actions.

**8) Fichiers ajoutés**
- Workflow CI : [/.github/workflows/ci.yml](.github/workflows/ci.yml)
- Workflow publication GHCR : [/.github/workflows/publish-ghcr.yml](.github/workflows/publish-ghcr.yml)

**9) Bonnes pratiques pédagogiques (pour enseignants / code review)**
- Expliquer chaque PR par étapes : but, what changed, tests run, commands to reproduce.
- Documenter les choix de sécurité importante dans `SECURITY.md` (ex: token expiry, CSP, rate limiting).
- Faire des exercices : ajouter un GH Action qui simule une faille et demander aux élèves d'appliquer la checklist.

---

Si vous voulez, j'appliquerai maintenant ces changements en créant les workflows et en ajoutant le sous-module `third_party/security-guidance` (si vous confirmez). Je peux aussi créer un template `devops/` réutilisable pour tous vos projets.
docker-compose up --build

