# 🇨🇭 GUIDE OUTILS SUISSE & INTÉGRATIONS PAIEMENTS
## Optimisé pour e-commerce Suisse

---

## 📋 RÉSUMÉ EXÉCUTIF

Pour le marché suisse, vous devez prioriser:
1. **Paiements**: Stripe (carte + SEPA) + Twint (natif CH)
2. **Logistique**: La Poste Suisse API (étiquettes auto)
3. **Marketing**: Hootsuite (scheduling multi-canaux)
4. **Email**: SendGrid + Brevo (RGPD compliant)
5. **Compliance**: TVA CH 7.7%, Loi fédérale retours

---

## 💳 PAIEMENTS SUISSE

### 1️⃣ STRIPE (Solution principale)

#### Caractéristiques
```
✅ Accepte: Cartes (Visa, MC, Amex), SEPA, iDEAL, Bancontact
✅ PSD2 / 3D Secure obligatoire (SCA)
✅ TVA remise auto en Suisse
✅ Webhook fiables
✅ SDK & documentation excellent
❌ Frais: 1.4–2.9% + CHF 0.30 / transaction
❌ Délai virement: 2–3 jours
```

#### Inscription compte marchand Suisse

```bash
# 1. Aller sur https://stripe.com/ch
# 2. Sign up → Business type: E-commerce
# 3. Pays: Switzerland
# 4. TVA: 7.7% (auto-applied)
# 5. Bank: IBAN suisse
# 6. Receive API keys: sk_live_... & pk_live_...
```

#### Configuration Flask

```python
# config/stripe_config.py

import stripe
import os

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Configuration produits Stripe
PRODUCTS_STRIPE = {
    'shipping_ch_std': 'price_1O...',  # Livraison standard CH (CHF 9.90)
    'shipping_ch_express': 'price_1O...',  # Express (CHF 19.90)
}
```

#### Implémentation checkout

```python
# routes/checkout.py

from flask import Blueprint, request, jsonify, render_template
import stripe
from models import db, Order, OrderItem, Product, User

checkout_bp = Blueprint('checkout', __name__, url_prefix='/api/checkout')

@checkout_bp.route('/create-session', methods=['POST'])
def create_session():
    """
    Créer une session de paiement Stripe
    """
    data = request.get_json()
    user_id = data.get('user_id')
    cart_items = data.get('items')  # [{product_id: 1, qty: 2}, ...]
    shipping_address = data.get('address')
    
    # Calculs
    line_items = []
    subtotal = 0
    
    for item in cart_items:
        product = Product.query.get(item['product_id'])
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        amount_chf = int(float(product.price_chf) * 100)
        subtotal += amount_chf * item['qty']
        
        line_items.append({
            'price_data': {
                'currency': 'chf',
                'unit_amount': amount_chf,
                'product_data': {
                    'name': product.name,
                    'description': product.description,
                    'images': [product.image_url] if product.image_url else [],
                    'metadata': {'product_id': product.id}
                }
            },
            'quantity': item['qty']
        })
    
    # Frais de port (exemple: CHF 9.90 standard)
    shipping_amount = 990  # en centimes
    line_items.append({
        'price_data': {
            'currency': 'chf',
            'unit_amount': shipping_amount,
            'product_data': {
                'name': 'Frais de port (La Poste Standard)',
                'type': 'service'
            }
        },
        'quantity': 1
    })
    
    # Créer commande temporaire
    order = Order(
        order_number=f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        user_id=user_id,
        subtotal_chf=subtotal / 100,
        shipping_chf=shipping_amount / 100,
        tax_chf=0,  # Calculated after
        total_chf=(subtotal + shipping_amount) / 100,
        shipping_address=shipping_address,
        status='pending'
    )
    
    # Ajouter items
    for i, item in enumerate(cart_items):
        order_item = OrderItem(
            product_id=item['product_id'],
            quantity=item['qty'],
            price_at_purchase=Product.query.get(item['product_id']).price_chf
        )
        order.items.append(order_item)
    
    db.session.add(order)
    db.session.commit()
    
    # Créer session Stripe
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],  # Ajouter 'ideal' pour Benelux
            line_items=line_items,
            mode='payment',
            success_url=f"{request.base_url.rstrip('/')}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{request.base_url.rstrip('/')}/cancel?order_id={order.id}",
            metadata={
                'order_id': order.id,
                'user_id': user_id
            },
            # Adresse pour facturation
            billing_address_collection='required',
            customer_email=User.query.get(user_id).email,
        )
        
        # Sauvegarder session Stripe
        order.stripe_session_id = session.id
        db.session.commit()
        
        return jsonify({
            'sessionId': session.id,
            'orderId': order.id
        }), 200
        
    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400

@checkout_bp.route('/success', methods=['GET'])
def success():
    """Callback après paiement réussi"""
    session_id = request.args.get('session_id')
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Récupérer commande
        order = Order.query.filter_by(stripe_session_id=session_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Marquer comme payée
        if session.payment_status == 'paid':
            order.status = 'paid'
            order.payment_method = 'stripe'
            
            # Réduire stock
            for item in order.items:
                item.product.stock_qty -= item.quantity
            
            db.session.commit()
            
            # Envoyer confirmation email (async)
            from celery_app import celery
            from tasks import send_order_confirmation_email
            send_order_confirmation_email.delay(order.id)
            
            return render_template('checkout_success.html', order=order), 200
        
        return jsonify({'error': 'Payment not confirmed'}), 400
        
    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400

@checkout_bp.route('/cancel', methods=['GET'])
def cancel():
    """Callback si client annule"""
    order_id = request.args.get('order_id')
    order = Order.query.get(order_id)
    if order and order.status == 'pending':
        order.status = 'cancelled'
        db.session.commit()
    return render_template('checkout_cancel.html', order=order), 200
```

