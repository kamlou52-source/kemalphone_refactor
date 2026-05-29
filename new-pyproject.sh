#!/usr/bin/env bash
# =============================================================================
# new-pyproject.sh — Initialise un nouveau projet Python proprement
# Usage : bash new-pyproject.sh mon-projet 3.11
# =============================================================================

set -euo pipefail

PROJECT_NAME="${1:-mon-projet}"
PYTHON_VERSION="${2:-3.11}"
BASE_DIR="${HOME}/projets"

echo "╔══════════════════════════════════════════════════════╗"
echo "  🐍 Nouveau projet : $PROJECT_NAME (Python $PYTHON_VERSION)"
echo "╚══════════════════════════════════════════════════════╝"

# 1. Créer le dossier
mkdir -p "$BASE_DIR/$PROJECT_NAME"
cd "$BASE_DIR/$PROJECT_NAME"
echo "📁 Dossier créé : $BASE_DIR/$PROJECT_NAME"

# 2. Fixer la version Python avec pyenv
if command -v pyenv &>/dev/null; then
  pyenv local "$PYTHON_VERSION"
  echo "🐍 Python $PYTHON_VERSION fixé via pyenv"
else
  echo "⚠️  pyenv non trouvé — installez-le : curl https://pyenv.run | bash"
fi

# 3. Créer le venv avec uv
if command -v uv &>/dev/null; then
  uv venv .venv --python "$PYTHON_VERSION"
  echo "📦 Venv créé avec uv"
else
  echo "⚠️  uv non trouvé — installez-le : curl -LsSf https://astral.sh/uv/install.sh | sh"
  python3 -m venv .venv
fi

# 4. .envrc pour direnv
cat > .envrc << 'EOF'
source .venv/bin/activate
[ -f .env ] && dotenv .env
EOF
if command -v direnv &>/dev/null; then
  direnv allow .
  echo "🔁 direnv configuré"
else
  echo "⚠️  direnv non trouvé : sudo apt install direnv"
fi

# 5. .env et .env.example
cat > .env.example << 'EOF'
SECRET_KEY=changez-moi
DATABASE_URL=sqlite:///dev.db
MAIL_SERVER=localhost
MAIL_PORT=1025
EOF
cp .env.example .env
echo "🔐 .env créé depuis .env.example"

# 6. .gitignore
cat > .gitignore << 'EOF'
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
.direnv/
EOF

# 7. pyproject.toml minimal
if command -v uv &>/dev/null; then
  uv init --no-workspace 2>/dev/null || true
fi

# 8. Git init
git init -q
git add .
git commit -m "chore: init projet $PROJECT_NAME" -q
echo "📝 Git initialisé"

echo ""
echo "✅ Projet prêt !"
echo ""
echo "   cd $BASE_DIR/$PROJECT_NAME"
echo "   uv add flask              # ajouter des dépendances"
echo "   uv add --dev pytest ruff  # dépendances dev"
echo "   uv sync                   # installer depuis uv.lock"
echo ""
