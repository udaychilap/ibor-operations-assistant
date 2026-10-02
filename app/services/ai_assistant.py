import json

from openai import OpenAI

from app.config import settings
from app.db.connection import get_conn
from app.services.investigation import investigate_break


client = OpenAI(api_key=settings.openai_api_key)


SYSTEM_INSTRUCTIONS = """
You are an IBOR Operations Assistant supporting investment operations.

You help operations analysts investigate transaction reconciliation
breaks using ONLY operational evidence supplied by the application.

The application contains:
- external/source transactions
- IBOR transactions
- transaction reconciliation results
- ingestion rejects
- ingestion job information

Important rules:

1. Do not invent transactions, job failures, rejects, causes,
   account activity, or system events.

2. Clearly distinguish confirmed evidence from possible
   investigation paths.

3. Do not claim a transaction was rejected unless a matching
   reject record exists in the supplied evidence.

4. A PARTIAL ingestion job does not prove that a specific
   investigated transaction was rejected.

5. Do not change or second-guess the deterministic
   reconciliation status.

6. Use concise investment-operations terminology.

7. Recommend investigation steps before recommending replay
   or correction when root cause is not confirmed.

8. If evidence is insufficient, explicitly say that the root
   cause is not confirmed.

9. UNPAIR-EXT means the external/source transaction exists but
   the corresponding IBOR transaction was not found.

10. UNPAIR-INT means the IBOR transaction exists but the
    corresponding external/source transaction was not found.

11. MISMATCH means both transactions exist but one or more
    reconciled values differ.

12. PAIRED means the deterministic reconciliation successfully
    matched the transaction.

13. When answering questions across multiple reconciliation
    records, summarize only what can be established from the
    supplied reconciliation evidence.

14. If the user asks which break should be investigated first,
    do not invent business priority. Explain the available
    operational factors that may be used for prioritization,
    such as break type, frequency, affected account, evidence
    of ingestion reject, or size of mismatch.

15. Keep responses readable for an investment-operations analyst.

When useful, structure answers with headings such as:

Summary:
Confirmed Evidence:
Assessment:
Recommended Actions:
"""


def ai_investigate_break(recon_id: int):
    evidence = investigate_break(recon_id)

    if not evidence:
        return None

    prompt = f"""
Investigate the following IBOR reconciliation break.

Operational evidence:

{json.dumps(evidence, default=str, indent=2)}

Provide the response with these sections:

Summary:
Confirmed Evidence:
Assessment:
Recommended Actions:
"""

    response = client.responses.create(
        model=settings.openai_model,
        instructions=SYSTEM_INSTRUCTIONS,
        input=prompt,
    )

    return {
        "recon_id": recon_id,
        "recon_status": evidence["recon_status"],
        "source_txn_id": evidence["source_txn_id"],
        "model": settings.openai_model,
        "ai_explanation": response.output_text,
        "evidence": evidence,
    }


