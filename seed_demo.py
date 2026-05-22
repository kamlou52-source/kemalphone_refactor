
# seed_demo.py — Génère des données de démonstration
from app import app, db, User, UserInput, Invoice, InvoiceItem, SWISS_VAT_RATES
from datetime import datetime, timedelta
from random import choice, randint, random

def main():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Utilisateurs
        admin = User(email="admin@example.com"); admin.set_password("Admin#123"); admin.role="admin"
        staff = User(email="staff@example.com"); staff.set_password("Staff#123"); staff.role="staff"
        user  = User(email="user@example.com");  user.set_password("User#123");  user.role="user"
        db.session.add_all([admin, staff, user]); db.session.commit()

        # User inputs
        models = ["Android Samsung","Android Pixel","iPhone 14","iPhone 13","iPhone 12","iPhone 11"]
        problems = ["Écran cassé","Batterie faible","Caméra floue","Port de charge","Lent/trop chaud","Ne s'allume plus"]
        for _ in range(20):
            ui = UserInput(fname=choice(["Amine","Sara","Leo","Maya","Noah","Lina","Adam","Emma"]),
                           modele=choice(models),
                           problem=choice(problems))
            ui.created = datetime.utcnow() - timedelta(days=randint(0,300), hours=randint(0,60))
            db.session.add(ui)
        db.session.commit()

        # Factures
        vat_codes = list(SWISS_VAT_RATES.keys())
        for i in range(8):
            inv = Invoice(customer_name=choice(["Société Alpha","Mme Dubois","M. Martin","SARL Beta","Mme Rossi","M. Keller"]),
                          customer_email="client{}@mail.com".format(i+1),
                          method=choice(["quote","pay_now","pay_on_pickup"]),
                          status="draft")
            db.session.add(inv); db.session.flush()
            line_count = randint(1,3)
            subtotal = 0.0; vat_amount = 0.0
            for j in range(line_count):
                qty = randint(1,3)
                price = choice([49.0, 79.0, 99.0, 129.0, 149.0, 199.0])
                vat_code = choice(vat_codes)
                vat_rate = SWISS_VAT_RATES[vat_code]
                item = InvoiceItem(invoice_id=inv.id, description=f"Prestation {j+1}", qty=qty, unit_price=price, vat_code=vat_code, vat_rate=vat_rate)
                db.session.add(item)
                subtotal += qty*price
                vat_amount += qty*price*vat_rate
            inv.subtotal = round(subtotal,2)
            inv.vat_amount = round(vat_amount,2)
            inv.total = round(inv.subtotal + inv.vat_amount, 2)
            inv.status = choice(["draft","pending","paid"])
            inv.created = datetime.utcnow() - timedelta(days=randint(0,20))
        db.session.commit()

        print("✅ Données de démonstration créées.")
        print("Comptes :")
        print(" - admin@example.com / Admin#123")
        print(" - staff@example.com / Staff#123")
        print(" - user@example.com  / User#123")

if __name__ == "__main__":
    main()
