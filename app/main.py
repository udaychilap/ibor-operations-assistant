from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.db.connection import get_conn
from app.services.ai_assistant import ai_chat, ai_investigate_break
from app.services.ingestion import ingest_csv
from app.services.investigation import investigate_break
from app.services.reconciliation import reconcile


app = FastAPI(
    title="IBOR Operations Assistant - Phase 1",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    scope: Literal["selected", "all"] = "selected"
    recon_id: int | None = None
    business_date: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


@app.post("/demo/reset")
def reset_demo():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                TRUNCATE TABLE
                    ibor_txn_recon_record,
                    ibor_load_reject,
                    ibor_transaction,
                    source_transaction,
                    ibor_job_run
                RESTART IDENTITY CASCADE
                """
            )

    return {
        "status": "SUCCESS",
        "message": "Demo operational data reset successfully",
    }


@app.get("/health")
def health():
    with get_conn() as conn:
        conn.execute("SELECT 1").fetchone()

    return {"status": "ok"}


@app.post("/ingest")
def ingest(file: str = "data/inbound/transactions.csv"):
    try:
        return ingest_csv(file)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Inbound file not found",
        )


@app.post("/reconcile")
def recon():
    return reconcile()


@app.get("/recon/breaks")
def breaks():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM ibor_txn_recon_record
            WHERE recon_status <> 'PAIRED'
            ORDER BY recon_id DESC
            LIMIT 100
            """
        ).fetchall()

    return rows


@app.get("/recon/breaks/{recon_id}")
def break_detail(recon_id: int):
    result = investigate_break(recon_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Reconciliation record not found",
        )

    return result


@app.post("/assistant/investigate/{recon_id}")
def assistant_investigate(recon_id: int):
    result = ai_investigate_break(recon_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Reconciliation record not found",
        )

    return result


@app.post("/assistant/chat")
def assistant_chat(request: ChatRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty",
        )

    if request.scope == "selected" and request.recon_id is None:
        raise HTTPException(
            status_code=400,
            detail="recon_id is required for selected scope",
        )

    try:
        history = [
            message.model_dump()
            for message in request.history
        ]

        result = ai_chat(
            question=question,
            scope=request.scope,
            recon_id=request.recon_id,
            business_date=request.business_date,
            history=history,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        print("AI CHAT ERROR:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="AI assistant failed to process the question.",
        )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=(
                "No reconciliation evidence was found "
                "for the requested context."
            ),
        )

    return result


@app.get("/jobs/latest")
def latest_jobs():
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT *
            FROM ibor_job_run
            ORDER BY started_at DESC
            LIMIT 20
            """
        ).fetchall()


@app.get("/rejects")
def rejects():
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT *
            FROM ibor_load_reject
            ORDER BY reject_id DESC
            LIMIT 100
            """
        ).fetchall()


@app.post("/demo/unpair-ext")
def demo_unpair_ext():
    with get_conn() as conn:
        with conn.cursor() as cur:
            txn = cur.execute(
                """
                SELECT
                    s.source_txn_id,
                    s.account_id,
                    s.security_id,
                    s.txn_type,
                    s.quantity,
                    s.price
                FROM source_transaction s
                JOIN ibor_transaction i
                  ON i.source_txn_id = s.source_txn_id
                ORDER BY s.source_txn_id DESC
                LIMIT 1
                """
            ).fetchone()

            if not txn:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "No ingested transactions available. "
                        "Run ingestion first."
                    ),
                )

            cur.execute(
                """
                DELETE FROM ibor_transaction
                WHERE source_txn_id = %s
                """,
                (txn["source_txn_id"],),
            )

    return {
        "status": "SUCCESS",
        "scenario": "UNPAIR-EXT",
        "source_txn_id": txn["source_txn_id"],
        "account_id": txn["account_id"],
        "security_id": txn["security_id"],
        "txn_type": txn["txn_type"],
        "quantity": float(txn["quantity"]),
        "price": float(txn["price"]),
        "message": (
            "External transaction exists but corresponding "
            "IBOR transaction was removed."
        ),
    }
