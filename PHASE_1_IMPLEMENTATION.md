# 📋 PLAN D'IMPLÉMENTATION PHASE 1
## Fondations E-commerce | Semaines 1-4

---

## 🎯 OBJECTIFS PHASE 1

- ✅ Upgrade dépendances Python
- ✅ Extension modèle de données (Product, Order, Return)
- ✅ Configuration Redis + Celery
- ✅ Audit de sécurité
- ✅ Docker-compose mise à jour
- ✅ Tests unitaires
- ✅ Documentation développeur

---

## 📦 ÉTAPE 1 : Mise à jour requirements.txt

### Fichier à modifier: `requirements.txt`

**Ajouter les dépendances suivantes** :

```
# Existants (à conserver)
flask==2.3.2
flask_sqlalchemy==3.0.5
flask_login==0.6.2
flask_babel==2.0.0
Flask-Mail==0.9.1
qrcode==7.4.2
reportlab==4.0.4
gunicorn==21.2.0
psycopg2-binary==2.9.6
python-dotenv==1.0.0

# ===== NOUVEAUX (E-COMMERCE) =====

# Paiements
stripe==6.0.0                      # Intégration Stripe
requests==2.31.0                   # HTTP client (APIs externes)

# Cache & Sessions
redis==5.0.0                       # Client Redis
flask-caching==2.0.2               # Caching decorator

# Tâches asynchrones
celery==5.3.1                      # Task queue
redis==5.0.0                       # Message broker

# Email transactionnel
Flask-Mail==0.9.1                  # (déjà présent, conserver)
python-mailgun==1.1.5              # Alternative à SendGrid

# Validation & Sécurité
email-validator==2.0.0             # Email validation
validators==0.22.0                 # URL, phone, etc.
bleach==6.0.0                      # HTML sanitization
python-dotenv==1.0.0               # (déjà présent)

# API & Webhooks
pydantic==2.0.3                    # Data validation
marshmallow==3.20.1                # Serialization

# Images & Fichiers
pillow==10.0.0                     # Image processing
boto3==1.28.20                     # AWS S3 (optionnel)

# Tests
pytest==7.4.0                      # Test framework
pytest-flask==1.2.0                # Flask fixtures
pytest-cov==4.1.0                  # Coverage
factory-boy==3.3.0                 # Test data factory

# Audit de sécurité
pip-audit==2.6.0                   # Vulnerability scan
safety==2.3.5                      # Dependency checker

# Monitoring & Logging
sentry-sdk==1.32.0                 # Error tracking
python-json-logger==2.0.7          # Structured logging

# Utilitaires
python-dateutil==2.8.2             # Date utilities
pytz==2023.3                       # Timezone
```

### ⚙️ Installation

```bash
# Activer venv (si pas déjà fait)
source .venv/bin/activate

# Mettre à jour pip
pip install --upgrade pip

# Installer/Mettre à jour dépendances
pip install -r requirements.txt

# Freeze des versions actuelles
pip freeze > requirements.txt

# Audit de sécurité
pip-audit --desc          # Montrer descriptions vulnérabilités
safety check --json       # Vérifier dependencies
```

---

## 📊 ÉTAPE 2 : Extension du Modèle de Données

### Créer fichier: `models.py`

