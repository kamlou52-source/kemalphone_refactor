#!/usr/bin/env bash
set -euo pipefail

echo "Initialise le dépôt git local, ajoute le sous-module security-guidance, et pousse vers GitHub."

if [ ! -d .git ]; then
  git init
  git add -A
  git commit -m "Initial commit"
fi

REPO_URL="$1"  # https://github.com/Kamilou52/<repo>.git
if [ -z "$REPO_URL" ]; then
  echo "Usage: $0 <git_repo_url>" >&2
  exit 2
fi

git branch -M main || true
git remote add origin "$REPO_URL" || git remote set-url origin "$REPO_URL"

echo "Ajout du sous-module third_party/security-guidance (si possible)"
git submodule add https://github.com/anthropics/security-guidance third_party/security-guidance || true
git submodule update --init --remote || true

echo "Push initial vers origin/main"
git push -u origin main

echo "Terminé. Ajoutez les Secrets GitHub (GITHUB_TOKEN, GHCR_PAT si besoin) via Settings → Secrets."
