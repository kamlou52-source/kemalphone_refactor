#!/usr/bin/env bash
# =============================================================================
# fix-pyenv.sh — Diagnostic et réparation d'un environnement Python
# Usage : bash fix-pyenv.sh          (dans le dossier du projet)
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓ $*${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $*${NC}"; }
fail() { echo -e "${RED}  ✗ $*${NC}"; }

echo "═══════════════════════════════════════════════"
echo "  🔍 Diagnostic environnement Python"
echo "  Dossier : $(pwd)"
echo "═══════════════════════════════════════════════"
echo ""

# ── Outils ──────────────────────────────────────────────────────────────────

echo "── Outils installés ───────────────────────────"
command -v pyenv  &>/dev/null && ok  "pyenv  : $(pyenv --version)" || fail "pyenv  : NON TROUVÉ"
command -v uv     &>/dev/null && ok  "uv     : $(uv --version)"    || warn "uv     : non trouvé  → curl -LsSf https://astral.sh/uv/install.sh | sh"
command -v direnv &>/dev/null && ok  "direnv : $(direnv version)"  || warn "direnv : non trouvé  → sudo apt install direnv"
echo ""

# ── Python actif ────────────────────────────────────────────────────────────
echo "── Python actif ───────────────────────────────"
PYTHON_BIN=$(which python3 2>/dev/null || which python 2>/dev/null || echo "")
if [ -z "$PYTHON_BIN" ]; then
  fail "Aucun Python trouvé dans PATH"
else
  ok "Python : $PYTHON_BIN — $(python3 --version 2>&1)"
fi

if [ -f .python-version ]; then
  REQUIRED=$(cat .python-version)
  CURRENT=$(python3 --version 2>&1 | awk '{print $2}')
  if [[ "$CURRENT" == "$REQUIRED"* ]]; then
    ok "Version .python-version ($REQUIRED) correspond"
  else
    warn "Version requise : $REQUIRED | Version active : $CURRENT"
    echo "     → Exécutez : pyenv local $REQUIRED && uv venv .venv --python $REQUIRED"
  fi
fi
echo ""

# ── Venv ────────────────────────────────────────────────────────────────────
echo "── Environnement virtuel ──────────────────────"
if [ -d .venv ]; then
  ok ".venv présent"
  if [ -n "${VIRTUAL_ENV:-}" ]; then
    ok "Venv ACTIF : $VIRTUAL_ENV"
  else
    warn "Venv présent mais NON activé"
    echo "     → Exécutez : source .venv/bin/activate"
    echo "       Ou configurez direnv avec un .envrc"
  fi
else
  fail ".venv absent"
  echo "     → Exécutez : uv venv .venv --python 3.11"
fi
echo ""

# ── Dépendances ─────────────────────────────────────────────────────────────
echo "── Dépendances ────────────────────────────────"
if [ -f requirements.txt ]; then
  ok "requirements.txt présent"
elif [ -f pyproject.toml ]; then
  ok "pyproject.toml présent"
else
  warn "Aucun fichier de dépendances trouvé"
fi

if [ -f uv.lock ]; then
  ok "uv.lock présent (reproductible)"
else
  warn "Pas de uv.lock — lancez : uv lock"
fi

# Vérifier les conflits si venv actif
if [ -n "${VIRTUAL_ENV:-}" ]; then
  echo ""
  echo "  Vérification des conflits..."
  if command -v uv &>/dev/null; then
    uv pip check 2>&1 && ok "Aucun conflit détecté" || fail "Conflits détectés (voir ci-dessus)"
  fi
fi
echo ""

# ── .env ────────────────────────────────────────────────────────────────────
echo "── Variables d'environnement ──────────────────"
if [ -f .env ]; then
  ok ".env présent"
  # Vérifier les variables clés Flask sans afficher les valeurs
  grep -q "^SECRET_KEY"    .env && ok "SECRET_KEY définie"    || warn "SECRET_KEY manquante"
  grep -q "^DATABASE_URL"  .env && ok "DATABASE_URL définie"  || warn "DATABASE_URL manquante"
else
  warn ".env absent"
  [ -f .env.example ] && echo "     → Exécutez : cp .env.example .env && nano .env" \
                       || echo "     → Créez un .env (voir PYTHON_ENVS.md section 4)"
fi
echo ""

# ── Résumé & actions recommandées ───────────────────────────────────────────
echo "═══════════════════════════════════════════════"
echo "  Actions recommandées"
echo "═══════════════════════════════════════════════"

ACTIONS=0

if [ ! -d .venv ]; then
  echo "  1. uv venv .venv --python 3.11"
  ACTIONS=$((ACTIONS+1))
fi

if [ ! -f .envrc ]; then
  cat << 'MSG'
  2. Créer .envrc :
     echo 'source .venv/bin/activate
     dotenv .env' > .envrc && direnv allow
MSG
  ACTIONS=$((ACTIONS+1))
fi

if [ -f requirements.txt ] && [ ! -f uv.lock ]; then
  echo "  3. uv pip compile requirements.txt -o requirements.lock"
  ACTIONS=$((ACTIONS+1))
fi

[ $ACTIONS -eq 0 ] && echo -e "${GREEN}  Tout semble en ordre ! 🎉${NC}"
echo ""
