# Template d'automatisation pour projets

Placez ici des workflows réutilisables et des notes pour automatiser CI/CD et scans de sécurité.

Contenu recommandé :
- `ci.yml` : tests, lint, pip-audit
- `publish.yml` : build & publish image (GHCR/DockerHub)
- `scripts/` : scripts d'initialisation (git, submodule, push)
- `SECURITY.md` : règles de sécurité et checklist

Usage : copier les fichiers nécessaires dans `/.github/workflows/` et ajuster les secrets GitHub.
