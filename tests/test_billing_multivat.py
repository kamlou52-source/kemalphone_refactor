
from app import db, Invoice, InvoiceItem, SWISS_VAT_RATES

def test_multi_vat_calculation(client, db):
    # Login as staff
    from app import User
    u = User(email="s@test.com"); u.set_password("pw"); u.role="staff"
    db.session.add(u); db.session.commit()
    client.post("/login", data={"email":"s@test.com", "password":"pw"}, follow_redirects=True)

    # Create invoice with 2 lines, different VAT
    data = {
        "customer_name":"Test Co",
        "customer_email":"co@test.com",
        "method":"pay_on_pickup",
        "items_count":"2",
        "desc_1":"Line A",
        "qty_1":"2",
        "price_1":"100",
        "vat_1":"standard",  # 8.1%
        "desc_2":"Line B",
        "qty_2":"1",
        "price_2":"50",
        "vat_2":"reduit",    # 2.6%
    }
    r = client.post("/billing", data=data, follow_redirects=True)
    assert r.status_code == 200
    inv = Invoice.query.order_by(Invoice.id.desc()).first()
    assert inv is not None
    # Expected subtotal = 2*100 + 1*50 = 250
    # VAT = 200*0.081 + 50*0.026 = 16.2 + 1.3 = 17.5
    assert round(inv.subtotal,2) == 250.00
    assert round(inv.vat_amount,1) == 17.5
    assert round(inv.total,2) == 267.50
