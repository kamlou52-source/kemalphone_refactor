# Gestion d'environnements Python — 7+ projets sur Linux

## Stack recommandée : pyenv + uv + direnv

| Outil    | Rôle                                              |
|----------|---------------------------------------------------|
| `pyenv`  | Gérer plusieurs versions Python (3.10, 3.11, 3.12…) |
| `uv`     | Remplaçant ultra-rapide de pip+virtualenv+pip-tools  |
| `direnv` | Activer automatiquement le bon venv en entrant dans un dossier |

---

## 1 — Installer pyenv

```bash
# Dépendances build
sudo apt update && sudo apt install -y \
  build-essential libssl-dev zlib1g-dev libbz2-dev \
  libreadline-dev libsqlite3-dev libncursesw5-dev \
  xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

# Installer pyenv
curl https://pyenv.run | bash

# Ajouter dans ~/.bashrc (ou ~/.zshrc)
echo '
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc

source ~/.bashrc
```

### Utilisation pyenv

```bash
# Lister les versions dispo
pyenv install --list | grep "3\.1[0-9]"

# Installer les versions dont vous avez besoin
pyenv install 3.11.9
pyenv install 3.12.4

# Définir la version globale par défaut
pyenv global 3.11.9

# Forcer une version dans UN projet (crée un .python-version)
cd ~/projets/kemalphone
pyenv local 3.11.9

# Vérifier
python --version   # → Python 3.11.9
```

---

## 2 — Installer uv (remplace pip + venv + pip-tools)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version
```

`uv` est 10–100× plus rapide que pip. Il gère aussi les lock files.

### Workflow uv par projet

```bash
cd ~/projets/kemalphone

# Créer un venv avec la bonne version Python
uv venv .venv --python 3.11

# Installer depuis requirements.txt existant
uv pip install -r requirements.txt

# Installer un package et l'ajouter à requirements.txt
uv pip install flask
uv pip freeze > requirements.txt

# Meilleure pratique : utiliser pyproject.toml + uv lock
uv init          # crée pyproject.toml si absent
uv add flask sqlalchemy flask-mail    # ajoute + installe
uv add --dev pytest black ruff        # dépendances dev
uv lock                               # génère uv.lock (reproductible)
uv sync                               # installe exactement ce qui est dans uv.lock
```

### Migrer un projet existant (requirements.txt → uv)

```bash
cd ~/projets/monprojet

# 1. Créer l'env
uv venv .venv --python 3.11
source .venv/bin/activate

# 2. Installer l'existant
uv pip install -r requirements.txt

# 3. Générer un lock file propre
uv pip compile requirements.txt -o requirements.lock

# Désormais les collègues/CI font :
uv pip sync requirements.lock   # installation exacte garantie
```

---

## 3 — Installer direnv (activation automatique du venv)

Sans direnv, vous devez taper `source .venv/bin/activate` à chaque fois.
Avec direnv, c'est automatique dès que vous entrez dans le dossier.

```bash
sudo apt install direnv

# Ajouter dans ~/.bashrc
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
source ~/.bashrc
```

### Configurer chaque projet

```bash
cd ~/projets/kemalphone

# Créer le fichier .envrc
cat > .envrc << 'EOF'
# Active le venv Python
source .venv/bin/activate

# Charge les variables d'env depuis .env
dotenv .env
EOF

# Autoriser direnv pour ce dossier
direnv allow .
```

Résultat : dès que vous faites `cd ~/projets/kemalphone`, le venv s'active
et les variables `.env` sont chargées. `cd ..` les désactive.

---

## 4 — Structure type pour chaque projet

```
mon-projet/
├── .python-version      ← version Python (pyenv local X.Y.Z)
├── .envrc               ← activation automatique (direnv)
├── .env                 ← secrets locaux (JAMAIS commité)
├── .env.example         ← template commité
├── .gitignore           ← inclure .venv/, .env, __pycache__/
├── pyproject.toml       ← config projet + dépendances (uv)
├── uv.lock              ← lock file reproductible (commité)
├── requirements.txt     ← optionnel, pour compat CI classique
└── src/
    └── app.py
```

### .gitignore minimal Python

```gitignore
.venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.env
*.sqlite3
.DS_Store
```

---

## 5 — Commandes quotidiennes résumées

```bash
# Nouveau projet from scratch
mkdir nouveau-projet && cd nouveau-projet
pyenv local 3.12.4
uv venv .venv --python 3.12
echo 'source .venv/bin/activate\ndotenv .env' > .envrc
direnv allow
uv init
uv add flask

# Cloner un projet existant
git clone https://github.com/...
cd le-projet
uv sync          # installe tout depuis uv.lock
direnv allow     # si .envrc présent

# Mettre à jour toutes les dépendances d'un projet
uv lock --upgrade
uv sync

# Voir ce qui est installé
uv pip list

# Vérifier les vulnérabilités
uv pip audit     # ou: pip-audit (si installé séparément)

# Lister tous vos envs pyenv
pyenv versions

# Changer de Python pour un projet
pyenv local 3.10.14
uv venv .venv --python 3.10   # recrée le venv
uv sync
```

---

## 6 — Cas spécial : projet EL Kémal Phone (Flask)

```bash
cd ~/projets/kemalphone
pyenv local 3.11.9
uv venv .venv --python 3.11
direnv allow

# Installer les dépendances Flask du projet
uv add flask flask-sqlalchemy flask-mail flask-babel \
       flask-login werkzeug python-dotenv qrcode \
       reportlab psycopg2-binary

# Dépendances dev
uv add --dev pytest black ruff pip-audit

# Générer requirements.txt pour compatibilité (Dockerfile, CI…)
uv pip freeze > requirements.txt

# Lancer
flask --app app run --debug
```

---

## 7 — Docker : isoler complètement un projet

Pour les projets où vous voulez une isolation totale (PostgreSQL inclus) :

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir uv && uv pip install --system -r requirements.txt
COPY . .
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000"]
```

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports: ["5000:5000"]
    env_file: .env
    depends_on: [db]
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: kemal
      POSTGRES_PASSWORD: kemalpass
      POSTGRES_DB: kemaldb
    volumes: [pgdata:/var/lib/postgresql/data]

volumes:
  pgdata:
```

```bash
# Lancer tout
docker compose up --build

# Reconstruire uniquement si requirements changent
docker compose build --no-cache app
```

---

## 8 — Diagnostic rapide d'un problème de dépendances

```bash
# Quel Python est actif ?
which python && python --version

# Quel venv est actif ?
echo $VIRTUAL_ENV

# Est-ce le bon pip ?
which pip && pip --version

# Conflit de versions ?
uv pip check

# Arbre de dépendances
uv pip tree

# Vulnérabilités connues
pip-audit
```

---

## Récapitulatif : pourquoi cette stack ?

- **pyenv** : une version Python par projet, sans sudo, sans casser le système
- **uv** : 100× plus rapide que pip, lock files fiables, remplace pip-tools/Poetry pour la plupart des cas
- **direnv** : zéro friction, le bon env s'active automatiquement
- **Pas de conda** : trop lourd pour du pur Python web
- **Pas de Poetry seul** : uv est plus rapide et plus simple pour les projets Flask/scripts
