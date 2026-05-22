# DevOps Template (réutilisable)

Ce dossier contient un modèle réutilisable d'automatisation CI/CD pour projets Python/Flask.

Structure :
- `templates/ci.yml` : CI basique (lint, pip-audit, tests)
- `templates/publish.yml` : build & push image (GHCR)
- `install.sh` : script pour déployer les templates dans un dépôt existant

Utilisation rapide depuis un projet :
```bash
# depuis la racine du projet qui doit recevoir les workflows
cp -r devops-template/templates/.github_workflows/ .github/
./devops-template/install.sh
```

Personnalisez les fichiers `ci.yml` et `publish.yml` selon vos besoins (secrets, tags).
