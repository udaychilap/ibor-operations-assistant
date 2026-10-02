INSERT INTO ibor_account(account_id, account_name) VALUES
('UMA10001','Demo Growth Account'),('UMA10002','Demo Balanced Account'),('UMA10003','Demo Income Account')
ON CONFLICT DO NOTHING;
INSERT INTO ibor_security(security_id,symbol,security_name,asset_class) VALUES
('SEC-AAPL','AAPL','Apple Inc.','EQUITY'),('SEC-MSFT','MSFT','Microsoft Corp.','EQUITY'),('SEC-IBM','IBM','International Business Machines','EQUITY'),('SEC-TLT','TLT','iShares 20+ Year Treasury Bond ETF','FIXED_INCOME')
ON CONFLICT DO NOTHING;