#### Webhook Stripe

```python
# routes/webhooks.py

from flask import Blueprint, request, jsonify
import stripe
from models import db, Order

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhooks')

@webhooks_bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    """
    Webhook Stripe pour événements paiement
    """
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            os.getenv('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Traiter événements
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order = Order.query.filter_by(stripe_session_id=session.id).first()
        
        if order:
            order.status = 'paid'
            order.payment_method = 'stripe'
            db.session.commit()
            
            # Déclencher traitement commande
            # from tasks import process_order
            # process_order.delay(order.id)
    
    elif event['type'] == 'charge.refunded':
        charge = event['data']['object']
        # Gérer remboursement
    
    return jsonify({'success': True}), 200
```

---

### 2️⃣ TWINT (Paiement Suisse natif)

#### Caractéristiques
```
✅ Paiement mobile dominant en Suisse (80% SMEs)
✅ Pas de frais de change (CHF natif)
✅ Paiement par QR code
✅ Simple et rapide
❌ Frais: 1.8–2.5% (plus haut que Stripe)
❌ Limite: ~CHF 200 / transaction
❌ Documentation moins complète
```

#### Inscription

```bash
# 1. Aller sur https://business.twint.app
# 2. KYC complet (entreprise)
# 3. Compte bancaire suisse requis
# 4. Obtenir API credentials
```

#### Intégration Flask

