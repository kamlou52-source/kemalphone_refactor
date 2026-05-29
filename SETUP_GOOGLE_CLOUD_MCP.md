# Guide : Intégration Google Cloud CLI & MCP dans votre environnement local

## Vue d'ensemble

Ce guide explique comment connecter votre projet EL Kémal Phone Solutions
à Google Cloud CLI via MCP (Model Context Protocol) depuis VS Code, Claude ou Cursor.

---

## 1. Prérequis

```bash
# Python 3.10+
python3 --version

# Node.js 18+ (nécessaire pour certains MCP servers)
node --version

# Google Cloud CLI
# → https://cloud.google.com/sdk/docs/install
gcloud --version
```

---

## 2. Installer & initialiser Google Cloud CLI

```bash
# macOS (Homebrew)
brew install --cask google-cloud-sdk

# Linux (Debian/Ubuntu)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authentifier
gcloud auth login
gcloud auth application-default login

# Configurer votre projet
gcloud config set project VOTRE_PROJECT_ID
```

---

## 3. MCP Server : Google Cloud (dans Claude ou Cursor)

### Option A — MCP serveur officiel Google Cloud

Ajoutez dans votre fichier de config MCP (`.mcp.json` à la racine du projet) :

```json
{
  "mcpServers": {
    "google-cloud": {
      "command": "npx",
      "args": ["-y", "@google-cloud/mcp-server"],
      "env": {
        "GOOGLE_CLOUD_PROJECT": "VOTRE_PROJECT_ID",
        "GOOGLE_APPLICATION_CREDENTIALS": "/chemin/vers/service-account.json"
      }
    }
  }
}
```

### Option B — MCP via gcloud CLI wrappé

```json
{
  "mcpServers": {
    "gcloud-cli": {
      "command": "python3",
      "args": ["devops/mcp_gcloud_bridge.py"],
      "env": {
        "GOOGLE_CLOUD_PROJECT": "VOTRE_PROJECT_ID"
      }
    }
  }
}
```

---

## 4. Variables d'environnement (.env)

```dotenv
# Base de données (Cloud SQL en prod, SQLite en dev)
DATABASE_URL=postgresql+psycopg2://kemal:kemalpass@127.0.0.1:5432/kemaldb

# Secrets
SECRET_KEY=votre-secret-key-aleatoire-ici

# Mail
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=votre@gmail.com
MAIL_PASSWORD=votre-app-password

# Google Cloud
GOOGLE_CLOUD_PROJECT=kemalphone-prod
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json

# Génération d'images/vidéos IA (Vertex AI Imagen)
VERTEX_AI_LOCATION=europe-west1
```

---

## 5. Génération d'images & vidéos IA avec Vertex AI

Pour générer automatiquement des visuels produits via l'IA :

```bash
pip install google-cloud-aiplatform --break-system-packages
```

Script d'exemple `scripts/generate_product_visuals.py` :

```python
import vertexai
from vertexai.vision_models import ImageGenerationModel

vertexai.init(project="kemalphone-prod", location="europe-west1")
model = ImageGenerationModel.from_pretrained("imagegeneration@006")

prompt = "iPhone 13 Pro Space Black, studio product photo, white background, 4K"
images = model.generate_images(prompt=prompt, number_of_images=1)
images[0].save(location="static/img/products/iphone13pro.jpg", include_generation_parameters=False)
```

Pour les vidéos courtes, utilisez **Veo 2** (Vertex AI) ou **Runway ML** via API.

---

## 6. Lancer en développement

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Démarrer PostgreSQL (ou utiliser SQLite en ajoutant DATABASE_URL=sqlite:///dev.db dans .env)
flask run --debug
# → http://127.0.0.1:5000
```

---

## 7. Déploiement Cloud Run (optionnel)

```bash
gcloud run deploy kemalphone \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=$DATABASE_URL,SECRET_KEY=$SECRET_KEY"
```

---

## 8. Structure recommandée des assets produits

```
static/
├── img/
│   └── products/
│       ├── iphone13pro.jpg      ← Photo réelle ou générée par IA
│       ├── s22.jpg
│       ├── airpods.jpg
│       ├── pixel7a.jpg
│       ├── iphonese3.jpg
│       ├── coque.jpg
│       └── placeholder.svg      ← Fallback si image manquante
└── videos/
    ├── iphone13pro.mp4          ← Vidéo démo (réelle ou IA)
    ├── s22.mp4
    └── ...
```

Générez `placeholder.svg` avec :
```bash
echo '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300"><rect fill="#f0f0f0" width="400" height="300"/><text x="50%" y="50%" text-anchor="middle" fill="#999" font-size="18" dy=".3em">📱 Image à venir</text></svg>' > static/img/products/placeholder.svg
```

---

## Ressources

- [Google Cloud CLI](https://cloud.google.com/sdk/docs)
- [Vertex AI Imagen](https://cloud.google.com/vertex-ai/generative-ai/docs/image/overview)
- [Vertex AI Veo (vidéo)](https://cloud.google.com/vertex-ai/generative-ai/docs/video/overview)
- [MCP Protocol](https://modelcontextprotocol.io)
- [Claude MCP Docs](https://docs.anthropic.com/en/docs/build-with-claude/mcp)
