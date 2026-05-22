-- Schéma PostgreSQL pour l’application Kemal Phone Solutions
-- À exécuter dans la base: kemaldb

-- =========================
-- Table: user (utilisateurs)
-- =========================
CREATE TABLE IF NOT EXISTS "user" (
  id            SERIAL PRIMARY KEY,
  email         VARCHAR(120) UNIQUE NOT NULL,
  password_hash VARCHAR(200)       NOT NULL,
  role          VARCHAR(20)        NOT NULL DEFAULT 'user'
);

-- ==================================
-- Table: userinput (demandes clients)
-- ==================================
CREATE TABLE IF NOT EXISTS userinput (
  id      SERIAL PRIMARY KEY,
  fname   VARCHAR(50)  NOT NULL,
  modele  VARCHAR(80)  NOT NULL,
  problem VARCHAR(255) NOT NULL,
  created TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ==============================================
-- Table: quicktoken (jetons de connexion par QR)
-- ==============================================
CREATE TABLE IF NOT EXISTS quicktoken (
  id         SERIAL PRIMARY KEY,
  token      VARCHAR(64) UNIQUE NOT NULL,
  purpose    VARCHAR(32)        NOT NULL DEFAULT 'login',
  user_id    INTEGER NULL REFERENCES "user"(id) ON DELETE SET NULL,
  created    TIMESTAMP          NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP          NOT NULL
);

-- ===========================================
-- Table: invoice (factures / devis)
-- ===========================================
CREATE TABLE IF NOT EXISTS invoice (
  id             SERIAL PRIMARY KEY,
  customer_name  VARCHAR(120) NOT NULL,
  customer_email VARCHAR(120),
  method         VARCHAR(20)  NOT NULL DEFAULT 'quote',  -- quote | pay_now | pay_on_pickup
  subtotal       NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  vat_amount     NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  total          NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  status         VARCHAR(20)   NOT NULL DEFAULT 'draft', -- draft | paid | pending
  created        TIMESTAMP     NOT NULL DEFAULT NOW()
);

-- ===========================================
-- Table: invoiceitem (lignes de facture)
-- ===========================================
CREATE TABLE IF NOT EXISTS invoiceitem (
  id          SERIAL PRIMARY KEY,
  invoice_id  INTEGER NOT NULL REFERENCES invoice(id) ON DELETE CASCADE,
  description VARCHAR(200) NOT NULL,
  qty         INTEGER      NOT NULL DEFAULT 1,
  unit_price  NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  vat_code    VARCHAR(10)   NOT NULL DEFAULT 'standard',
  vat_rate    NUMERIC(5,3)  NOT NULL DEFAULT 0.081
);

-- =======================
-- Index utiles / perf
-- =======================
CREATE INDEX IF NOT EXISTS ix_userinput_created
  ON userinput (created DESC);

CREATE INDEX IF NOT EXISTS ix_user_email
  ON "user" (email);

CREATE INDEX IF NOT EXISTS ix_invoiceitem_invoice_id
  ON invoiceitem (invoice_id);

-- Un index dédié sur token (en plus de UNIQUE si besoin d’analyses)
CREATE INDEX IF NOT EXISTS ix_quicktoken_token
  ON quicktoken (token);
