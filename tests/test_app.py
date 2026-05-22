import pytest
from kemalphone_refactor import app, db, User, UserInput, Invoice, InvoiceItem, SWISS_VAT_RATES

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # seed admin, staff, user
            admin = User(email="admin@test.com"); admin.set_password("pass"); admin.role="admin"
            staff = User(email="staff@test.com"); staff.set_password("pass"); staff.role="staff"
            user = User(email="user@test.com"); user.set_password("pass"); user.role="user"
            db.session.add_all([admin, staff, user]); db.session.commit()
        yield client

def login(client, email, password="pass"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)

def test_userinput_form_validation(client):
    # simulate posting empty data
    rv = client.post("/userinput", data={}, follow_redirects=True)
    html = rv.get_data(as_text=True)
    assert "Prénom invalide" in html or "erreur" in html.lower()

def test_invoice_multi_vat(client):
    with app.app_context():
        inv = Invoice(customer_name="Test", customer_email="t@t", method="quote", subtotal=0, vat_amount=0, total=0)
        db.session.add(inv); db.session.flush()
        # Add items with different VAT
        db.session.add(InvoiceItem(invoice_id=inv.id, description="A", qty=1, unit_price=100, vat_code="standard", vat_rate=SWISS_VAT_RATES["standard"]))
        db.session.add(InvoiceItem(invoice_id=inv.id, description="B", qty=2, unit_price=50, vat_code="reduit", vat_rate=SWISS_VAT_RATES["reduit"]))
        db.session.commit()
        items = InvoiceItem.query.filter_by(invoice_id=inv.id).all()
        subtotal = sum(it.qty*it.unit_price for it in items)
        vat = sum(it.qty*it.unit_price*it.vat_rate for it in items)
        assert round(subtotal,2) == 200
        assert round(vat,2) == round(100*0.081 + 2*50*0.026,2)

def test_role_access_control(client):
    # user should not access /billing
    login(client,"user@test.com")
    rv = client.get("/billing", follow_redirects=True)
    assert b"Acc" in rv.data  # access denied message

    # staff can access /billing
    login(client,"staff@test.com")
    rv = client.get("/billing")
    assert rv.status_code == 200

    # admin can access /stats
    login(client,"admin@test.com")
    rv = client.get("/stats")
    assert rv.status_code == 200

def test_stripe_webhook_simulation(client):
    # Post fake webhook with checkout.session.completed
    import json as pyjson
    payload = pyjson.dumps({
        "id":"evt_test",
        "type":"checkout.session.completed",
        "data":{"object":{"metadata":{"invoice_id":"1"}}}
    })
    # create invoice id 1
    with app.app_context():
        inv = Invoice(customer_name="T", customer_email="t", method="pay_now", subtotal=10, vat_amount=1, total=11, status="pending")
        db.session.add(inv); db.session.commit()
    rv = client.post("/stripe/webhook", data=payload, content_type="application/json")
    assert rv.status_code == 200
    with app.app_context():
        inv = Invoice.query.get(1)
        assert inv.status == "paid"
