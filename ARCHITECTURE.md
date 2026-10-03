IBOR Operations Assistant — Architecture

1. Overview

The IBOR Operations Assistant is an investment-operations application designed to demonstrate transaction ingestion, IBOR reconciliation, break investigation, and evidence-grounded AI-assisted analysis.

The core architectural principle is:

Deterministic systems establish operational facts. AI explains those facts but does not create or alter them.

The application separates transaction processing from AI interpretation so that reconciliation results remain reproducible, auditable, and independent of the language model.

The current implementation includes:

* CSV-based transaction ingestion
* reference-data validation
* IBOR transaction persistence
* deterministic transaction reconciliation
* reconciliation break classification
* ingestion reject capture
* job-run tracking
* deterministic break investigation
* evidence-grounded AI explanations
* conversational reconciliation analysis
* React/Vite user interface
* FastAPI backend
* PostgreSQL persistence
* Dockerized PostgreSQL runtime

⸻

2. Architecture Principles

The project follows several architectural principles.

2.1 Deterministic processing before AI

Transaction validation, ingestion, reconciliation, and break classification are performed entirely by application and database logic.

The AI model cannot modify:

* transaction data
* reconciliation status
* reconciliation results
* reject records
* job status

The model receives previously established operational evidence and generates an explanation.

⸻

2.2 Evidence-grounded AI

Before an AI request is made, the backend retrieves authoritative evidence from PostgreSQL.

For a selected reconciliation break, this can include:

* reconciliation record
* external/source transaction
* IBOR transaction
* matching ingestion reject
* ingestion job
* quantity differences
* amount differences
* deterministic break reason

The model is explicitly instructed not to invent missing information.

⸻

2.3 Clear separation of concerns

The backend is divided into services with distinct responsibilities.

app/
├── main.py
├── config.py
├── db/
│   └── connection.py
├── generator/
│   └── generate_data.py
└── services/
    ├── ingestion.py
    ├── reconciliation.py
    ├── investigation.py
    └── ai_assistant.py

Each service performs a specific part of the operational workflow.

⸻

2.4 Operational traceability

The system records ingestion runs and rejected records so that reconciliation breaks can be investigated using operational evidence rather than assumptions.

Important operational tables include:

* ibor_job_run
* ibor_load_reject
* source_transaction
* ibor_transaction
* ibor_txn_recon_record

⸻

3. High-Level Architecture

flowchart TD
    A[External Transaction CSV] --> B[FastAPI Ingestion Endpoint]
    B --> C[Ingestion Service]
    C --> D{Reference Data Validation}
    D -->|Valid| E[Source Transaction]
    D -->|Invalid| F[Load Reject]
    E --> G[IBOR Transaction]
    C --> H[Job Run]
    E --> I[Reconciliation Service]
    G --> I
    I --> J[Reconciliation Records]
    J --> K{Recon Status}
    K --> L[PAIRED]
    K --> M[MISMATCH]
    K --> N[UNPAIR-EXT]
    K --> O[UNPAIR-INT]
    M --> P[Investigation Service]
    N --> P
    O --> P
    P --> Q[Operational Evidence]
    Q --> R[AI Assistant Service]
    R --> S[OpenAI Model]
    S --> T[Evidence-Grounded Explanation]
    T --> U[React UI]

⸻

4. Runtime Architecture

The current local runtime is intentionally simple.

┌──────────────────────────────┐
│         React / Vite         │
│      localhost:5173          │
└──────────────┬───────────────┘
               │ HTTP / JSON
               ▼
┌──────────────────────────────┐
│            FastAPI           │
│      127.0.0.1:8000          │
│                              │
│  Ingestion                   │
│  Reconciliation              │
│  Investigation               │
│  AI Assistant                │
└──────────────┬───────────────┘
               │ psycopg
               ▼
┌──────────────────────────────┐
│          PostgreSQL 17       │
│ Docker: ibor-postgres        │
│ Host port: 5433              │
│ Container port: 5432         │
└──────────────────────────────┘
               FastAPI
                  │
                  │ HTTPS
                  ▼
        ┌─────────────────┐
        │ OpenAI API      │
        │ AI Explanation  │
        └─────────────────┘

