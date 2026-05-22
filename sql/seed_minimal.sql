-- Données de test minimales
-- À exécuter dans la base: kemaldb

-- Quelques demandes utilisateur
INSERT INTO userinput (fname, modele, problem)
VALUES
  ('Alice', 'iPhone 12', 'Écran fissuré'),
  ('Marc',  'Samsung Galaxy S21', 'Batterie qui se décharge vite'),
  ('Nora',  'iPad Pro 11', 'Connecteur USB-C endommagé');

-- Un quicktoken de démonstration (non lié à un user)
INSERT INTO quicktoken (token, purpose, user_id, created, expires_at)
VALUES ('demo-qr-token', 'login', NULL, NOW(), NOW() + INTERVAL '10 minutes')
ON CONFLICT (token) DO NOTHING;

-- Un devis d’exemple + sa ligne (CTE pour récupérer l'id)
WITH inv AS (
  INSERT INTO invoice (customer_name, customer_email, method, subtotal, vat_amount, total, status)
  VALUES ('Client Démo', 'client.demo@example.com', 'quote',
          100.00, ROUND(100.00 * 0.081, 2), ROUND(100.00 + ROUND(100.00 * 0.081, 2), 2),
          'draft')
  RETURNING id
)
INSERT INTO invoiceitem (invoice_id, description, qty, unit_price, vat_code, vat_rate)
SELECT id, 'Remplacement écran', 1, 100.00, 'standard', 0.081
FROM inv;

-- Un second exemple "payé"
WITH inv2 AS (
  INSERT INTO invoice (customer_name, customer_email, method, subtotal, vat_amount, total, status)
  VALUES ('Société Exemple SA', 'compta@example.com', 'pay_now',
          249.90, ROUND(249.90 * 0.081, 2), ROUND(249.90 + ROUND(249.90 * 0.081, 2), 2),
          'paid')
  RETURNING id
)
INSERT INTO invoiceitem (invoice_id, description, qty, unit_price, vat_code, vat_rate)
SELECT id, 'Remplacement batterie premium', 1, 249.90, 'standard', 0.081
FROM inv2;
