import csv
import json
import uuid
from datetime import date
from pathlib import Path

from app.db.connection import get_conn


def ingest_csv(path: str):
    run_id = uuid.uuid4()
    p = Path(path)

    with p.open() as f:
        rows = list(csv.DictReader(f))

    ok = 0
    rejects = 0

    with get_conn() as conn:

        conn.execute(
            """
            INSERT INTO ibor_job_run(
                run_id,
                job_name,
                business_date,
                status,
                input_count
            )
            VALUES(
                %s,
                'TRANSACTION_INGESTION',
                %s,
                'STARTED',
                %s
            )
            """,
            (
                run_id,
                date.today(),
                len(rows)
            )
        )

        for n, r in enumerate(rows, 2):

            try:
                with conn.transaction():

                    # -------------------------------------------------
                    # Validate Account
                    # -------------------------------------------------
                    acct = conn.execute(
                        """
                        SELECT 1
                        FROM ibor_account
                        WHERE account_id = %s
                        """,
                        (r["account_id"],)
                    ).fetchone()

                    if not acct:
                        raise ValueError(
                            f"Unknown account {r['account_id']}"
                        )

                    # -------------------------------------------------
                    # Validate Security
                    # -------------------------------------------------
                    sec = conn.execute(
                        """
                        SELECT 1
                        FROM ibor_security
                        WHERE security_id = %s
                        """,
                        (r["security_id"],)
                    ).fetchone()

                    if not sec:
                        raise ValueError(
                            f"Unknown security {r['security_id']}"
                        )

                    # -------------------------------------------------
                    # Detect synthetic demo scenarios
                    # -------------------------------------------------
                    scenario_unpair_ext = (
                        r["source_txn_id"].startswith("UNPAIR-EXT-")
                    )

                    scenario_unpair_int = (
                        r["source_txn_id"].startswith("UNPAIR-INT-")
                    )

                    scenario_mismatch = (
                        r["source_txn_id"].startswith("MISMATCH-")
                    )

                    # -------------------------------------------------
                    # Base values from external feed
                    # -------------------------------------------------
                    source_values = (
                        r["source_txn_id"],
                        r["account_id"],
                        r["security_id"],
                        r["txn_type"],
                        r["trade_date"],
                        r["settle_date"],
                        r["quantity"],
                        r["price"],
                        r["amount"],
                        r["currency"],
                        p.name
                    )

                    # -------------------------------------------------
                    # External / Source side
                    # -------------------------------------------------
                    #
                    # UNPAIR-INT means:
                    # IBOR has the transaction,
                    # but external source does not.
                    #
                    # Therefore, skip source_transaction insert.
                    # -------------------------------------------------
                    if not scenario_unpair_int:

                        conn.execute(
                            """
                            INSERT INTO source_transaction(
                                source_txn_id,
                                account_id,
                                security_id,
                                txn_type,
                                trade_date,
                                settle_date,
                                quantity,
                                price,
                                amount,
                                currency,
                                source_file
                            )
                            VALUES(
                                %s,%s,%s,%s,%s,
                                %s,%s,%s,%s,%s,%s
                            )
                            """,
                            source_values
                        )

                    # -------------------------------------------------
                    # IBOR side
                    # -------------------------------------------------
                    #
                    # UNPAIR-EXT means:
                    # transaction exists externally,
                    # but IBOR does not have it.
                    #
                    # Therefore, skip ibor_transaction insert.
                    # -------------------------------------------------
                    if not scenario_unpair_ext:

                        ibor_quantity = r["quantity"]
                        ibor_amount = r["amount"]

                        # ---------------------------------------------
                        # MISMATCH scenario
                        # ---------------------------------------------
                        #
                        # External and IBOR transactions both exist,
                        # but quantity and amount differ.
                        # ---------------------------------------------
                        if scenario_mismatch:

                            ibor_quantity = str(
                                float(r["quantity"]) + 5
                            )

                            ibor_amount = str(
                                round(
                                    float(ibor_quantity)
                                    * float(r["price"]),
                                    2
                                )
                            )

                        ibor_values = (
                            r["source_txn_id"],
                            r["account_id"],
                            r["security_id"],
                            r["txn_type"],
                            r["trade_date"],
                            r["settle_date"],
                            ibor_quantity,
                            r["price"],
                            ibor_amount,
                            r["currency"],
                            run_id
                        )

                        conn.execute(
                            """
                            INSERT INTO ibor_transaction(
                                source_txn_id,
                                account_id,
                                security_id,
                                txn_type,
                                trade_date,
                                settle_date,
                                quantity,
                                price,
                                amount,
                                currency,
                                load_run_id
                            )
                            VALUES(
                                %s,%s,%s,%s,%s,
                                %s,%s,%s,%s,%s,%s
                            )
                            """,
                            ibor_values
                        )

                ok += 1

            except Exception as e:

                rejects += 1

                conn.execute(
                    """
                    INSERT INTO ibor_load_reject(
                        run_id,
                        source_file,
                        row_number,
                        raw_record,
                        reject_reason
                    )
                    VALUES(
                        %s,%s,%s,%s,%s
                    )
                    """,
                    (
                        run_id,
                        p.name,
                        n,
                        json.dumps(r),
                        str(e)
                    )
                )

        # ---------------------------------------------------------
        # Determine overall ingestion status
        # ---------------------------------------------------------
        if rejects == 0:
            status = "SUCCESS"

        elif ok == 0:
            status = "FAILED"

        else:
            status = "PARTIAL"

        # ---------------------------------------------------------
        # Update job run
        # ---------------------------------------------------------
        conn.execute(
            """
            UPDATE ibor_job_run
            SET
                status = %s,
                completed_at = NOW(),
                success_count = %s,
                reject_count = %s
            WHERE run_id = %s
            """,
            (
                status,
                ok,
                rejects,
                run_id
            )
        )

        conn.commit()

    return {
        "run_id": str(run_id),
        "status": status,
        "input_count": len(rows),
        "success_count": ok,
        "reject_count": rejects
    }