```python
# models.py - Modèles SQLAlchemy pour e-commerce

from datetime import datetime
from enum import Enum as PyEnum
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import enum

db = SQLAlchemy()

# ===== ENUMS =====

class ProductCategory(str, PyEnum):
    PHONE = "phone"              # Appareils
    COMPUTER = "computer"        # Ordinateurs
    APPLIANCE = "appliance"      # Électroménagers
    PARTS = "parts"              # Pièces détachées
    ACCESSORIES = "accessories"  # Accessoires

class ProductCondition(str, PyEnum):
    NEW = "new"                  # Neuf
    REFURBISHED = "refurbished"  # Reconditionné Grade A
    GOOD = "good"                # Bon état
    FAIR = "fair"                # Acceptable

class OrderStatus(str, PyEnum):
    PENDING = "pending"          # En attente de paiement
    PAID = "paid"                # Payé
    PROCESSING = "processing"    # Traitement
    SHIPPED = "shipped"          # Expédié
    DELIVERED = "delivered"      # Livré
    RETURNED = "returned"        # Retourné
    CANCELLED = "cancelled"      # Annulé

class ReturnStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"

# ===== MODÈLES =====

class User(UserMixin, db.Model):
    __tablename__ = "user"
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    role = db.Column(db.String(20), default="user")  # user, admin, staff
    is_active = db.Column(db.Boolean, default=True)
    
    # Relations
    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')
    addresses = db.relationship('Address', backref='user', lazy=True, cascade='all, delete-orphan')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    __tablename__ = "product"
    __table_args__ = (
        db.Index('idx_product_sku', 'sku'),
        db.Index('idx_product_category', 'category'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)  # URL-friendly
    description = db.Column(db.Text)
    category = db.Column(db.String(20), nullable=False)
    condition = db.Column(db.String(20), default="refurbished")
    
    price_chf = db.Column(db.Numeric(10, 2), nullable=False)
    stock_qty = db.Column(db.Integer, default=0)
    
    # Détails produit
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    specs = db.Column(db.JSON)  # {"ram": "8GB", "storage": "256GB", ...}
    
    # Images
    image_url = db.Column(db.String(500))
    images = db.relationship('ProductImage', backref='product', cascade='all, delete-orphan')
    
    # Métadonnées
    weight_kg = db.Column(db.Numeric(6, 2))
    warranty_months = db.Column(db.Integer, default=12)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def as_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'price': float(self.price_chf),
            'stock': self.stock_qty,
            'category': self.category,
            'condition': self.condition,
        }

class ProductImage(db.Model):
    __tablename__ = "product_image"
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    alt_text = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, default=0)

class Order(db.Model):
    __tablename__ = "order"
    __table_args__ = (
        db.Index('idx_order_user_id', 'user_id'),
        db.Index('idx_order_created', 'created_at'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Montants (en CHF)
    subtotal_chf = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_chf = db.Column(db.Numeric(10, 2), default=0)
    tax_chf = db.Column(db.Numeric(10, 2), default=0)
    total_chf = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Statut & paiement
    status = db.Column(db.String(20), default="pending")
    payment_method = db.Column(db.String(50))  # stripe, twint, card
    stripe_session_id = db.Column(db.String(255))
    
    # Livraison
    shipping_address = db.Column(db.JSON, nullable=False)
    tracking_number = db.Column(db.String(100))
    
    # Relations
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')
    
    # Métadonnées
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OrderItem(db.Model):
    __tablename__ = "order_item"
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Numeric(10, 2), nullable=False)
    
    product = db.relationship('Product')

class Address(db.Model):
    __tablename__ = "address"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    street = db.Column(db.String(150), nullable=False)
    street_number = db.Column(db.String(10), nullable=False)
    postal_code = db.Column(db.String(10), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(2), default="CH")
    phone = db.Column(db.String(20))
    
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReturnRequest(db.Model):
    __tablename__ = "return_request"
    
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_item.id'), nullable=False)
    
    reason = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")
    
    refund_amount_chf = db.Column(db.Numeric(10, 2))
    return_label_url = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    order_item = db.relationship('OrderItem')
```

### Intégrer dans app.py

```python
# Au début de app.py, remplacer les modèles existants par:

from models import (
    db, User, Product, ProductImage, Order, OrderItem,
    Address, ReturnRequest, ProductCategory, ProductCondition,
    OrderStatus, ReturnStatus
)

# Puis dans create_app():
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'sqlite:///kemalphone.db'
)
db.init_app(app)
```

---

## ⚙️ ÉTAPE 3 : Configuration Redis & Celery

### Créer fichier: `.env` (template)

```bash
# Base de données
DATABASE_URL=postgresql+psycopg2://kemal:kemalpass@localhost:5432/kemaldb

# Redis (cache + session store)
REDIS_URL=redis://localhost:6379/0

# Celery (task queue)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Flask config
SECRET_KEY=your-super-secret-key-change-in-prod
FLASK_ENV=development

# Paiements (à remplir Phase 3)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...

# Email
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=SG.xxxxx

# La Poste (Phase 4)
LA_POSTE_API_KEY=
LA_POSTE_API_URL=https://sandbox.laposte.fr/api/v1

# Hootsuite (Phase 5)
HOOTSUITE_API_TOKEN=
```

### Créer fichier: `celery_app.py`

```python
# celery_app.py - Configuration Celery

from celery import Celery
import os

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=os.getenv('CELERY_RESULT_BACKEND'),
        broker=os.getenv('CELERY_BROKER_URL'),
    )
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery
```

### Utilisation dans app.py

```python
from celery_app import make_celery

app = Flask(__name__)
# ... config ...

celery = make_celery(app)

# Exemple: Task email asynchrone
@celery.task
def send_order_confirmation_email(order_id):
    from flask_mail import Message
    order = Order.query.get(order_id)
    msg = Message(
        f"Confirmation commande {order.order_number}",
        recipients=[order.user.email],
        html=render_template('email/order_confirmation.html', order=order)
    )
    mail.send(msg)
```

---

## 🐳 ÉTAPE 4 : Mise à jour Docker-compose

### Fichier à modifier: `docker-compose.yml`

