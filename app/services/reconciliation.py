from datetime import date
from app.db.connection import get_conn

def reconcile(business_date=None):
    d=business_date or date.today()
    with get_conn() as conn:
        conn.execute('DELETE FROM ibor_txn_recon_record WHERE business_date=%s',(d,))
        conn.execute('''INSERT INTO ibor_txn_recon_record(business_date,source_txn_id,ibor_txn_id,account_id,security_id,recon_status,break_reason)
        SELECT %s,s.source_txn_id,i.ibor_txn_id,s.account_id,s.security_id,
        CASE WHEN i.ibor_txn_id IS NULL THEN 'UNPAIR-EXT'
             WHEN s.quantity<>i.quantity OR s.amount<>i.amount THEN 'MISMATCH' ELSE 'PAIRED' END,
        CASE WHEN i.ibor_txn_id IS NULL THEN 'External transaction not found in IBOR'
             WHEN s.quantity<>i.quantity OR s.amount<>i.amount THEN 'Quantity or amount mismatch' END
        FROM source_transaction s LEFT JOIN ibor_transaction i ON i.source_txn_id=s.source_txn_id WHERE s.trade_date=%s''',(d,d))
        conn.execute('''INSERT INTO ibor_txn_recon_record(business_date,source_txn_id,ibor_txn_id,account_id,security_id,recon_status,break_reason)
        SELECT %s,i.source_txn_id,i.ibor_txn_id,i.account_id,i.security_id,'UNPAIR-INT','IBOR transaction not found in external source'
        FROM ibor_transaction i LEFT JOIN source_transaction s ON s.source_txn_id=i.source_txn_id WHERE i.trade_date=%s AND s.source_txn_id IS NULL''',(d,d))
        conn.commit()
        rows=conn.execute('SELECT recon_status,COUNT(*) count FROM ibor_txn_recon_record WHERE business_date=%s GROUP BY recon_status ORDER BY recon_status',(d,)).fetchall()
    return {'business_date':str(d),'summary':rows}
