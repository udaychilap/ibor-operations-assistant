from app.db.connection import get_conn


def investigate_break(recon_id: int):
    with get_conn() as conn:

        # ---------------------------------------------------------
        # 1. Reconciliation record
        # ---------------------------------------------------------
        recon = conn.execute(
            """
            SELECT *
            FROM ibor_txn_recon_record
            WHERE recon_id = %s
            """,
            (recon_id,),
        ).fetchone()

        if not recon:
            return None

        source_txn_id = recon["source_txn_id"]
        business_date = recon["business_date"]

        # ---------------------------------------------------------
        # 2. External transaction
        # ---------------------------------------------------------
        source = conn.execute(
            """
            SELECT *
            FROM source_transaction
            WHERE source_txn_id = %s
            """,
            (source_txn_id,),
        ).fetchone()

        # ---------------------------------------------------------
        # 3. IBOR transaction
        # ---------------------------------------------------------
        ibor = conn.execute(
            """
            SELECT *
            FROM ibor_transaction
            WHERE source_txn_id = %s
            """,
            (source_txn_id,),
        ).fetchone()

        # ---------------------------------------------------------
        # 4. Matching ingestion reject
        # ---------------------------------------------------------
        reject = conn.execute(
            """
            SELECT *
            FROM ibor_load_reject
            WHERE raw_record ->> 'source_txn_id' = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (source_txn_id,),
        ).fetchone()

        # ---------------------------------------------------------
        # 5. Latest ingestion job for business date
        # ---------------------------------------------------------
        job = conn.execute(
            """
            SELECT *
            FROM ibor_job_run
            WHERE business_date = %s
              AND job_name = 'TRANSACTION_INGESTION'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (business_date,),
        ).fetchone()

    status = recon["recon_status"]

    comparison = {}

    root_cause = recon["break_reason"]

    recommended_action = None

    # -------------------------------------------------------------
    # MISMATCH
    # -------------------------------------------------------------
    if status == "MISMATCH":

        if source and ibor:

            source_qty = float(source["quantity"])
            ibor_qty = float(ibor["quantity"])

            source_amount = float(source["amount"])
            ibor_amount = float(ibor["amount"])

            comparison = {
                "external_quantity": source_qty,
                "ibor_quantity": ibor_qty,
                "quantity_difference": round(
                    source_qty - ibor_qty, 4
                ),
                "external_amount": source_amount,
                "ibor_amount": ibor_amount,
                "amount_difference": round(
                    source_amount - ibor_amount, 2
                ),
            }

            differences = []

            if source_qty != ibor_qty:
                differences.append("quantity")

            if source_amount != ibor_amount:
                differences.append("amount")

            root_cause = (
                "Mismatch detected in "
                + " and ".join(differences)
                + "."
            )

            recommended_action = (
                "Compare the external and IBOR transaction values. "
                "Validate the source-of-record values and correct or "
                "replay the transaction only after identifying which "
                "side contains the incorrect data."
            )

    # -------------------------------------------------------------
    # UNPAIR-EXT
    # -------------------------------------------------------------
    elif status == "UNPAIR-EXT":

        if reject:

            root_cause = (
                "The external transaction is missing from IBOR and "
                "a matching ingestion reject was found."
            )

            recommended_action = (
                "Review the ingestion reject reason, correct the "
                "underlying data issue, and replay the transaction."
            )

        else:

            root_cause = (
                "The external transaction exists but no corresponding "
                "IBOR transaction was found. No matching ingestion "
                "reject was found."
            )

            recommended_action = (
                "Investigate the ingestion and interface processing "
                "path to determine why the transaction did not reach "
                "IBOR. Review job execution and downstream processing "
                "before replaying the transaction."
            )

    # -------------------------------------------------------------
    # UNPAIR-INT
    # -------------------------------------------------------------
    elif status == "UNPAIR-INT":

        root_cause = (
            "The transaction exists in IBOR but no corresponding "
            "external source transaction was found."
        )

        recommended_action = (
            "Validate whether the transaction was created internally, "
            "whether the external feed is delayed, or whether the "
            "source transaction identifier is incorrect."
        )

    # -------------------------------------------------------------
    # Operational evidence
    # -------------------------------------------------------------
    operational_context = {
        "external_transaction_found": source is not None,
        "ibor_transaction_found": ibor is not None,
        "matching_reject_found": reject is not None,
        "matching_reject": dict(reject) if reject else None,
        "ingestion_job": dict(job) if job else None,
    }

    return {
        "recon_id": recon["recon_id"],
        "business_date": str(recon["business_date"]),
        "source_txn_id": recon["source_txn_id"],
        "account_id": recon["account_id"],
        "security_id": recon["security_id"],
        "recon_status": status,
        "break_reason": recon["break_reason"],
        "comparison": comparison,
        "root_cause": root_cause,
        "recommended_action": recommended_action,
        "operational_context": operational_context,
        "external_transaction": dict(source) if source else None,
        "ibor_transaction": dict(ibor) if ibor else None,
    }