def get_all_recon_evidence(
    business_date=None,
    limit: int = 100,
):
    """
    Build deterministic evidence for questions that concern
    the complete reconciliation run.

    This intentionally retrieves database evidence before
    sending anything to the model.
    """

    with get_conn() as conn:

        if business_date:
            date_row = conn.execute(
                """
                SELECT %s::date AS business_date
                """,
                (business_date,),
            ).fetchone()
        else:
            date_row = conn.execute(
                """
                SELECT MAX(business_date) AS business_date
                FROM ibor_txn_recon_record
                """
            ).fetchone()

        if not date_row or not date_row["business_date"]:
            return None

        resolved_date = date_row["business_date"]

        summary_rows = conn.execute(
            """
            SELECT
                recon_status,
                COUNT(*) AS count
            FROM ibor_txn_recon_record
            WHERE business_date = %s
            GROUP BY recon_status
            ORDER BY recon_status
            """,
            (resolved_date,),
        ).fetchall()

        break_rows = conn.execute(
            """
            SELECT
                recon_id,
                business_date,
                source_txn_id,
                ibor_txn_id,
                account_id,
                security_id,
                recon_status,
                break_reason
            FROM ibor_txn_recon_record
            WHERE business_date = %s
              AND recon_status <> 'PAIRED'
            ORDER BY recon_id DESC
            LIMIT %s
            """,
            (resolved_date, limit),
        ).fetchall()

        account_rows = conn.execute(
            """
            SELECT
                account_id,
                COUNT(*) AS break_count
            FROM ibor_txn_recon_record
            WHERE business_date = %s
              AND recon_status <> 'PAIRED'
            GROUP BY account_id
            ORDER BY break_count DESC, account_id
            LIMIT 50
            """,
            (resolved_date,),
        ).fetchall()

        security_rows = conn.execute(
            """
            SELECT
                security_id,
                COUNT(*) AS break_count
            FROM ibor_txn_recon_record
            WHERE business_date = %s
              AND recon_status <> 'PAIRED'
            GROUP BY security_id
            ORDER BY break_count DESC, security_id
            LIMIT 50
            """,
            (resolved_date,),
        ).fetchall()

        job = conn.execute(
            """
            SELECT *
            FROM ibor_job_run
            WHERE business_date = %s
              AND job_name = 'TRANSACTION_INGESTION'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (resolved_date,),
        ).fetchone()

        reject_rows = conn.execute(
            """
            SELECT
                reject_reason,
                COUNT(*) AS reject_count
            FROM ibor_load_reject
            GROUP BY reject_reason
            ORDER BY reject_count DESC
            LIMIT 50
            """
        ).fetchall()

    return {
        "business_date": str(resolved_date),
        "reconciliation_summary": [dict(row) for row in summary_rows],
        "break_count": len(break_rows),
        "breaks": [dict(row) for row in break_rows],
        "accounts_with_breaks": [dict(row) for row in account_rows],
        "securities_with_breaks": [dict(row) for row in security_rows],
        "latest_ingestion_job": dict(job) if job else None,
        "reject_summary": [dict(row) for row in reject_rows],
    }


def format_history(history):
    """
    Keep a small amount of conversational context.

    Database evidence remains authoritative. Conversation
    history is only used to understand follow-up questions.
    """

    if not history:
        return "No previous conversation."

    lines = []

    for message in history[-8:]:
        if isinstance(message, dict):
            role = message.get("role", "unknown")
            content = message.get("content", "")
        else:
            role = getattr(message, "role", "unknown")
            content = getattr(message, "content", "")

        if not content:
            continue

        lines.append(f"{role.upper()}: {content}")

    if not lines:
        return "No previous conversation."

    return "\n".join(lines)


def ai_chat(
    question: str,
    scope: str,
    recon_id=None,
    business_date=None,
    history=None,
):
    if scope not in {"selected", "all"}:
        raise ValueError("scope must be 'selected' or 'all'")

    if scope == "selected":
        if recon_id is None:
            raise ValueError("recon_id is required for selected scope")

        evidence = investigate_break(int(recon_id))

        if not evidence:
            return None

        evidence_count = 1
        context_description = f"Selected reconciliation record #{recon_id}"

    else:
        evidence = get_all_recon_evidence(business_date=business_date)

        if not evidence:
            return None

        evidence_count = evidence.get("break_count", 0)
        context_description = (
            "Complete reconciliation run "
            f"for business date {evidence['business_date']}"
        )

    conversation = format_history(history)

    prompt = f"""
The operations analyst is asking a question about IBOR
transaction reconciliation.

Scope:
{context_description}

Current question:
{question}

Recent conversation:
{conversation}

Authoritative operational evidence:

{json.dumps(evidence, default=str, indent=2)}

Answer the analyst's current question directly.

Requirements:

- Base the answer only on the supplied evidence.
- Do not invent missing information.
- If the question cannot be answered from the evidence,
  say what evidence would be required.
- Clearly distinguish confirmed facts from possible causes.
- For a selected break, focus on that reconciliation record.
- For all-recon scope, summarize patterns across the supplied
  reconciliation records.
- When giving recommended actions, explain the operational
  reason for each action.
- Keep the answer concise but useful.
"""

    response = client.responses.create(
        model=settings.openai_model,
        instructions=SYSTEM_INSTRUCTIONS,
        input=prompt,
    )

    return {
        "answer": response.output_text,
        "model": settings.openai_model,
        "scope": scope,
        "recon_id": recon_id if scope == "selected" else None,
        "business_date": evidence.get("business_date"),
        "evidence_count": evidence_count,
    }