⸻

5. Component Architecture

5.1 React UI

The frontend is located under:

ui/

The primary application files are:

ui/src/App.jsx
ui/src/App.css
ui/src/index.css
ui/src/main.jsx

The frontend communicates with FastAPI using REST endpoints.

Its responsibilities include:

* triggering ingestion
* triggering reconciliation
* displaying reconciliation results
* displaying breaks
* selecting a break
* viewing investigation evidence
* interacting with the AI Operations Assistant

The frontend does not perform reconciliation logic.

⸻

6. FastAPI Layer

The main API application is implemented in:

app/main.py

FastAPI currently acts as both:

* HTTP routing layer
* lightweight application orchestration layer

The current project keeps route definitions in main.py.

Future versions can separate these into API router modules.

⸻

7. API Endpoints

Health

GET /health

Checks API availability and validates database connectivity using:

SELECT 1

⸻

Reset Demo Data

POST /demo/reset

Clears operational transaction and reconciliation tables while preserving reference data.

Tables reset include:

ibor_txn_recon_record
ibor_load_reject
ibor_transaction
source_transaction
ibor_job_run

⸻

Ingestion

POST /ingest

Default file:

data/inbound/transactions.csv

The endpoint delegates processing to:

app.services.ingestion.ingest_csv()

⸻

Run Reconciliation

POST /reconcile

Executes deterministic transaction reconciliation.

⸻

Retrieve Breaks

GET /recon/breaks

Returns reconciliation records where:

recon_status != PAIRED

⸻

Investigate Break

GET /recon/breaks/{recon_id}

Returns deterministic operational evidence for a specific reconciliation record.

⸻

AI Investigate Break

POST /assistant/investigate/{recon_id}

Retrieves deterministic evidence and sends it to the configured OpenAI model.

⸻

AI Chat

POST /assistant/chat

Supports two scopes:

selected
all

Selected scope

Investigates one reconciliation record.

Requires:

recon_id

All scope

Analyzes the complete reconciliation run for a business date.

⸻

Latest Jobs

GET /jobs/latest

Returns recent ingestion jobs.

⸻

Rejects

GET /rejects

Returns recent ingestion rejects.

⸻

Demo UNPAIR-EXT

POST /demo/unpair-ext

Removes an IBOR transaction while preserving the corresponding external transaction.

This creates a controlled demonstration of:

UNPAIR-EXT

⸻

8. Transaction Ingestion Architecture

Transaction ingestion is implemented in:

app/services/ingestion.py

The ingestion workflow begins with a CSV transaction file.

flowchart TD
    A[CSV File] --> B[Create Job Run]
    B --> C[Read Transaction]
    C --> D{Account Valid?}
    D -->|No| E[Reject Record]
    D -->|Yes| F{Security Valid?}
    F -->|No| E
    F -->|Yes| G[Insert Source Transaction]
    G --> H[Insert IBOR Transaction]
    H --> I[Increment Success Count]
    E --> J[Increment Reject Count]
    I --> K[Continue Processing]
    J --> K
    K --> L[Update Job Status]
    L --> M[SUCCESS / PARTIAL / FAILED]

⸻

9. Ingestion Job Tracking

Each ingestion run receives a UUID.

Example:

run_id = UUID

The run is stored in:

ibor_job_run

The job starts with:

STARTED

At completion, the status becomes:

SUCCESS
PARTIAL
FAILED

The status is determined from:

input_count
success_count
reject_count

⸻

10. Reference Data Validation

Before a transaction is accepted, two reference-data validations occur.

Account validation

The account must exist in:

ibor_account

Unknown accounts generate a load reject.

⸻

Security validation

The security must exist in:

ibor_security

Unknown securities generate a load reject.

⸻

11. Transaction Persistence

The project intentionally maintains two transaction representations.

External transaction

Stored in:

source_transaction

This represents the upstream or external transaction source.

⸻

IBOR transaction

Stored in:

ibor_transaction

This represents the transaction as loaded into the IBOR environment.