```yaml
version: '3.8'

services:
  # Base de données
  db:
    image: postgres:15-alpine
    container_name: kemalphone_db
    environment:
      POSTGRES_USER: kemal
      POSTGRES_PASSWORD: kemalpass
      POSTGRES_DB: kemaldb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kemal"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Cache Redis
  redis:
    image: redis:7-alpine
    container_name: kemalphone_redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Application Flask
  app:
    build: .
    container_name: kemalphone_app
    command: gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql+psycopg2://kemal:kemalpass@db:5432/kemaldb
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      FLASK_ENV: production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped

  # Worker Celery (tâches asynchrones)
  worker:
    build: .
    container_name: kemalphone_worker
    command: celery -A celery_app.celery worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+psycopg2://kemal:kemalpass@db:5432/kemaldb
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      - db
      - redis
    restart: unless-stopped

  # Email local (dev)
  mailhog:
    image: mailhog/mailhog:latest
    container_name: kemalphone_mailhog
    ports:
      - "1025:1025"    # SMTP
      - "8025:8025"    # Web UI
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

---

## 🧪 ÉTAPE 5 : Tests Unitaires

### Créer fichier: `tests/conftest.py` (mise à jour)

```python
# tests/conftest.py

import pytest
import os
from app import app, db

@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

@pytest.fixture
def runner(app):
    """Flask CLI runner"""
    return app.test_cli_runner()

@pytest.fixture
def init_db():
    """Initialize database"""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()
```

### Créer fichier: `tests/test_products.py`

```python
# tests/test_products.py

import pytest
from models import Product, ProductCategory

def test_create_product(init_db):
    """Test création produit"""
    product = Product(
        sku='IPHONE14-128',
        name='iPhone 14 128GB',
        slug='iphone-14-128gb',
        category='phone',
        condition='refurbished',
        price_chf=599.99,
        stock_qty=5,
        brand='Apple',
        model='iPhone 14'
    )
    init_db.session.add(product)
    init_db.session.commit()
    
    assert Product.query.count() == 1
    assert product.sku == 'IPHONE14-128'

def test_product_api(client):
    """Test API produits"""
    response = client.get('/api/products')
    assert response.status_code == 200
```

### Lancer les tests

```bash
# Tous les tests
pytest

# Avec coverage
pytest --cov=. --cov-report=html

# Tests spécifiques
pytest tests/test_products.py -v
```

---

## 🔐 ÉTAPE 6 : Audit de Sécurité

### Checklist de sécurité

```bash
# 1. Audit dépendances
pip-audit --desc
safety check --json

# 2. Scan vulnérabilités code
# Optionnel: bandit, semgrep
pip install bandit
bandit -r . -f json > bandit-report.json

# 3. Audit fichiers
# Chercher hardcoded secrets
pip install detect-secrets
detect-secrets scan --baseline .secrets.baseline

# 4. Vérifier HTTPS (production)
# ssl-labs.com: tester après deploy
```

### Résultats attendus

✅ Aucune vulnérabilité critique
✅ Secrets non commitées
✅ Validations input côté serveur
✅ HTTPS forcé en production

---

## ✅ CHECKLIST FIN DE PHASE 1

### Code
- [ ] `requirements.txt` mise à jour + testé
- [ ] `models.py` créé avec tous les modèles e-commerce
- [ ] `app.py` intègre les nouveaux modèles
- [ ] `celery_app.py` créé et configuré
- [ ] `.env.example` créé avec tous les vars
- [ ] Tests unitaires passent (`pytest`)
- [ ] Audit sécurité OK (`pip-audit`, `bandit`)

### Infrastructure
- [ ] `docker-compose.yml` mis à jour
- [ ] PostgreSQL démarre sans erreur
- [ ] Redis connect correctement
- [ ] Celery worker se lance
- [ ] MailHog fonctionne (dev emails)

### Documentation
- [ ] README.md mise à jour (installation Phase 1)
- [ ] CONTRIBUTING.md crée (for team)
- [ ] API documentation (postman collection)

### Git
- [ ] Commits clairs et atomiques
- [ ] `.gitignore` inclut `.env`, `__pycache__`, `.venv`
- [ ] Branch `feature/phase-1-foundation` mergée
- [ ] Tags versioning (`v0.1.0`)

---

## 🚀 Commandes pour démarrer Phase 1

```bash
# 1. Créer env et installer dépendances
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Mettre à jour BD (migrations)
flask db upgrade        # Si utilisant Alembic
# Ou directement:
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# 3. Lancer tests
pytest -v

# 4. Lancer avec Docker
docker-compose up -d
docker-compose logs -f app

# 5. Vérifier
curl http://localhost:5000/health
curl http://localhost:5000/api/products
```

---

**Prêt pour Phase 2? À bientôt! 🎉**
