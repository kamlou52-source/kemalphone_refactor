#!/usr/bin/env bash
set -euo pipefail

echo "Installation du template devops dans le dépôt courant..."

# create target .github/workflows if needed
mkdir -p .github/workflows

# copy templates
cp -v devops-template/templates/ci.yml .github/workflows/ci.yml || true
cp -v devops-template/templates/publish.yml .github/workflows/publish.yml || true

# copy SECURITY.md if absent
if [ ! -f SECURITY.md ]; then
  cp -v SECURITY.md . || true
fi

echo "Template installé. N'oubliez pas d'ajuster les secrets GitHub et personnaliser les workflows."
