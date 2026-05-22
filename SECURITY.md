# SECURITY

Règles de base pour ce projet :

- Ne pas committer `.env` ni clés secrètes.
- Utiliser GitHub Secrets pour CI/CD.
- Valider toute entrée utilisateur côté serveur.
- Forcer HTTPS en production.
- Limiter les droits des comptes de service.
- Scanner les dépendances (`pip-audit`, `safety`).

Checklist recommandée :
1. Secrets : vérifier absence dans l'historique (`git secrets` / `truffleHog`).
2. Dépendances : `pip-audit`.
3. Static analysis : `bandit`, `flake8`.
4. CI : exiger PRs et revues avant merge.
