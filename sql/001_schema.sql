CREATE TABLE IF NOT EXISTS ibor_account (
  account_id VARCHAR(32) PRIMARY KEY,
  account_name VARCHAR(100) NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS ibor_security (
  security_id VARCHAR(32) PRIMARY KEY,
  symbol VARCHAR(20) NOT NULL UNIQUE,
  security_name VARCHAR(120) NOT NULL,
  asset_class VARCHAR(30) NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'USD'
);
CREATE TABLE IF NOT EXISTS source_transaction (
  source_txn_id VARCHAR(64) PRIMARY KEY,
  account_id VARCHAR(32) NOT NULL REFERENCES ibor_account(account_id),
  security_id VARCHAR(32) NOT NULL REFERENCES ibor_security(security_id),
  txn_type VARCHAR(16) NOT NULL CHECK (txn_type IN ('BUY','SELL')),
  trade_date DATE NOT NULL,
  settle_date DATE NOT NULL,
  quantity NUMERIC(20,6) NOT NULL CHECK (quantity > 0),
  price NUMERIC(20,6) NOT NULL CHECK (price >= 0),
  amount NUMERIC(20,2) NOT NULL,
  currency CHAR(3) NOT NULL,
  source_file VARCHAR(255),
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS ibor_transaction (
  ibor_txn_id BIGSERIAL PRIMARY KEY,
  source_txn_id VARCHAR(64) UNIQUE,
  account_id VARCHAR(32) NOT NULL REFERENCES ibor_account(account_id),
  security_id VARCHAR(32) NOT NULL REFERENCES ibor_security(security_id),
  txn_type VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL,
  settle_date DATE NOT NULL,
  quantity NUMERIC(20,6) NOT NULL,
  price NUMERIC(20,6) NOT NULL,
  amount NUMERIC(20,2) NOT NULL,
  currency CHAR(3) NOT NULL,
  load_run_id UUID,
  loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS ibor_job_run (
  run_id UUID PRIMARY KEY,
  job_name VARCHAR(80) NOT NULL,
  business_date DATE NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN ('STARTED','SUCCESS','FAILED','PARTIAL')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  input_count INTEGER NOT NULL DEFAULT 0,
  success_count INTEGER NOT NULL DEFAULT 0,
  reject_count INTEGER NOT NULL DEFAULT 0,
  error_message TEXT
);
CREATE TABLE IF NOT EXISTS ibor_load_reject (
  reject_id BIGSERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES ibor_job_run(run_id),
  source_file VARCHAR(255),
  row_number INTEGER,
  raw_record JSONB,
  reject_reason TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS ibor_txn_recon_record (
  recon_id BIGSERIAL PRIMARY KEY,
  business_date DATE NOT NULL,
  source_txn_id VARCHAR(64),
  ibor_txn_id BIGINT,
  account_id VARCHAR(32),
  security_id VARCHAR(32),
  recon_status VARCHAR(20) NOT NULL CHECK (recon_status IN ('PAIRED','UNPAIR-EXT','UNPAIR-INT','MISMATCH')),
  break_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_source_txn_date ON source_transaction(trade_date);
CREATE INDEX IF NOT EXISTS idx_ibor_txn_date ON ibor_transaction(trade_date);
CREATE INDEX IF NOT EXISTS idx_recon_date_status ON ibor_txn_recon_record(business_date,recon_status);