```python
# integrations/twint.py

import requests
import os
from datetime import datetime, timedelta
import hmac
import hashlib

class TwintGateway:
    
    def __init__(self):
        self.api_key = os.getenv('TWINT_API_KEY')
        self.merchant_id = os.getenv('TWINT_MERCHANT_ID')
        self.api_url = 'https://pay.twint.ch/api/v1'  # Production
    
    def generate_signature(self, data: dict) -> str:
        """Générer signature HMAC-SHA256 pour requête"""
        payload = ''.join(f"{k}={v}" for k, v in sorted(data.items()))
        signature = hmac.new(
            self.api_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def create_payment_request(self, amount_chf: float, order_id: str):
        """
        Créer une requête de paiement Twint
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        payload = {
            'amount': int(amount_chf * 100),  # En centimes
            'currency': 'CHF',
            'merchantId': self.merchant_id,
            'orderId': order_id,
            'timestamp': timestamp,
            'callback': f'{os.getenv("APP_URL")}/webhooks/twint',
        }
        
        signature = self.generate_signature(payload)
        
        headers = {
            'X-Signature': signature,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f'{self.api_url}/payment-requests',
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                'success': True,
                'qr_code': data.get('qrCode'),
                'request_id': data.get('requestId'),
                'expires_at': data.get('expiresAt')
            }
        
        except requests.RequestException as e:
            return {'success': False, 'error': str(e)}
    
    def verify_payment(self, request_id: str) -> dict:
        """Vérifier statut du paiement"""
        try:
            response = requests.get(
                f'{self.api_url}/payment-requests/{request_id}',
                headers={
                    'X-API-Key': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                'status': data.get('status'),  # 'PENDING', 'CONFIRMED', 'FAILED'
                'transaction_id': data.get('transactionId'),
                'amount': data.get('amount'),
            }
        
        except requests.RequestException as e:
            return {'error': str(e)}

# Routes Flask
from flask import Blueprint, request, jsonify, render_template
from models import db, Order

twint_bp = Blueprint('twint', __name__, url_prefix='/api/twint')
twint_gateway = TwintGateway()

@twint_bp.route('/initiate', methods=['POST'])
def initiate_payment():
    """Initier paiement Twint"""
    data = request.get_json()
    order_id = data.get('order_id')
    
    order = Order.query.get(order_id)
    if not order or order.status != 'pending':
        return jsonify({'error': 'Invalid order'}), 400
    
    result = twint_gateway.create_payment_request(
        float(order.total_chf),
        order.order_number
    )
    
    if result['success']:
        # Sauvegarder request_id
        order.twint_request_id = result['request_id']
        db.session.commit()
        
        return jsonify({
            'qrCode': result['qr_code'],
            'requestId': result['request_id'],
            'expiresAt': result['expires_at']
        }), 200
    
    return jsonify({'error': result.get('error')}), 400

@twint_bp.route('/status/<request_id>', methods=['GET'])
def check_status(request_id):
    """Vérifier statut du paiement"""
    result = twint_gateway.verify_payment(request_id)
    
    if 'error' not in result:
        order = Order.query.filter_by(twint_request_id=request_id).first()
        
        if result['status'] == 'CONFIRMED' and order:
            order.status = 'paid'
            order.payment_method = 'twint'
            db.session.commit()
        
        return jsonify(result), 200
    
    return jsonify(result), 400

@twint_bp.route('/webhook', methods=['POST'])
def twint_webhook():
    """Webhook Twint"""
    data = request.get_json()
    request_id = data.get('requestId')
    status = data.get('status')
    
    if status == 'CONFIRMED':
        order = Order.query.filter_by(twint_request_id=request_id).first()
        if order:
            order.status = 'paid'
            order.payment_method = 'twint'
            db.session.commit()
    
    return jsonify({'success': True}), 200
```

#### Template checkout avec Twint QR

```html
<!-- templates/checkout_twint.html -->

<div class="payment-method" id="twint-payment">
    <h3>Paiement par Twint</h3>
    
    <div id="qr-container" style="text-align: center;">
        <p>Scannez le code QR avec votre app Twint :</p>
        <img id="qr-code" src="" alt="QR Code Twint" style="width: 250px; height: 250px;">
    </div>
    
    <p style="text-align: center; margin-top: 20px;">
        Vérification en cours...
        <span id="status-spinner">⏳</span>
    </p>
    
    <div id="payment-status"></div>
</div>

<script>
async function initiateTwintPayment(orderId) {
    const response = await fetch('/api/twint/initiate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderId })
    });
    
    const data = await response.json();
    
    if (data.qrCode) {
        document.getElementById('qr-code').src = data.qrCode;
        
        // Poll status
        pollTwintStatus(data.requestId);
    }
}

async function pollTwintStatus(requestId) {
    const maxAttempts = 60;
    let attempts = 0;
    
    const poll = setInterval(async () => {
        const response = await fetch(`/api/twint/status/${requestId}`);
        const data = await response.json();
        
        if (data.status === 'CONFIRMED') {
            clearInterval(poll);
            document.getElementById('payment-status').innerHTML = 
                '✅ Paiement confirmé! Redirection...';
            window.location.href = '/checkout/success';
        } else if (data.status === 'FAILED') {
            clearInterval(poll);
            document.getElementById('payment-status').innerHTML = 
                '❌ Paiement échoué.';
        }
        
        attempts++;
        if (attempts >= maxAttempts) {
            clearInterval(poll);
        }
    }, 1000);
}
</script>
```

