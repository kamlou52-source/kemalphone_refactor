# app.py  — EL Kémal Phone Solutions (version corrigée)
import os, io, base64, secrets, time, qrcode
from io import StringIO
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, current_app, flash,
    jsonify, session, send_from_directory, send_file, Response
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, or_
from flask_mail import Mail, Message
from flask_babel import Babel, gettext as _
from flask_login import (
    LoginManager, UserMixin, login_user, login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv, find_dotenv

# ===== Extensions (créées au niveau module) =====================================
db = SQLAlchemy()
mail = Mail()
babel = Babel()
login_manager = LoginManager()

# ===== Catalogue boutique (source unique) =======================================
SHOP_PRODUCTS = [
    {
        "slug": "iphone-13-pro",
        "name": "iPhone 13 Pro",
        "price": "699 CHF",
        "category": "iOS",
        "badge": "Best-seller",
        "description": "iPhone reconditionné premium, batterie ≥ 85 %, Face ID fonctionnel.",
        "image": "img/products/iphone13pro.jpg",
        "video": "videos/iphone13pro.mp4",
    },
    {
        "slug": "samsung-s22",
        "name": "Samsung Galaxy S22",
        "price": "549 CHF",
        "category": "Android",
        "badge": "Nouveau",
        "description": "Smartphone Android performant, garanti 6 mois, écran AMOLED.",
        "image": "img/products/s22.jpg",
        "video": "videos/s22.mp4",
    },
    {
        "slug": "airpods-pro",
        "name": "AirPods Pro",
        "price": "149 CHF",
        "category": "Accessoire",
        "badge": "",
        "description": "Écouteurs sans fil Apple ANC, boîtier de charge MagSafe inclus.",
        "image": "img/products/airpods.jpg",
        "video": "videos/airpods.mp4",
    },
    {
        "slug": "pixel-7a",
        "name": "Google Pixel 7a",
        "price": "449 CHF",
        "category": "Android",
        "badge": "",
        "description": "Appareil photo exceptionnel, Android pur, mises à jour garanties.",
        "image": "img/products/pixel7a.jpg",
        "video": "videos/pixel7a.mp4",
    },
    {
        "slug": "iphone-se-3",
        "name": "iPhone SE 3e gén.",
        "price": "379 CHF",
        "category": "iOS",
        "badge": "Prix imbattable",
        "description": "Le plus compact des iPhones avec puce A15 Bionic.",
        "image": "img/products/iphonese3.jpg",
        "video": "videos/iphonese3.mp4",
    },
    {
        "slug": "coque-magsafe",
        "name": "Coque MagSafe Universal",
        "price": "29 CHF",
        "category": "Accessoire",
        "badge": "",
        "description": "Protection slim compatible MagSafe, disponible en 6 coloris.",
        "image": "img/products/coque.jpg",
        "video": "",
    },
]

# ===== Utilitaires config =======================================================
def normalize_db_url(raw: str | None) -> str:
    fallback = "postgresql+psycopg2://kemal:kemalpass@127.0.0.1:5432/kemaldb"
    if not raw or not raw.strip():
        return fallback
    url = raw.strip()
    return url.replace("localhost", "127.0.0.1") if "localhost" in url else url

def wait_for_db(uri: str, retries: int = 10, delay: float = 1.0):
    from sqlalchemy import create_engine
    eng = create_engine(uri, pool_pre_ping=True, future=True)
    last_err = None
    for _ in range(retries):
        try:
            with eng.connect() as c:
                c.execute(text("select 1"))
                return
        except Exception as e:
            last_err = e
            time.sleep(delay)
    raise RuntimeError(f"DB indisponible. URI={uri}\nDernière erreur: {last_err}")

# ===== Modèles ==================================================================
class UserInput(db.Model):
    __tablename__ = "userinput"
    __table_args__ = (db.Index("idx_userinput_created", "created"),)
    id      = db.Column(db.Integer, primary_key=True)
    fname   = db.Column(db.String(50),  nullable=False)
    modele  = db.Column(db.String(80),  nullable=False)
    problem = db.Column(db.String(255), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "fname": self.fname,
            "modele": self.modele,
            "problem": self.problem,
            "created": (self.created.isoformat() if self.created else None),
        }

class User(UserMixin, db.Model):
    __tablename__ = "user"
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default="user")
    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)