Having two stores allows the reconciliation engine to compare the upstream source against the IBOR representation.

⸻

12. Reconciliation Architecture

Reconciliation is implemented in:

app/services/reconciliation.py

The reconciliation engine is deterministic SQL logic.

The AI model is not involved.

The primary match key is:

source_txn_id

External and IBOR transactions are compared for the requested business date.

⸻

13. Reconciliation Statuses

The engine supports four statuses.

PAIRED

Both the external transaction and IBOR transaction exist, and reconciled values agree.

External = Present
IBOR     = Present
Values   = Match

Result:

PAIRED

⸻

MISMATCH

Both transactions exist, but one or more compared values differ.

Current comparisons include:

quantity
amount

Example:

External Quantity: 200
IBOR Quantity:     205
External Amount:   70,956.00
IBOR Amount:       72,729.90

Result:

MISMATCH

⸻

UNPAIR-EXT

The external transaction exists, but the corresponding IBOR transaction does not.

External = Present
IBOR     = Missing

Result:

UNPAIR-EXT

Operational interpretation:

External transaction not found in IBOR

⸻

UNPAIR-INT

The IBOR transaction exists, but the corresponding external transaction does not.

External = Missing
IBOR     = Present

Result:

UNPAIR-INT

Operational interpretation:

IBOR transaction not found in external source

⸻

14. Reconciliation Flow

flowchart TD
    A[External Transaction] --> C{IBOR Transaction Exists?}
    C -->|No| D[UNPAIR-EXT]
    C -->|Yes| E{Quantity and Amount Match?}
    E -->|Yes| F[PAIRED]
    E -->|No| G[MISMATCH]
    H[IBOR Transactions] --> I{External Transaction Exists?}
    I -->|No| J[UNPAIR-INT]

⸻

15. Controlled Demo Scenarios

The transaction generator supports synthetic scenarios used to demonstrate reconciliation behavior.

Scenario detection currently uses transaction ID prefixes.

UNPAIR-EXT

UNPAIR-EXT-*

The external transaction is written.

The IBOR transaction is intentionally skipped.

⸻

UNPAIR-INT

UNPAIR-INT-*

The IBOR transaction is written.

The external transaction is intentionally skipped.

⸻

MISMATCH

MISMATCH-*

Both transactions are written, but the IBOR quantity is altered.

Current demonstration behavior:

IBOR quantity = external quantity + 5

IBOR amount is then recalculated.

This provides predictable test data for reconciliation and investigation.

⸻

16. Investigation Architecture

Break investigation is implemented in:

app/services/investigation.py

This layer is particularly important because it separates deterministic operational analysis from AI explanation.

For a reconciliation ID, the service retrieves:

ibor_txn_recon_record
source_transaction
ibor_transaction
ibor_load_reject
ibor_job_run

It then builds structured evidence.

⸻

17. Investigation Evidence

For a reconciliation break, the investigation service can produce:

{
  "recon_id": 25,
  "business_date": "2026-09-30",
  "source_txn_id": "...",
  "account_id": "...",
  "security_id": "...",
  "recon_status": "MISMATCH",
  "comparison": {},
  "root_cause": "...",
  "recommended_action": "...",
  "operational_context": {},
  "external_transaction": {},
  "ibor_transaction": {}
}

This object becomes the authoritative context for the AI assistant.

⸻

18. Mismatch Investigation

For MISMATCH, the investigation service calculates:

external_quantity
ibor_quantity
quantity_difference
external_amount
ibor_amount
amount_difference

For example:

quantity_difference =
external_quantity - ibor_quantity

and:

amount_difference =
external_amount - ibor_amount

This comparison is deterministic.

⸻

19. UNPAIR-EXT Investigation

For UNPAIR-EXT, the service determines whether a matching ingestion reject exists.

Two different operational conditions are therefore possible.

Matching reject exists

The system has evidence that the transaction encountered an ingestion problem.

Recommended investigation can focus on the reject reason.

No matching reject exists

The system cannot conclude that ingestion rejected the transaction.

The analyst should investigate:

* interface processing
* ingestion path
* downstream processing
* job execution
* transaction propagation

The system intentionally avoids inventing a cause.

⸻

20. UNPAIR-INT Investigation

For UNPAIR-INT, IBOR contains a transaction that cannot be found in the external source.

Possible investigation paths include:

* internally generated transaction
* delayed upstream feed
* incorrect source transaction identifier
* missing upstream transaction

These remain investigation paths unless confirmed by evidence.

⸻

21. AI Assistant Architecture

AI functionality is implemented in:

app/services/ai_assistant.py

The current integration uses the OpenAI Responses API.

The model name is configured through:

OPENAI_MODEL

with a local development default defined in configuration.

The API key is supplied through environment configuration and is not stored in the repository.

⸻

22. AI Evidence Flow

sequenceDiagram
    participant User
    participant UI
    participant API
    participant Investigation
    participant PostgreSQL
    participant AI
    User->>UI: Ask reconciliation question
    UI->>API: POST /assistant/chat
    API->>Investigation: Build evidence
    Investigation->>PostgreSQL: Query operational data
    PostgreSQL-->>Investigation: Deterministic evidence
    Investigation-->>API: Evidence object
    API->>AI: Instructions + evidence + question
    AI-->>API: Explanation
    API-->>UI: Answer
    UI-->>User: Investigation response

The important architectural point is:

Database evidence → AI

not:

AI → database conclusions

⸻

23. AI Guardrails

The system prompt explicitly instructs the model to follow operational rules.

Important guardrails include:

* do not invent transactions
* do not invent rejects
* do not invent failures
* do not invent causes
* do not change deterministic reconciliation status
* distinguish evidence from possible investigation paths
* do not infer that a specific transaction was rejected solely because a job is PARTIAL
* explain when evidence is insufficient
* recommend investigation before replay when root cause is unknown

This reduces hallucination risk in an operations environment.

⸻

24. Selected-Break Chat Scope

When:

scope = selected

the assistant receives evidence only for the selected reconciliation record.

A recon_id is mandatory.

This mode supports questions such as:

Why is this transaction mismatched?
What is different between external and IBOR?
Was this transaction rejected?
What should operations investigate next?

⸻

25. All-Reconciliation Chat Scope

When:

scope = all

the backend builds evidence for the reconciliation run.

This includes:

* business date
* reconciliation status counts
* break records
* accounts with breaks
* securities with breaks
* latest ingestion job
* reject summary

This allows questions such as:

Summarize today's reconciliation failures.
How many breaks occurred?
Which accounts contain breaks?
What types of breaks occurred?

⸻

26. Conversation History

The assistant accepts limited conversation history.

Only the most recent messages are used to understand follow-up questions.

Current implementation retains up to:

8 messages

Conversation history does not override database evidence.

The database remains authoritative.

⸻

27. Database Architecture

PostgreSQL is the persistent operational store.

The major entities are:

erDiagram
    IBOR_ACCOUNT ||--o{ SOURCE_TRANSACTION : contains
    IBOR_ACCOUNT ||--o{ IBOR_TRANSACTION : contains
    IBOR_SECURITY ||--o{ SOURCE_TRANSACTION : references
    IBOR_SECURITY ||--o{ IBOR_TRANSACTION : references
    IBOR_JOB_RUN ||--o{ IBOR_LOAD_REJECT : produces
    SOURCE_TRANSACTION ||--o| IBOR_TXN_RECON_RECORD : reconciles
    IBOR_TRANSACTION ||--o| IBOR_TXN_RECON_RECORD : reconciles

⸻

28. Database Tables

ibor_account

Reference-data table containing accounts.

Important columns:

account_id
account_name
currency
active
created_at

⸻

ibor_security

Reference-data table containing securities.

Important columns:

security_id
symbol
security_name
asset_class
currency

⸻

source_transaction

Stores transactions received from the external source.

Important columns:

source_txn_id
account_id
security_id
txn_type
trade_date
settle_date
quantity
price
amount
currency
source_file
received_at

⸻

ibor_transaction

Stores the IBOR-side representation.

Important columns:

ibor_txn_id
source_txn_id
account_id
security_id
txn_type
trade_date
settle_date
quantity
price
amount
currency
load_run_id
loaded_at

⸻

ibor_job_run

Tracks operational ingestion runs.

Important columns:

run_id
job_name
business_date
status
started_at
completed_at
input_count
success_count
reject_count
error_message

⸻

ibor_load_reject

Stores transactions that fail ingestion validation or persistence.

Important columns:

reject_id
run_id
source_file
row_number
raw_record
reject_reason
created_at

⸻

ibor_txn_recon_record

Stores reconciliation results.

Important columns:

recon_id
business_date
source_txn_id
ibor_txn_id
account_id
security_id
recon_status
break_reason
created_at

⸻

29. Reference Data

The demonstration environment currently contains three accounts.

UMA10001
UMA10002
UMA10003

Sample securities include:

SEC-AAPL
SEC-MSFT
SEC-IBM
SEC-TLT

Reference data is seeded using:

sql/002_seed_reference.sql

⸻

30. Database Indexing

Current indexes include:

source_transaction.trade_date
ibor_transaction.trade_date
ibor_txn_recon_record.business_date + recon_status

These indexes support the major operational queries used by ingestion and reconciliation.

⸻

31. Database Connectivity

Database access is implemented using:

psycopg

with dictionary row support:

row_factory=dict_row

Connection configuration is provided through:

DATABASE_URL

Environment configuration is managed through:

pydantic-settings

⸻

32. Configuration Architecture

Configuration is defined in:

app/config.py

Important settings include:

database_url
inbound_dir
openai_api_key
openai_model

Local settings can be loaded from:

.env

The actual .env file is excluded from Git.

The repository contains:

.env.example

for configuration guidance.

⸻

33. Docker Architecture

PostgreSQL runs through Docker Compose.

Current service:

postgres:17

Container:

ibor-postgres

Local port mapping:

localhost:5433 → postgres:5432

Database initialization scripts are mounted from:

./sql

into:

/docker-entrypoint-initdb.d

This initializes:

001_schema.sql
002_seed_reference.sql

⸻

34. PostgreSQL Persistence

Docker uses the named volume:

ibor_pgdata

This keeps database data persistent across container restarts.

⸻

35. CORS

FastAPI currently allows the local Vite development server:

http://localhost:5173
http://127.0.0.1:5173

Production environments should replace this configuration with explicit production origins.

⸻

36. Current Security Model

The current project is a local development and portfolio implementation.

It does not yet include:

* user authentication
* authorization
* RBAC
* API gateway
* network isolation
* rate limiting
* centralized secrets management

These are future production concerns and should not be interpreted as implemented features.

⸻

37. Current Error Handling

FastAPI returns controlled errors for several scenarios.

Examples include:

404 – inbound file not found
404 – reconciliation record not found
400 – missing recon_id
400 – invalid request scope
400 – no data available for demo scenario
500 – AI assistant processing failure

Ingestion failures at row level are written to:

ibor_load_reject

instead of terminating the complete ingestion run.

This enables partial-success processing.

⸻

38. Current Application Data Flow

CSV
 │
 ▼
Ingestion
 │
 ├───────────────► Reject Store
 │
 ▼
Source Transaction
 │
 ▼
IBOR Transaction
 │
 ▼
Reconciliation
 │
 ├── PAIRED
 ├── MISMATCH
 ├── UNPAIR-EXT
 └── UNPAIR-INT
        │
        ▼
Investigation
        │
        ▼
Evidence Object
        │
        ▼
AI Assistant
        │
        ▼
FastAPI
        │
        ▼
React UI

⸻

39. Repository Architecture

ibor-operations-assistant/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   │
│   ├── api/
│   │   └── __init__.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── connection.py
│   │
│   ├── generator/
│   │   ├── __init__.py
│   │   └── generate_data.py
│   │
│   └── services/
│       ├── __init__.py
│       ├── ingestion.py
│       ├── reconciliation.py
│       ├── investigation.py
│       └── ai_assistant.py
│
├── sql/
│   ├── 001_schema.sql
│   └── 002_seed_reference.sql
│
├── ui/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── ARCHITECTURE.md

⸻

40. Current Technology Stack

Layer	Technology
UI	React
Frontend build	Vite
API	FastAPI
Language	Python
Validation	Pydantic
Database	PostgreSQL 17
Database driver	psycopg 3
Local database runtime	Docker Compose
AI integration	OpenAI Responses API
Configuration	pydantic-settings
Source control	Git / GitHub

⸻

41. Current Architecture vs Target Architecture

The current project intentionally favors clarity and demonstrability over production complexity.

Current

React
   │
FastAPI
   │
PostgreSQL
FastAPI ─────► OpenAI API

Target production architecture

                       Internet
                           │
                           ▼
                  ┌────────────────┐
                  │ CDN / Frontend │
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ API Gateway /  │
                  │ Load Balancer  │
                  └───────┬────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │ Containerized API    │
               │ FastAPI              │
               └──────────┬───────────┘
                          │
               ┌──────────┴─────────┐
               │                    │
               ▼                    ▼
       ┌───────────────┐      ┌───────────────┐
       │ Managed DB    │      │ OpenAI API    │
       │ PostgreSQL    │      │               │
       └───────────────┘      └───────────────┘

⸻

42. Potential AWS Target Architecture

A future AWS deployment could use:

Route 53
   │
CloudFront
   │
S3 / frontend hosting
   │
Application Load Balancer
   │
ECS Fargate / FastAPI
   │
Amazon RDS PostgreSQL

Supporting services could include:

AWS Secrets Manager
CloudWatch
ECR
IAM
VPC
Security Groups
AWS WAF

This represents a target architecture only.

It is not part of the current implementation.

⸻

43. Production Evolution

Potential future architectural enhancements include:

API modularization

Move routes from:

app/main.py

into modules such as:

app/api/ingestion.py
app/api/reconciliation.py
app/api/assistant.py
app/api/jobs.py

⸻

Repository layer

Introduce database repositories between services and raw SQL.

Example:

API
 │
Service
 │
Repository
 │
PostgreSQL

⸻

Database migrations

Replace bootstrap-only SQL scripts with a migration framework such as Alembic.

⸻

Authentication and RBAC

Introduce roles such as:

Operations Analyst
Operations Manager
Administrator
Read Only

⸻

Observability

Future production monitoring could include:

structured logging
request correlation IDs
API latency metrics
reconciliation metrics
job-run metrics
AI invocation metrics
database metrics
distributed tracing

⸻

Reconciliation scalability

Future reconciliation could support:

* multiple transaction sources
* configurable matching rules
* tolerance-based matching
* security identifier cross-reference
* account cross-reference
* settlement-date reconciliation
* currency reconciliation
* duplicate detection
* configurable business-date processing

⸻

44. Future IBOR Domain Expansion

The current project focuses on transaction reconciliation.

Future phases could extend the architecture into additional IBOR operational areas.

Phase 2

Positions:

BOD positions
intraday positions
position reconciliation
T-1 / T processing

⸻

Phase 3

Cash and tax lots:

cash balances
settled cash
unsettled cash
tax lots
cash reconciliation

⸻

Phase 4

Operational intelligence:

SQL diagnostics
rule-based investigation
historical break patterns
automated run-book suggestions
evidence retrieval
AI-assisted operations support

⸻

45. Architectural Design Summary

The key architectural decision in the IBOR Operations Assistant is the separation between:

Operational truth

and:

AI interpretation

Operational truth is determined by:

PostgreSQL data
+
deterministic Python logic
+
deterministic SQL reconciliation

AI is used only after that evidence has been established.

The resulting flow is:

Transactions
     │
     ▼
Deterministic Processing
     │
     ▼
Deterministic Reconciliation
     │
     ▼
Deterministic Investigation
     │
     ▼
Structured Evidence
     │
     ▼
AI Explanation
     │
     ▼
Operations Analyst

This architecture allows the project to demonstrate how generative AI can assist investment operations without allowing AI to become the system of record or the reconciliation engine.