---

## 📦 LOGISTIQUE : LA POSTE SUISSE

### Configuration API

```python
# integrations/laposte.py

import requests
import os
from datetime import datetime

class LaPosteGateway:
    
    def __init__(self):
        self.api_key = os.getenv('LA_POSTE_API_KEY')
        self.base_url = os.getenv('LA_POSTE_API_URL', 
            'https://api.laposte.ch/v1')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_shipment(self, order_id: int, shipping_address: dict):
        """
        Créer un envoi La Poste et générer étiquette
        """
        from models import Order
        
        order = Order.query.get(order_id)
        if not order:
            return {'error': 'Order not found'}
        
        payload = {
            'recipientAddress': {
                'firstName': shipping_address['first_name'],
                'lastName': shipping_address['last_name'],
                'street': f"{shipping_address['street']} {shipping_address['street_number']}",
                'postalCode': shipping_address['postal_code'],
                'city': shipping_address['city'],
                'country': shipping_address.get('country', 'CH'),
                'phone': shipping_address.get('phone', ''),
            },
            'packages': [
                {
                    'weight': 0.5,  # kg (estimer selon produits)
                    'length': 20,   # cm
                    'width': 15,
                    'height': 10,
                    'contents': 'Electronics',
                }
            ],
            'services': ['STANDARD'],  # STANDARD, EXPRESS
            'reference': order.order_number,
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/shipments',
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Sauvegarder tracking number
            order.tracking_number = data.get('trackingNumber')
            db.session.commit()
            
            return {
                'success': True,
                'tracking_number': data.get('trackingNumber'),
                'label_url': data.get('labelUrl'),  # PDF
                'shipment_id': data.get('shipmentId'),
            }
        
        except requests.RequestException as e:
            return {'error': str(e)}
    
    def get_tracking(self, tracking_number: str):
        """Récupérer statut de suivi"""
        try:
            response = requests.get(
                f'{self.base_url}/shipments/{tracking_number}',
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'status': data.get('status'),
                'events': data.get('events', []),
                'estimated_delivery': data.get('estimatedDeliveryDate'),
            }
        
        except requests.RequestException as e:
            return {'error': str(e)}
    
    def create_return_label(self, order_item_id: int):
        """Générer étiquette retour"""
        from models import OrderItem, Order
        
        order_item = OrderItem.query.get(order_item_id)
        if not order_item:
            return {'error': 'Order item not found'}
        
        order = order_item.order
        
        # Adresse retour (entrepôt EL Kémal)
        return_address = {
            'firstName': 'EL Kémal',
            'lastName': 'Phone Solutions',
            'street': 'Rue de...',
            'postalCode': '1201',
            'city': 'Genève',
            'country': 'CH',
        }
        
        payload = {
            'returnAddress': return_address,
            'originShipmentNumber': order.tracking_number,
            'reference': f"RET-{order.order_number}",
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/return-labels',
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'success': True,
                'label_url': data.get('labelUrl'),
                'return_number': data.get('returnNumber'),
            }
        
        except requests.RequestException as e:
            return {'error': str(e)}

# Routes
from flask import Blueprint, jsonify

laposte_bp = Blueprint('laposte', __name__, url_prefix='/api/shipping')
laposte = LaPosteGateway()

@laposte_bp.route('/shipments/<order_id>', methods=['POST'])
def create_shipment(order_id):
    """Créer expédition"""
    from models import Order
    
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    result = laposte.create_shipment(order_id, order.shipping_address)
    
    if result.get('success'):
        return jsonify(result), 200
    
    return jsonify(result), 400

@laposte_bp.route('/tracking/<tracking_number>', methods=['GET'])
def get_tracking(tracking_number):
    """Suivi colis"""
    result = laposte.get_tracking(tracking_number)
    return jsonify(result), 200
```

---

## 📱 AUTOMATISATION MARKETING : HOOTSUITE

### Configuration