class QuickToken(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    token      = db.Column(db.String(64), unique=True, nullable=False, index=True)
    purpose    = db.Column(db.String(32), nullable=False, default="login")
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created    = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

# --- Facturation ----------------------------------------------------------------
SWISS_VAT_RATES = {'standard': 0.081, 'reduit': 0.026, 'special': 0.038}
SWISS_VAT_RATE  = SWISS_VAT_RATES['standard']

class Invoice(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    customer_name  = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=True)
    method     = db.Column(db.String(20), nullable=False, default='quote')
    subtotal   = db.Column(db.Float, nullable=False, default=0.0)
    vat_amount = db.Column(db.Float, nullable=False, default=0.0)
    total      = db.Column(db.Float, nullable=False, default=0.0)
    status     = db.Column(db.String(20), nullable=False, default='draft')
    created    = db.Column(db.DateTime, default=datetime.utcnow)

class InvoiceItem(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    invoice_id  = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False, index=True)
    description = db.Column(db.String(200), nullable=False)
    qty         = db.Column(db.Integer, nullable=False, default=1)
    unit_price  = db.Column(db.Float, nullable=False, default=0.0)
    vat_code    = db.Column(db.String(10), nullable=False, default='standard')
    vat_rate    = db.Column(db.Float, nullable=False, default=0.081)

# ===== Application factory ======================================================
def create_app():
    # -- .env
    env_path = find_dotenv(usecwd=True) or str(Path(__file__).with_name(".env"))
    if env_path:
        load_dotenv(env_path, override=False)
    print("Loaded .env from:", env_path)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-prod")

    # Assets versionnés
    app.config['ASSET_VERSION'] = str(int(time.time())) if app.debug else "1.0.0"
    def asset(path: str) -> str:
        return url_for("static", filename=path, v=current_app.config['ASSET_VERSION'])
    app.jinja_env.globals['asset'] = asset

    # Uploads
    UPLOAD_DIR = Path(app.root_path) / "uploads"
    UPLOAD_DIR.mkdir(exist_ok=True)
    app.config["UPLOAD_FOLDER"]        = str(UPLOAD_DIR)
    app.config["MAX_CONTENT_LENGTH"]   = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
    def allowed_file(filename: str) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    # DB
    raw_url = os.getenv("DATABASE_URL")
    db_url  = normalize_db_url(raw_url)
    print("DATABASE_URL used by SQLAlchemy:", db_url)
    app.config["SQLALCHEMY_DATABASE_URI"]    = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"]  = {"pool_pre_ping": True}

    # Mail
    app.config.setdefault('MAIL_SERVER',   os.getenv('MAIL_SERVER', 'localhost'))
    app.config.setdefault('MAIL_PORT',     int(os.getenv('MAIL_PORT', '1025')))
    app.config.setdefault('MAIL_USE_TLS',  os.getenv('MAIL_USE_TLS','false').lower()=='true')
    app.config.setdefault('MAIL_USE_SSL',  os.getenv('MAIL_USE_SSL','false').lower()=='true')
    app.config.setdefault('MAIL_USERNAME', os.getenv('MAIL_USERNAME'))
    app.config.setdefault('MAIL_PASSWORD', os.getenv('MAIL_PASSWORD'))
    app.config.setdefault('MAIL_DEFAULT_SENDER', (
        os.getenv('MAIL_FROM_NAME', 'Kemal Phone'),
        os.getenv('MAIL_FROM_ADDR', 'noreply@example.com')
    ))

    # i18n
    app.config['BABEL_DEFAULT_LOCALE']    = 'fr'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['fr', 'en', 'de', 'it']

    # Init extensions
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"
    babel.init_app(app, locale_selector=lambda:
        session.get('locale')
        or request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])
        or 'fr'
    )

    # DB ready + create_all + seed admin
    with app.app_context():
        wait_for_db(app.config["SQLALCHEMY_DATABASE_URI"])
        db.create_all()
        if not User.query.filter_by(email="admin@example.com").first():
            admin = User(email="admin@example.com", role="admin")
            admin.set_password("Admin!234")
            db.session.add(admin); db.session.commit()
            print("Admin créé.")

    @app.context_processor
    def inject_i18n():
        return {"supported_locales": app.config.get("BABEL_SUPPORTED_LOCALES", ["fr","en"])}

    # ===== Helpers / Décorateurs ================================================
    def is_alpha(s: str) -> bool:
        return s.replace(" ", "").isalpha()

    def staff_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or getattr(current_user,'role','user') not in ('staff','admin'):
                flash(_('Accès réservé au personnel.'), 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapper

    def admin_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or getattr(current_user,'role','user') != 'admin':
                flash(_('Accès réservé aux administrateurs.'), 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapper

    def store_db(fname, modele, problem):
        fname = User.fname
        ui = UserInput(fname=fname.strip(), modele=modele.strip(),
                       problem=problem.strip(), created=datetime.utcnow())
        db.session.add(ui); db.session.commit()
        return ui.id

    # ===== ROUTES ===============================================================

    # Langue
    @app.route('/set_locale/<locale>', endpoint='set_locale')
    def set_locale(locale):
        if locale not in app.config['BABEL_SUPPORTED_LOCALES']:
            flash(_('Langue non supportée.'), 'error')
        else:
            session['locale'] = locale
            flash(_('Langue changée.'), 'success')
        return redirect(request.referrer or url_for('index'))

    # --- Accueil (SANS produits — ils vivent dans /boutique) --------------------
    @app.route("/")
    def index():
        # On passe juste les dernières demandes pour le suivi client
        recent = UserInput.query.order_by(UserInput.created.desc()).limit(5).all()
        return render_template("index.html", recent_requests=recent)

    # --- Boutique ---------------------------------------------------------------
    @app.route("/boutique")
    def boutique():
        category = request.args.get("cat", "")
        products = SHOP_PRODUCTS
        if category:
            products = [p for p in products if p["category"] == category]
        categories = sorted({p["category"] for p in SHOP_PRODUCTS})
        return render_template("boutique.html",
                               products=products,
                               categories=categories,
                               active_cat=category)

    @app.route("/boutique/<slug>")
    def product_detail(slug):
        product = next((p for p in SHOP_PRODUCTS if p["slug"] == slug), None)
        if not product:
            flash("Produit introuvable.", "error")
            return redirect(url_for("boutique"))
        related = [p for p in SHOP_PRODUCTS if p["category"] == product["category"] and p["slug"] != slug][:3]
        return render_template("product_detail.html", product=product, related=related)

    @app.route("/boutique/<slug>/commander", methods=["POST"])
    def product_order(slug):
        product = next((p for p in SHOP_PRODUCTS if p["slug"] == slug), None)
        if not product:
            return redirect(url_for("boutique"))
        flash(f"✅ Votre demande pour « {product['name']} » a été envoyée. Nous vous contactons sous 24h.", "success")
        return redirect(url_for("boutique"))

    # --- Formulaires réparation -------------------------------------------------
    @app.route("/userinput", methods=["GET", "POST"], endpoint="userinput_form")
    def userinput_form():
        if request.method == "POST":
            fname = (request.form.get("fname") or "").strip()
            if not fname or not is_alpha(fname):
                flash("Le prénom doit contenir uniquement des lettres.", "error")
                return redirect(url_for("userinput_form"))
            session["pending_fname"] = fname
            return redirect(url_for("android_form"))
        return render_template("userinput.html")

    @app.route("/android_form", methods=["GET", "POST"])
    def android_form():
        fname = session.get("pending_fname")
        if not fname:
            flash("Veuillez d'abord saisir votre prénom.", "error")
            return redirect(url_for("userinput_form"))
        if request.method == "POST":
            modele  = (request.form.get("modele") or "").strip()
            problem = (request.form.get("Problems") or request.form.get("problem") or "").strip()
            errors = []
            if not modele:  errors.append("Veuillez choisir un modèle.")
            if not problem: errors.append("Veuillez décrire le problème.")
            if errors:
                for e in errors: flash(e, "error")
                return redirect(url_for("android_form"))
            uid = store_db(fname, modele, problem)
            session.pop("pending_fname", None)
            session["last_userinput_id"] = uid
            flash("✅ Votre demande a été enregistrée.", "success")
            return redirect(url_for("index"))
        return render_template("android_form.html", fname=fname)

    @app.route("/ios_form", methods=["GET", "POST"])
    def ios_form():
        fname = session.get("pending_fname")
        if not fname:
            flash("Veuillez d'abord saisir votre prénom.", "error")
            return redirect(url_for("userinput_form"))
        if request.method == "POST":
            modele  = (request.form.get("modele") or "").strip()
            problem = (request.form.get("Problems") or request.form.get("problem") or "").strip()
            errors = []
            if not modele:  errors.append("Veuillez choisir un modèle.")
            if not problem: errors.append("Veuillez décrire le problème.")
            if errors:
                for e in errors: flash(e, "error")
                return redirect(url_for("ios_form"))
            uid = store_db(fname, modele, problem)
            session.pop("pending_fname", None)
            session["last_userinput_id"] = uid
            flash("✅ Votre demande a été enregistrée.", "success")
            return redirect(url_for("index"))
        return render_template("ios_form.html", fname=fname)

    # --- Historique -------------------------------------------------------------
    @app.get("/userinput_list")
    def userinput_list():
        q       = (request.args.get("q") or "").strip()
        modele  = (request.args.get("modele") or "").strip()
        start_s = (request.args.get("start") or "").strip()
        end_s   = (request.args.get("end") or "").strip()
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(50, int(request.args.get("per_page", 20)))
        qry = UserInput.query
        if q:
            like = f"%{q}%"
            qry = qry.filter(or_(UserInput.fname.ilike(like),
                                 UserInput.modele.ilike(like),
                                 UserInput.problem.ilike(like)))
        if modele:
            qry = qry.filter(UserInput.modele == modele)
        def _d(s):
            try: return datetime.strptime(s, "%Y-%m-%d")
            except Exception: return None
        start_dt, end_dt = _d(start_s), _d(end_s)
        if start_dt: qry = qry.filter(UserInput.created >= start_dt)
        if end_dt:   qry = qry.filter(UserInput.created < (end_dt + timedelta(days=1)))
        qry = qry.order_by(UserInput.created.desc())
        pagination = qry.paginate(page=page, per_page=per_page, error_out=False)
        models = [m[0] for m in db.session.query(UserInput.modele).distinct().order_by(UserInput.modele.asc()).all()]
        return render_template("userinput_list.html",
                               userinputs=pagination.items,
                               pagination=pagination,
                               models=models)

    @app.get("/userinput/<int:rid>")
    def userinput_detail(rid: int):
        u = UserInput.query.get_or_404(rid)
        return render_template("request_detail.html", u=u)

    # --- API JSON ---------------------------------------------------------------
    @app.get("/api/userinputs")
    def api_userinputs():
        limit = int(request.args.get("limit", 100))
        rows = UserInput.query.order_by(UserInput.created.desc()).limit(limit).all()
        return jsonify([r.as_dict() for r in rows])

    @app.get("/me")
    def me_api():
        uid = session.get("last_userinput_id")
        ui = UserInput.query.get(uid) if uid else None
        if not ui:
            ui = UserInput.query.order_by(UserInput.created.desc()).first()
        if not ui:
            return jsonify({"error": "no data"}), 404
        return jsonify(ui.as_dict())

    @app.get("/api/products")
    def api_products():
        return jsonify(SHOP_PRODUCTS)

    # --- Uploads ----------------------------------------------------------------
    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        if request.method == "POST":
            f = request.files.get("file")
            if not f or not f.filename:
                flash("Choisissez un fichier.", "error"); return redirect(url_for("upload"))
            if not allowed_file(f.filename):
                flash("Type non autorisé (png, jpg, jpeg, pdf).", "error"); return redirect(url_for("upload"))
            name = secure_filename(f.filename)
            f.save(UPLOAD_DIR / name)
            flash("Fichier envoyé ✅", "success")
            return redirect(url_for("upload"))
        files = sorted(UPLOAD_DIR.glob("*"))
        return render_template("upload.html", files=[p.name for p in files])

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # --- Export CSV -------------------------------------------------------------
    @app.get("/export/userinputs.csv")
    @login_required
    @admin_required
    def export_userinputs_csv():
        rows = UserInput.query.order_by(UserInput.id.asc()).all()
        si = StringIO()
        import csv
        w = csv.writer(si)
        w.writerow(["id","fname","modele","problem","created"])
        for r in rows:
            w.writerow([r.id, r.fname, r.modele, r.problem,
                        r.created.isoformat() if r.created else ""])
        return Response(si.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="userinputs.csv"'})

    # --- Santé ------------------------------------------------------------------
    @app.get("/healthz")
    def healthz(): return "ok", 200

    @app.get("/readyz")
    def readyz():
        db.session.execute(text("SELECT 1"))
        return {"status": "ready"}, 200

    # ===== QR login + contact ===================================================
    def _create_qr_login_token(user_id=None, minutes_valid=10):
        tok = secrets.token_hex(24)
        expires = datetime.utcnow() + timedelta(minutes=minutes_valid)
        qt = QuickToken(token=tok, purpose="login", user_id=user_id, expires_at=expires)
        db.session.add(qt); db.session.commit()
        return tok

    def _qr_png_base64(data: str, box_size=8, border=2):
        img = qrcode.make(data, box_size=box_size, border=border)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @app.route("/contactus")
    def contact():
        uid = current_user.id if current_user.is_authenticated else None
        token = _create_qr_login_token(user_id=uid, minutes_valid=10)
        login_url = url_for("qr_login", token=token, _external=True)
        qr_b64 = _qr_png_base64(login_url)
        return render_template("contactus.html", qr_code=qr_b64, login_url=login_url)

    @app.route("/qr-login/<token>")
    def qr_login(token):
        qt = QuickToken.query.filter_by(token=token, purpose="login").first()
        if not qt: flash("QR invalide.", "error"); return redirect(url_for("index"))
        if qt.expires_at < datetime.utcnow(): flash("QR expiré.", "error"); return redirect(url_for("index"))
        if qt.user_id:
            user = User.query.get(qt.user_id)
            if user:
                login_user(user, duration=timedelta(days=7))
                flash("Connexion via QR réussie.", "success")
        else:
            session["quick_auth"] = True
            flash("Session rapide activée par QR.", "success")
        db.session.delete(qt); db.session.commit()
        return redirect(url_for("index"))

    # ===== Auth =================================================================
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            email    = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            if not email or not password:
                flash("E-mail et mot de passe requis.", "error")
                return redirect(url_for("register"))
            if User.query.filter_by(email=email).first():
                flash("Un compte existe déjà avec cet e-mail.", "error")
                return redirect(url_for("register"))
            user = User(email=email); user.set_password(password)
            db.session.add(user); db.session.commit()
            flash("Compte créé, vous pouvez vous connecter.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email    = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user, duration=timedelta(days=7))
                flash("Connexion réussie.", "success")
                return redirect(url_for("index"))
            flash("Identifiants invalides.", "error")
            return redirect(url_for("login"))
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Déconnecté.", "success")
        return redirect(url_for("index"))

    # ===== Stats ================================================================
    @app.route("/stats")
    @login_required
    @admin_required
    def stats():
        rows = UserInput.query.all()
        models   = Counter([r.modele  for r in rows])
        problems = Counter([r.problem for r in rows])
        data = {"models": models, "problems": problems, "total": len(rows)}
        return render_template("stats.html", stats=data)

    # ===== Facturation ==========================================================
    @app.route('/billing', methods=['GET','POST'])
    @staff_required
    def billing():
        if request.method == 'POST':
            name   = (request.form.get('customer_name')  or '').strip()
            email  = (request.form.get('customer_email') or '').strip()
            method = request.form.get('method') or 'quote'
            items  = []
            n = int(request.form.get('items_count') or 0)
            for i in range(1, n+1):
                desc     = (request.form.get(f'desc_{i}')  or '').strip()
                qty      = int(request.form.get(f'qty_{i}')   or 0)
                price    = float(request.form.get(f'price_{i}') or 0.0)
                vat_code = (request.form.get(f'vat_{i}') or 'standard')
                vat_rate = SWISS_VAT_RATES.get(vat_code, 0.081)
                if desc and qty > 0 and price >= 0:
                    items.append({'description': desc, 'qty': qty, 'unit_price': price,
                                  'vat_code': vat_code, 'vat_rate': vat_rate})
            if not name or not items:
                flash(_('Veuillez renseigner le client et au moins un article.'), 'error')
                return redirect(url_for('billing'))
            subtotal   = sum(it['qty']*it['unit_price'] for it in items)
            vat_amount = round(sum(it['qty']*it['unit_price']*it['vat_rate'] for it in items), 2)
            total      = round(subtotal + vat_amount, 2)
            inv = Invoice(customer_name=name, customer_email=email, method=method,
                          subtotal=subtotal, vat_amount=vat_amount, total=total,
                          status='pending' if method!='quote' else 'draft')
            db.session.add(inv); db.session.flush()
            for it in items:
                db.session.add(InvoiceItem(invoice_id=inv.id, **it))
            db.session.commit()
            if method == 'pay_now':
                inv.status = 'paid'; db.session.commit()
                flash(_('Paiement validé.'), 'success')
            elif method == 'pay_on_pickup':
                flash(_('Commande enregistrée. Paiement au retrait.'), 'success')
            else:
                flash(_('Devis généré.'), 'success')
            return redirect(url_for('invoice_view', invoice_id=inv.id))
        return render_template('billing.html')

    @app.route('/invoice/<int:invoice_id>')
    @staff_required
    def invoice_view(invoice_id):
        inv   = Invoice.query.get_or_404(invoice_id)
        items = InvoiceItem.query.filter_by(invoice_id=inv.id).all()
        return render_template('invoice.html', inv=inv, items=items,
                               vat_rate=int(SWISS_VAT_RATE*1000)/10)

    # PDF facture
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.units import mm

    def build_invoice_pdf(inv, items):
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        y = height - 30*mm
        c.setFont("Helvetica-Bold", 14); c.drawString(20*mm, y, f"Facture/Devis #{inv.id}")
        y -= 8*mm; c.setFont("Helvetica", 10)
        c.drawString(20*mm, y, f"Client: {inv.customer_name}  |  Email: {inv.customer_email or '-'}")
        y -= 10*mm; c.setFont("Helvetica-Bold", 10)
        c.drawString(20*mm, y, "Article"); c.drawString(100*mm, y, "Qté")
        c.drawString(115*mm, y, "PU"); c.drawString(135*mm, y, "TVA"); c.drawString(155*mm, y, "Montant")
        y -= 6*mm; c.line(20*mm, y, 190*mm, y); y -= 4*mm; c.setFont("Helvetica", 10)
        for it in items:
            if y < 30*mm:
                c.showPage(); y = height - 30*mm
            amount = (it.qty or 0) * (it.unit_price or 0.0)
            c.drawString(20*mm, y, (it.description or "")[:40])
            c.drawRightString(110*mm, y, str(it.qty))
            c.drawRightString(132*mm, y, f"{it.unit_price:.2f}")
            c.drawRightString(150*mm, y, f"{(it.vat_rate*100):.1f}%")
            c.drawRightString(190*mm, y, f"{amount:.2f}")
            y -= 6*mm
        y -= 6*mm; c.line(120*mm, y, 190*mm, y); y -= 6*mm
        c.drawRightString(170*mm, y, "Sous-total:"); c.drawRightString(190*mm, y, f"{inv.subtotal:.2f}"); y -= 6*mm
        c.drawRightString(170*mm, y, "TVA:"); c.drawRightString(190*mm, y, f"{inv.vat_amount:.2f}"); y -= 6*mm
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(170*mm, y, "Total:"); c.drawRightString(190*mm, y, f"{inv.total:.2f}")
        c.showPage(); c.save(); buf.seek(0); return buf

    @app.route("/invoice/<int:invoice_id>/pdf")
    @staff_required
    def invoice_pdf(invoice_id):
        inv   = Invoice.query.get_or_404(invoice_id)
        items = InvoiceItem.query.filter_by(invoice_id=inv.id).all()
        pdf   = build_invoice_pdf(inv, items)
        return send_file(pdf, mimetype="application/pdf",
                         as_attachment=True, download_name=f"invoice_{invoice_id}.pdf")

    @app.route("/invoice/<int:invoice_id>/email", methods=["POST"])
    @staff_required
    def invoice_email(invoice_id):
        inv = Invoice.query.get_or_404(invoice_id)
        if not inv.customer_email:
            flash(_("Aucune adresse e-mail fournie pour ce client."), "error")
            return redirect(url_for("invoice_view", invoice_id=invoice_id))
        items = InvoiceItem.query.filter_by(invoice_id=inv.id).all()
        pdf   = build_invoice_pdf(inv, items)
        msg   = Message(subject=f"Votre facture/devis #{invoice_id}",
                        recipients=[inv.customer_email])
        msg.body = _("Veuillez trouver ci-joint votre facture/devis.")
        msg.attach(f"invoice_{invoice_id}.pdf", "application/pdf", pdf.read())
        try:
            mail.send(msg)
            flash(_("E-mail envoyé."), "success")
        except Exception as e:
            flash(_("E-mail non configuré ou erreur d'envoi : ") + str(e), "error")
        return redirect(url_for("invoice_view", invoice_id=invoice_id))

    # ===== Assistant README =====================================================
    @app.route("/assistant")
    def assistant():
        return render_template("assistant.html")

    @app.route("/api/readme")
    def api_readme():
        readme_path = os.path.join(app.root_path, "README.md")
        if not os.path.exists(readme_path):
            return jsonify({"lines": []})
        with open(readme_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f.readlines()]
        return jsonify({"lines": lines})

    @app.route("/api/coach", methods=["POST"])
    def api_coach():
        q = (request.json or {}).get("q", "").lower()
        tips = []
        if "flask"    in q: tips.append("Utilisez des Blueprints pour modulariser votre application Flask.")
        if "sqlite"   in q or "sqlalchemy" in q: tips.append("Activez echo=True de SQLAlchemy en dev pour inspecter les requêtes.")
        if "css"      in q or "responsive" in q: tips.append("Adoptez CSS Grid et testez 360/768/1024px.")
        if not tips: tips = ["Précisez votre besoin (Flask, DB, Front, Déploiement, Tests)."]
        return jsonify({"answer": " ".join(tips)})

    # ===== Redirections legacy ==================================================
    @app.route('/index', methods=["GET","POST"])
    def legacy_index(): return redirect(url_for("index"))

    @app.route('/contactus.html')
    def legacy_contact_page(): return redirect(url_for("contact"))

    @app.route('/android_form.html', methods=["GET","POST"])
    def legacy_android_page(): return redirect(url_for("android_form"))

    @app.route('/ios_form.html', methods=["GET","POST"])
    def legacy_ios_page(): return redirect(url_for("ios_form"))

    @app.route('/kemalphonesolutions.js')
    def legacy_js():
        return send_from_directory(os.path.join(app.static_folder, 'js'), 'main.js')

    return app  # ← return INSIDE create_app()


# ===== Entrée ==================================================================
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
