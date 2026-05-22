
import json

def test_stripe_webhook_marks_paid(client, db):
    # Create an invoice
    from app import Invoice, db
    inv = Invoice(customer_name="Stripe Test", method="pay_now", subtotal=100.0, vat_amount=8.1, total=108.1, status="pending")
    db.session.add(inv); db.session.commit()

    # Send webhook event without signature (dev mode path)
    event = {
        "type":"checkout.session.completed",
        "data":{"object":{"metadata":{"invoice_id":str(inv.id)}}}
    }
    r = client.post("/stripe/webhook", data=json.dumps(event), headers={"Content-Type":"application/json"})
    assert r.status_code == 200

    # Verify
    inv = Invoice.query.get(inv.id)
    assert inv.status == "paid"