```python
# integrations/hootsuite.py

import requests
import os
from datetime import datetime

class HootsuiteGateway:
    
    def __init__(self):
        self.api_token = os.getenv('HOOTSUITE_API_TOKEN')
        self.base_url = 'https://platform.hootsuite.com/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
    
    def schedule_post(self, content: str, platforms: list, 
                      schedule_time: str, image_url: str = None):
        """
        Programmer un post sur plusieurs réseaux
        
        platforms: ['instagram', 'facebook', 'linkedin', 'tiktok']
        schedule_time: ISO format (2024-06-15T14:30:00Z)
        """
        payload = {
            'socialProfiles': [
                self._get_profile_id(platform) for platform in platforms
            ],
            'message': content,
            'media': [{'type': 'image', 'url': image_url}] if image_url else [],
            'scheduledDate': schedule_time,
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/posts',
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            return {
                'success': True,
                'post_id': data.get('id'),
                'scheduled_time': schedule_time
            }
        
        except requests.RequestException as e:
            return {'error': str(e)}
    
    def get_analytics(self, platform: str, start_date: str, end_date: str):
        """
        Récupérer statistiques engagement
        """
        params = {
            'socialProfiles': self._get_profile_id(platform),
            'startDate': start_date,
            'endDate': end_date,
        }
        
        try:
            response = requests.get(
                f'{self.base_url}/analytics/engagement',
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
        
        except requests.RequestException as e:
            return {'error': str(e)}
    
    def _get_profile_id(self, platform):
        """Mapper platform name vers Hootsuite profile ID"""
        profiles = {
            'instagram': os.getenv('HOOTSUITE_INSTAGRAM_PROFILE_ID'),
            'facebook': os.getenv('HOOTSUITE_FACEBOOK_PROFILE_ID'),
            'linkedin': os.getenv('HOOTSUITE_LINKEDIN_PROFILE_ID'),
            'tiktok': os.getenv('HOOTSUITE_TIKTOK_PROFILE_ID'),
        }
        return profiles.get(platform)

# Routes
from flask import Blueprint, request, jsonify

hootsuite_bp = Blueprint('hootsuite', __name__, url_prefix='/api/social')
hootsuite = HootsuiteGateway()

@hootsuite_bp.route('/posts/schedule', methods=['POST'])
def schedule_post():
    """Programmer un post"""
    data = request.get_json()
    
    result = hootsuite.schedule_post(
        content=data.get('content'),
        platforms=data.get('platforms', ['instagram', 'facebook']),
        schedule_time=data.get('schedule_time'),
        image_url=data.get('image_url')
    )
    
    if result.get('success'):
        # Sauvegarder en DB pour tracking
        post = SocialPost(
            content=data.get('content'),
            platforms=','.join(data.get('platforms')),
            scheduled_at=data.get('schedule_time'),
            hootsuite_post_id=result['post_id'],
            status='scheduled'
        )
        db.session.add(post)
        db.session.commit()
        
        return jsonify(result), 200
    
    return jsonify(result), 400

@hootsuite_bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Récupérer analytics"""
    platform = request.args.get('platform', 'instagram')
    start_date = request.args.get('start_date', '2024-05-01')
    end_date = request.args.get('end_date', '2024-06-01')
    
    result = hootsuite.get_analytics(platform, start_date, end_date)
    return jsonify(result), 200
```

### Template d'admin pour scheduler posts

