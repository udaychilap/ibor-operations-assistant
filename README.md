# IBOR Operations Assistant — Phase 1

A local learning/demo project that simulates an upstream accounting/custodian transaction feed, ingests it into an IBOR-like store, records operational audit results, and performs transaction reconciliation.

## Architecture

Upstream synthetic CSV -> validation -> SOURCE_TRANSACTION -> IBOR_TRANSACTION -> transaction reconciliation -> API diagnostics

This project uses synthetic data only and does not reproduce proprietary Charles River schemas.

## Prerequisites (Mac)

- Docker Desktop running
- Python 3.11+
- Terminal

## 1. Start PostgreSQL

The Docker database is exposed on **localhost:5433** so it does not conflict with a local PostgreSQL instance on 5432.

```bash
cd ibor-operations-assistant
docker compose up -d
```

Check it:

```bash
docker compose ps
```

## 2. Verify database tables

```bash
docker exec -it ibor-postgres psql -U ibor_user -d ibor_db
```

Inside psql:

```sql
\dt
SELECT * FROM ibor_account;
SELECT * FROM ibor_security;
\q
```

Tables created automatically:

- ibor_account
- ibor_security
- source_transaction
- ibor_transaction
- ibor_job_run
- ibor_load_reject
- ibor_txn_recon_record

## 3. Configure Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 4. Generate an inbound transaction file

```bash
python -m app.generator.generate_data --count 25 --scenario normal
```

The file is written to:

```text
data/inbound/transactions.csv
```

Available generator scenarios:

```bash
python -m app.generator.generate_data --scenario normal
python -m app.generator.generate_data --scenario bad_account
python -m app.generator.generate_data --scenario duplicate
```

## 5. Start FastAPI

```bash
uvicorn app.main:app --reload --port 8000
```

Open Swagger UI in your browser at `http://127.0.0.1:8000/docs`.

## 6. Run the IBOR flow

### Health check

```bash
curl http://127.0.0.1:8000/health
```

### Ingest the generated transaction file

```bash
curl -X POST 'http://127.0.0.1:8000/ingest'
```

Expected result resembles:

```json
{"status":"SUCCESS","input_count":25,"success_count":25,"reject_count":0}
```

### Run transaction reconciliation

```bash
curl -X POST 'http://127.0.0.1:8000/reconcile'
```

### View reconciliation breaks

```bash
curl http://127.0.0.1:8000/recon/breaks
```

### View latest ingestion jobs

```bash
curl http://127.0.0.1:8000/jobs/latest
```

### View rejected records

```bash
curl http://127.0.0.1:8000/rejects
```

## pgAdmin connection

Register a new server in pgAdmin:

```text
Name: IBOR Project
Host: 127.0.0.1
Port: 5433
Maintenance database: ibor_db
Username: ibor_user
Password: ibor_password
```

## Important reset command

The SQL scripts under `sql/` run automatically only when PostgreSQL initializes a new Docker volume. To completely reset the demo database:

```bash
docker compose down -v
docker compose up -d
```

This deletes all demo database data.

## Phase 1 database flow

```text
CSV file
   |
   v
IBOR_JOB_RUN
   |
   +---- invalid row ---> IBOR_LOAD_REJECT
   |
   v
SOURCE_TRANSACTION
   |
   v
IBOR_TRANSACTION
   |
   v
IBOR_TXN_RECON_RECORD
       |       |        |        |
     PAIRED UNPAIR-EXT UNPAIR-INT MISMATCH
```

## Next phases

Phase 2: positions, T-1/T calculations and position reconciliation.

Phase 3: cash, tax lots, BOD snapshots and promotion simulation.

Phase 4: operational question router + SQL diagnostics + document RAG, allowing questions such as "Did today's IBOR load complete?", "Why did recon break?", and "Which account caused the failure?".