```html
<!-- templates/admin/schedule_post.html -->

<form id="schedule-post-form">
    <h2>Programmer un Post</h2>
    
    <label>Contenu:</label>
    <textarea name="content" required placeholder="Écrivez votre message..."></textarea>
    
    <label>Image:</label>
    <input type="file" name="image" accept="image/*">
    
    <label>Réseaux:</label>
    <div>
        <label><input type="checkbox" name="platforms" value="instagram"> Instagram</label>
        <label><input type="checkbox" name="platforms" value="facebook"> Facebook</label>
        <label><input type="checkbox" name="platforms" value="linkedin"> LinkedIn</label>
        <label><input type="checkbox" name="platforms" value="tiktok"> TikTok</label>
    </div>
    
    <label>Date & Heure:</label>
    <input type="datetime-local" name="schedule_time" required>
    
    <button type="submit">Programmer</button>
</form>

<script>
document.getElementById('schedule-post-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const content = formData.get('content');
    const platforms = formData.getAll('platforms');
    const schedule_time = new Date(formData.get('schedule_time')).toISOString();
    
    // Upload image
    let image_url = null;
    if (formData.has('image')) {
        const file = formData.get('image');
        const imgData = new FormData();
        imgData.append('file', file);
        const imgRes = await fetch('/api/upload', { method: 'POST', body: imgData });
        const imgJson = await imgRes.json();
        image_url = imgJson.url;
    }
    
    const response = await fetch('/api/social/posts/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            content,
            platforms,
            schedule_time,
            image_url
        })
    });
    
    const data = await response.json();
    if (data.success) {
        alert('✅ Post programmé avec succès!');
        e.target.reset();
    } else {
        alert('❌ Erreur: ' + data.error);
    }
});
</script>
```

---

## 📧 EMAIL TRANSACTIONNEL : SENDGRID

### Configuration

```python
# config/email.py

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, Content

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', 'contact@elkemaphone.ch')

def send_email(to_email: str, subject: str, html_content: str):
    """Envoyer email via SendGrid"""
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        
        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        response = sg.send(message)
        return {'success': True, 'message_id': response.headers.get('X-Message-Id')}
    
    except Exception as e:
        return {'error': str(e)}

# Utilisation dans Celery task
from celery import shared_task
from flask import render_template

@shared_task
def send_order_confirmation(order_id: int):
    """Tâche asynchrone: envoyer confirmation"""
    from models import Order
    
    order = Order.query.get(order_id)
    if not order:
        return
    
    html = render_template('emails/order_confirmation.html', order=order)
    
    send_email(
        to_email=order.user.email,
        subject=f"Confirmation de votre commande {order.order_number}",
        html_content=html
    )
```

---

## 🏦 CONFORMITÉ SUISSE

### TVA Configuration

```python
# config/tax.py

# TVA Suisse
TAXES = {
    'CH': 0.077,  # 7.7% taux réduit pour électronique reconditionnée
}

def calculate_tax(amount_chf: float, country: str = 'CH') -> float:
    """Calculer montant TVA"""
    tax_rate = TAXES.get(country, 0)
    return amount_chf * tax_rate

def calculate_total_with_tax(amount_chf: float, country: str = 'CH') -> tuple:
    """Retourner (amount, tax, total)"""
    tax = calculate_tax(amount_chf, country)
    return (amount_chf, tax, amount_chf + tax)

# Utilisation
subtotal = 100.00
tax = calculate_tax(subtotal)
total = subtotal + tax
# Résultat: 100.00 + 7.70 = 107.70 CHF
```

### RGPD/LPD (Loi sur la protection des données)

```html
<!-- templates/privacy/cookie_consent.html -->

<div id="cookie-banner" class="cookie-banner">
    <h3>🍪 Cookies & Données personnelles</h3>
    <p>
        Nous utilisons des cookies pour améliorer votre expérience.
        <a href="/privacy-policy" target="_blank">Lire notre politique de confidentialité</a>
    </p>
    <button id="accept-cookies" class="btn-primary">Accepter</button>
    <button id="reject-cookies" class="btn-secondary">Refuser</button>
</div>

<script>
document.getElementById('accept-cookies').addEventListener('click', () => {
    localStorage.setItem('cookies_accepted', 'true');
    document.getElementById('cookie-banner').remove();
});
</script>
```

---

## 📋 CHECKLIST INTEGRATION OUTILS SUISSE

- [ ] Compte Stripe CH créé + keys configurées
- [ ] Compte Twint inscription faite
- [ ] API La Poste credentials obtenues
- [ ] Hootsuite account créé + réseaux sociaux connectés
- [ ] SendGrid API key configurée
- [ ] `.env` complété avec tous les credentials
- [ ] Webhook endpoints testés (Stripe, La Poste, Twint)
- [ ] Tests unitaires pour chaque intégration
- [ ] Documentation des APIs créée
- [ ] Conformité RGPD/TVA validée

---

**Next step: Phase 2 (Catalogue)** 🚀
