# Digital School Feeding Management Platform (DSFMP)
## Intelligent Fraud Detection, Risk Profiling & Immutable Audit System

[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.12-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.3.5-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Git Branch](https://img.shields.io/badge/Branch-dev-blue?style=for-the-badge&logo=git&logoColor=white)](https://github.com/ErediAlvin/Fraud-System.git)

---

## Table of Contents

1. [Executive Overview](#executive-overview)
2. [Problem Statement & Fraud Vectors](#problem-statement--fraud-vectors)
3. [Dual-Engine Defense Architecture](#dual-engine-defense-architecture)
4. [Key System Features & Modules](#key-system-features--modules)
5. [System Architecture & End-to-End Flow](#system-architecture--end-to-end-flow)
6. [Database & Storage Design (24-Table Schema)](#database--storage-design-24-table-schema)
7. [Technology Stack](#technology-stack)
8. [Project Directory Layout](#project-directory-layout)
9. [Installation & Getting Started](#installation--getting-started)
10. [Database Seeding & Preloaded Accounts](#database-seeding--preloaded-accounts)
11. [REST API Documentation & Endpoints](#rest-api-documentation--endpoints)
12. [Machine Learning & Composite Risk Scoring Engine](#machine-learning--composite-risk-scoring-engine)
13. [Security, RBAC & Compliance](#security-rbac--compliance)
14. [Operational Procedures (SOB / COB)](#operational-procedures-sob--cob)
15. [Git Version Control & Branching Strategy](#git-version-control--branching-strategy)
16. [Project Roadmap & Implementation Status](#project-roadmap--implementation-status)
17. [Academic & Project Metadata](#academic--project-metadata)

---

## Executive Overview

The **Digital School Feeding Management Platform (DSFMP) Fraud Detection System** is an enterprise-grade oversight, risk intelligence, and investigatory framework engineered to eliminate systemic fund leakage, ghost beneficiaries, procurement irregularities, and delivery diversion in national school meal programs.

School feeding programs manage millions of dollars in government subsidies, multi-lateral donor funding (e.g., World Food Programme), and community contributions. Studies indicate that **10% to 30% of allocated resources fail to reach vulnerable school children** due to paper-based tracking, manual verification bottlenecks, and absence of automated anomaly detection.

DSFMP solves this challenge with a **Dual-Engine Architecture**:
- **Proactive Machine Learning (ML) Engine:** Continually monitors transactional rhythms, meal records, and supply networks to score deviations and flag fraud in real time.
- **Immutable Blockchain Ledger Layer:** Cryptographically seals student identities, procurement contracts, and payment releases to guarantee non-repudiation and tamper prevention.

---

## Problem Statement & Fraud Vectors

The system directly counters four critical fraud vectors prevalent in subsidized public school feeding programs:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                SYSTEMIC FRAUD VECTORS                                  │
├──────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│ Fraud Vector             │ Manifestation               │ DSFMP Defense Mechanism       │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ 1. Ghost Beneficiaries   │ Fictitious or duplicated    │ Temporal attendance tracking, │
│                          │ student records to siphon   │ NEMIS cross-referencing &     │
│                          │ per-capita meal subsidies.  │ ML anomaly detection Model.   │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ 2. Supply Chain Leakage  │ Invoiced delivery quantities│ Dispatch vs. received weight  │
│    & Under-Delivery      │ exceeding verified weights  │ reconciliation and supplier   │
│                          │ at school kitchens.         │ variance outlier profiling.   │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ 3. Procurement Collusion │ Bid-rigging, price gouging, │ Relationship mapping Model    │
│                          │ and recurring kickbacks     │ analyzing officer-supplier    │
│                          │ between officers & vendors. │ interaction clusters.         │
├──────────────────────────┼─────────────────────────────┼───────────────────────────────┤
│ 4. Post-Entry Record     │ Retroactive alterations of  │ SHA-256 cryptographic hash    │
│    Tampering             │ ledger records and payment  │ chaining & permissioned block │
│                          │ status after audit release. │ confirmation receipts.        │
└──────────────────────────┴─────────────────────────────┴───────────────────────────────┘
```

---

## Dual-Engine Defense Architecture

Traditional systems rely either purely on reactive auditing or static rule checks. DSFMP couples **real-time behavioral intelligence** with **cryptographic record immutability**.

```
                           DSFMP TRANSACTION EVENT
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
      ┌─────────────────────────┐           ┌─────────────────────────┐
      │  ML ANOMALY DETECTION   │           │    BLOCKCHAIN LEDGER    │
      │         LAYER           │           │         LAYER           │
      ├─────────────────────────┤           ├─────────────────────────┤
      │ • Outlier Detection     │           │ • SHA-256 Record Hash   │
      │ • Pattern Reconstruction│           │ • Smart Contract Rules  │
      │ • Temporal Model        │           │ • Non-repudiation Chain │
      │ • Relationship Model    │           │ • Tamper Detection      │
      └────────────┬────────────┘           └────────────┬────────────┘
                   │                                     │
                   └──────────────────┬──────────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │   PERSISTENCE & STORAGE   │
                        │         MySQL 8.0         │
                        └─────────────┬─────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │  ANALYST WORKSPACE & UI   │
                        │  Triage • Kanban • Alert  │
                        └───────────────────────────┘
```

### The Synergy
- **Blockchain secures the record:** Guarantees that what was entered cannot be silently altered or deleted.
- **Machine Learning watches the record:** Analyzes entered records to detect if the data itself represents anomalous or fraudulent behavior.

---

## Key System Features & Modules

### 1. Executive Dashboard & Risk Heatmaps
- Real-time KPI summaries: Total Monitored Transactions, Active High-Risk Alerts, Estimated Protected Value (KES), and Unresolved Cases.
- Multi-county geographic risk concentration maps (e.g., Nairobi, Mombasa, Kisumu, Nakuru, Garissa).
- 14-day alert velocity and risk distribution metrics.

### 2. Intelligent Fraud Alerts Triage
- Severity classification: `CRITICAL` ($\ge 0.80$), `HIGH` ($0.60 - 0.79$), `MEDIUM` ($0.40 - 0.59$), and `LOW` ($< 0.40$).
- Categorized anomaly types: `GHOST_BENEFICIARY`, `DELIVERY_DISCREPANCY`, `PAYMENT_ANOMALY`, `SUPPLIER_COLLUSION`, `TEMPORAL_SPIKE`.
- Quick-action workflows: Immediate investigator assignment, case escalation, and feedback-based false positive dismissal.

### 3. Case Investigation Management (Kanban)
- 5-Stage investigation lifecycle: `DETECTED` $\to$ `TRIAGED` $\to$ `UNDER_INVESTIGATION` $\to$ `ESCALATED` $\to$ `RESOLVED`.
- SLA timers, evidence attachment management, chronological investigator comments, and audit trails.

### 4. Beneficiary & School Monitor
- Identifies ghost student enrollment patterns, duplicated birth certificates/NEMIS IDs, and statistical attendance-to-meal discrepancies.
- Ability to flag or clear individual beneficiary records with logged justification.

### 5. Financial Transactions Auditing
- Live monitoring of per-meal disbursements, supplier invoices, and subsidies.
- Time-series payment velocity inspections, high-volume threshold alerts, and anomaly flagging.

### 6. Supply Chain & Food Delivery Monitor
- Automated delta calculation between supplier dispatched weight vs. school received weight.
- Multi-supplier performance grading, delivery variance tracking, and supplier risk scoring.

### 7. Blockchain Record Verification Ledger
- Cryptographic proof verification for meal records, procurement releases, and beneficiary lists.
- Live database-to-chain mismatch scanner to identify unauthorized database row modifications.

### 8. System Settings, Security & Audit Trail
- Fine-grained parameter customization for Model weights, alert thresholds, and SLA durations.
- RBAC user provisioning and complete system action audit logging.

---

## System Architecture & End-to-End Flow

The DSFMP system is structured across four primary functional tiers:

1. **Presentation Tier (React + TypeScript + Vite):** A responsive, analytical web interface providing interactive data visualizations, Kanban boards, alert triage views, and real-time operational feeds.
2. **API & Security Gateway (FastAPI):** High-performance async ASGI application handling authentication, role-based access control, session validation, request routing, and business logic coordination.
3. **Intelligence & Integrity Layer (ML + Blockchain):** Parallel processing pipeline where incoming events are simultaneously evaluated by the Machine Learning ensemble for anomaly scoring and cryptographically hashed for ledger non-repudiation.
4. **Data Persistence Tier (MySQL 8.0):** Relational storage engine with 24 normalized tables maintaining foreign key integrity, index optimizations, and audit records.

---

## Database & Storage Design (24-Table Schema)

The persistent state is managed via **MySQL 8.0** with strict foreign key constraints, composite indexing, and `utf8mb4_unicode_ci` collation.

```
├── 1. Access Control & Identity
│   ├── `users`               : User profiles, hashed credentials, roles, 2FA secrets
│   ├── `sessions`            : Active authentication tokens, client IP, device signatures
│   └── `audit_log`           : Immutable chronological record of all administrative actions
│
├── 2. Administrative Geography
│   ├── `counties`            : Kenya 47 counties hierarchy
│   └── `sub_counties`        : Sub-county administrative demarcations
│
├── 3. Educational Infrastructure & Beneficiaries
│   ├── `schools`             : Primary & secondary institutions with feeding facilities
│   ├── `beneficiaries`       : Enrolled students, NEMIS IDs, status, risk scores
│   └── `meal_records`        : Daily served headcounts vs. kitchen logs
│
├── 4. Procurement & Supply Chain
│   ├── `suppliers`           : Certified food vendors and commodity distributors
│   ├── `procurement_orders`  : Purchase orders, food items, contractual costs
│   └── `deliveries`          : Dispatch notes, dispatched weight vs. received weight
│
├── 5. Financial Operations
│   └── `transactions`        : Subsidy disbursements, payments, reference hashes
│
├── 6. Risk, Alerts & Investigations
│   ├── `fraud_alerts`        : Real-time detected anomalies, risk tiers, scores
│   ├── `cases`               : Formal investigatory cases & SLA trackers
│   ├── `case_alerts`         : Many-to-many link between alerts and open cases
│   ├── `case_comments`       : Chronological notes between assigned investigators
│   ├── `case_attachments`    : Cryptographically stamped evidence files
│   └── `risk_profiles`       : Aggregated multi-factor risk scores per entity
│
├── 7. Machine Learning Registry
│   ├── `ml_models`           : Versioned Model metadata and inference configurations
│   └── `ml_model_metrics`    : Precision, recall, F1, and drift tracking logs
│
├── 8. Integrity & Operational Controls
│   ├── `sob_cob_procedures`  : Start-of-Business / Close-of-Business checklist audits
│   ├── `blockchain_ledger`   : Block headers, Merkle roots, and hash receipts
│   ├── `notifications`       : In-app broadcast events & priority alerts
│   └── `system_settings`     : Dynamic key-value fraud thresholds & configurations
```

---

## Technology Stack

### Backend
- **Language / Runtime:** Python 3.11 / 3.12 (Virtualenv)
- **Web Framework:** [FastAPI v0.115.12](https://fastapi.tiangolo.com/) (Async ASGI)
- **ASGI Web Server:** [Uvicorn v0.34.3](https://www.uvicorn.org/) (Standard multi-worker)
- **Database ORM:** [SQLAlchemy v2.0.41](https://www.sqlalchemy.org/) (Asyncio mode) + [aiomysql v0.2.0](https://github.com/aio-libs/aiomysql)
- **Schema Migrations:** [Alembic v1.15.2](https://alembic.sqlalchemy.org/)
- **Data Validation & Settings:** [Pydantic v2.11.4](https://docs.pydantic.dev/) & `pydantic-settings v2.9.1`
- **Security & Cryptography:** `python-jose` (JWT), `passlib[bcrypt]` (Password Hashing), `pyotp` (TOTP 2FA)

### Frontend
- **Framework & Core:** [React 18.3.1](https://react.dev/) + [TypeScript 5.x](https://www.typescriptlang.org/)
- **Build Tool & HMR:** [Vite v6.3.5](https://vitejs.dev/)
- **Styling & Design System:** [Tailwind CSS v4.1.12](https://tailwindcss.com/) with PostCSS
- **UI Components:** [Radix UI](https://www.radix-ui.com/) Primitives, [Lucide React](https://lucide.dev/)
- **Data Visualizations:** [Recharts v2.15.2](https://recharts.org/)
- **Animations:** [Framer Motion v12.23.24](https://www.framer.com/motion/)

---

## Project Directory Layout

```
IS Project II/
├── Diagrams/                                    # System architecture, ERD & UML flow diagrams
├── Documentation/                               # Capstone documentation, proposal & reports
├── checklist.txt                                # Project environment & rubric checklist
├── file_structure.txt                           # Detailed file breakdown
├── project_development_profile.txt              # Alignment & commit profile
├── README.md                                    # Root system documentation
│
└── Fraud-System/                                # Main Application Workspace
    ├── requirements.md                          # Functional & non-functional requirements
    ├── context.md                               # Backend development status tracker
    ├── DSFMP_Fraud_Detection_Handout.md         # Domain problem & fraud vectors handout
    ├── DSFMP_ML_Blockchain_Combined_Handout.md  # Architecture design reference
    │
    ├── backend/                                 # FastAPI Backend Service
    │   ├── .env.example                         # Environment template
    │   ├── requirements.txt                     # Python package dependencies
    │   ├── main.py                              # Application factory, lifespan & router setup
    │   ├── seed_db.py                           # Realistic Kenyan school feeding dataset seeder
    │   ├── seed_users.py                        # Default user roles & credentials seeder
    │   │
    │   ├── config/                              # Configuration & security
    │   │   ├── settings.py                      # Pydantic v2 application settings
    │   │   └── security.py                      # JWT tokens, bcrypt, TOTP 2FA logic
    │   ├── database/                            # Database connectivity
    │   │   ├── connection.py                    # Async SQLAlchemy engine & session maker
    │   │   └── schema.sql                       # 24-table MySQL 8 schema definition
    │   ├── middleware/                          # Authentication & RBAC dependencies
    │   │   └── dependencies.py                  # Token extraction & role verification
    │   ├── models/                              # SQLAlchemy ORM models
    │   │   └── user.py                          # User ORM model
    │   ├── schemas/                             # Pydantic request/response validation schemas
    │   │   ├── auth.py                          # Login, Token & 2FA schemas
    │   │   └── ...                              # Entity validation schemas
    │   ├── routes/                              # Modular REST API route controllers
    │   │   ├── auth.py                          # Login, 2FA, token refresh, logout
    │   │   ├── dashboard.py                     # Aggregated stats, KPIs, county breakdown
    │   │   ├── alerts.py                        # Fraud alerts filtering & triage
    │   │   ├── cases.py                         # Case management & Kanban workflows
    │   │   ├── beneficiaries.py                 # Ghost student detection & monitoring
    │   │   ├── transactions.py                  # Subsidy & disbursement analysis
    │   │   ├── supply_chain.py                  # Supplier delivery weight discrepancies
    │   │   ├── risk_profiles.py                 # Entity multi-factor risk scoring
    │   │   ├── reports.py                       # Compliance & audit report analytics
    │   │   └── settings.py                      # Global threshold configs, RBAC & logs
    │   ├── ml/                                  # ML Anomaly models & inference pipelines
    │   ├── blockchain/                          # Cryptographic ledger & tamper verification
    │   ├── controllers/                         # Domain business controllers
    │   ├── services/                            # External integrations & auxiliary services
    │   └── utils/                               # Common helpers & formatters
    │
    └── Frontend/                                # React 18 + TypeScript Application
        ├── package.json                         # Node dependencies & npm scripts
        ├── vite.config.ts                       # Vite bundling configuration
        ├── postcss.config.mjs                   # PostCSS configuration
        ├── index.html                           # Single Page Application HTML root
        └── src/
            ├── main.tsx                         # React bootstrap entry point
            ├── app/
            │   └── pages/                       # Domain analytical & operational views
            │       ├── Login.tsx                # Secure authentication & 2FA view
            │       ├── Dashboard.tsx            # Executive KPI summary & risk trends
            │       ├── FraudAlerts.tsx          # Real-time alert triage & filtering
            │       ├── CaseManagement.tsx       # Kanban investigation board
            │       ├── BeneficiaryMonitor.tsx   # Ghost student & attendance analytics
            │       ├── TransactionMonitor.tsx   # Procurement & payment audits
            │       ├── SupplyChainMonitor.tsx   # Delivery discrepancy & supplier rankings
            │       ├── RiskProfiles.tsx         # School & supplier risk scorecards
            │       ├── BlockchainLedger.tsx     # Immutable ledger audit trail
            │       ├── ModelPerformance.tsx     # ML Model accuracy, precision & drift
            │       ├── SOBCOBProcedures.tsx     # Start/Close of business checklists
            │       ├── ReportsAnalytics.tsx     # Compliance & audit trend reporting
            │       └── SystemSettings.tsx       # Global thresholds, RBAC & audit logs
            └── styles/                          # Application theming & Tailwind styles
```

---

## Installation & Getting Started

### Prerequisites
- **Python:** `v3.11` or `v3.12`
- **Node.js:** `v18.x` or `v20.x` with `npm`
- **MySQL:** `v8.0+`

---

### Step-by-Step Local Setup

#### 1. Backend Setup
```powershell
cd "c:\Users\alvin\Desktop\Projects\IS Project II\Fraud-System\backend"

# Create and activate Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install required Python dependencies
pip install -r requirements.txt

# Create .env from template and configure database credentials
cp .env.example .env
```

Ensure MySQL is running on `localhost:3306` with database `dsfmp_fraud`. Then initialize schema and seed baseline data:
```powershell
# Initialize schema & seed synthetic records
python seed_db.py
python seed_users.py

# Start Uvicorn development server with hot-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be live at:
- **FastAPI Backend & Swagger UI:** `http://localhost:8000/docs`
- **API Health Check:** `http://localhost:8000/health`

#### 2. Frontend Setup
```powershell
cd "c:\Users\alvin\Desktop\Projects\IS Project II\Fraud-System\Frontend"

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
- **Frontend Application:** `http://localhost:5173`

---

## Database Seeding & Preloaded Accounts

The backend includes an automated data generator (`backend/seed_db.py` & `backend/seed_users.py`) simulating an active Kenyan school feeding program across **Nairobi, Mombasa, Kisumu, Nakuru, and Garissa** counties.

### Pre-Configured Test Accounts (Password: `Password123!`)

| Email | Role | Accessible Scope | 2FA Status |
|---|---|---|---|
| `admin@dsfmp.go.ke` | `system_admin` | Global System Administration, Config, RBAC | Available |
| `analyst@dsfmp.go.ke` | `fraud_analyst` | Alerts, Triage, Case Management, Risk Analytics | Available |
| `officer.nairobi@dsfmp.go.ke` | `county_officer` | Nairobi County Feeding & School Inspection | Available |
| `supervisor@dsfmp.go.ke` | `supervisor` | Case Escalations, Approval & SLA Monitoring | Available |
| `school.admin@nairobieast.sc.ke` | `school_admin` | School Kitchen Logs, Attendance, Deliveries | Available |

---

## REST API Documentation & Endpoints

Interactive Swagger UI documentation is available out-of-the-box at `http://localhost:8000/docs` when `DEBUG=true`.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   CORE REST API ENDPOINTS                                       │
├─────────┬───────────────────────────────┬──────────────────────┬────────────────────────────────┤
│ Method  │ Endpoint                      │ Auth / Role          │ Description                    │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ POST    │ `/api/auth/login`             │ Public               │ Authenticate with credentials  │
│ POST    │ `/api/auth/verify-2fa`        │ Public (Pre-auth)    │ Verify TOTP 2FA token          │
│ POST    │ `/api/auth/refresh`           │ Authenticated        │ Refresh expired access token   │
│ POST    │ `/api/auth/logout`            │ Authenticated        │ Invalidate session token       │
│ GET     │ `/api/auth/me`                │ Authenticated        │ Retrieve current user profile  │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ GET     │ `/api/dashboard`              │ Authenticated        │ Get KPI summary & risk trends  │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ GET     │ `/api/alerts`                 │ Fraud Analyst+       │ List & filter fraud alerts     │
│ POST    │ `/api/alerts/{id}/dismiss`    │ Fraud Analyst+       │ Dismiss alert (False Positive) │
│ POST    │ `/api/alerts/{id}/escalate`   │ Fraud Analyst+       │ Escalate alert to formal Case  │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ GET     │ `/api/cases`                  │ Fraud Analyst+       │ List cases & Kanban stage view │
│ GET     │ `/api/cases/{id}`             │ Fraud Analyst+       │ Fetch case details & timeline  │
│ PATCH   │ `/api/cases/{id}/status`      │ Fraud Analyst+       │ Advance case workflow stage    │
│ POST    │ `/api/cases/{id}/comments`    │ Fraud Analyst+       │ Add chronological case comment │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ GET     │ `/api/beneficiaries`          │ Authenticated        │ List students & ghost flags    │
│ POST    │ `/api/beneficiaries/{id}/flag`│ Fraud Analyst+       │ Manually flag suspicious entry │
│ POST    │ `/api/beneficiaries/{id}/clear`│Fraud Analyst+       │ Clear flag with justification  │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ GET     │ `/api/transactions`           │ Authenticated        │ Financial transaction log      │
│ POST    │ `/api/transactions/{id}/investigate`│ Analyst+       │ Trigger transaction inquiry    │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ GET     │ `/api/supply-chain`           │ Authenticated        │ Supplier delivery variance     │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ GET     │ `/api/risk-profiles`          │ Authenticated        │ School & supplier risk tiers   │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ GET     │ `/api/reports`                │ Authenticated        │ Compliance & audit analytics   │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ GET     │ `/api/settings`               │ System Admin         │ Fetch global system settings   │
│ PUT     │ `/api/settings/{category}`    │ System Admin         │ Update fraud thresholds        │
│ GET     │ `/api/settings/users`         │ System Admin         │ Manage RBAC user accounts      │
│ GET     │ `/api/settings/audit-log`     │ System Admin         │ Query system security log      │
├─────────┼───────────────────────────────┼──────────────────────┼────────────────────────────────┤
│ GET     │ `/health`                     │ Public               │ Live MySQL service healthprobe │
└─────────┴───────────────────────────────┴──────────────────────┴────────────────────────────────┘
```

---

## Machine Learning & Composite Risk Scoring Engine

The ML engine employs a weighted multi-Model ensemble to produce a normalized **Composite Risk Score ($S \in [0, 1]$)** for every transactional and operational event.

### Mathematical Formulation
$$\text{Composite Risk Score} = (w_1 \cdot S_{\text{Model 1}}) + (w_2 \cdot S_{\text{Model 2}}) + (w_3 \cdot S_{\text{Model 3}}) + (w_4 \cdot S_{\text{Model 4}})$$

Where default calibrated weights are:
- **$w_1 = 0.25$ — Outlier Detection Model ($S_{\text{Model 1}}$):** Rapid tabular outlier detection for single-dimension transaction spikes and meal counts.
- **$w_2 = 0.30$ — Pattern Reconstruction Model ($S_{\text{Model 2}}$):** Multivariate feature reconstruction error measuring non-linear behavioral shifts.
- **$w_3 = 0.25$ — Temporal Model ($S_{\text{Model 3}}$):** Sequence prediction analyzing temporal school attendance rhythms and weekday variance.
- **$w_4 = 0.20$ — Relationship Model ($S_{\text{Model 4}}$):** Node and edge relationship embeddings detecting supplier-officer collusion clusters.

### Risk Tier Boundaries
- **CRITICAL ($\ge 0.80$):** Immediate automated alert, transaction freeze hold, and auto-case creation.
- **HIGH ($0.60 - 0.79$):** Flagged for mandatory analyst triage within 4-hour SLA.
- **MEDIUM ($0.40 - 0.59$):** Placed on active entity watchlist for trend confirmation.
- **LOW ($< 0.40$):** Baseline operations; verified normal behavior.

---

## Security, RBAC & Compliance

1. **Session & Token Management:**
   - Stateless JWT tokens with automated expiration validation and invalidation tracking upon logout.
2. **Multi-Factor Authentication (TOTP):**
   - Time-based One-Time Passwords compatible with Google Authenticator, Microsoft Authenticator, or Authy via `pyotp`.
3. **Role-Based Access Control (RBAC):**
   - Granular privilege checks via FastAPI dependency injection (`require_role([...])`).
4. **Data Protection & Auditability:**
   - Passwords hashed using `bcrypt` with automated salt generation.
   - All state modifications produce an immutable entry in the `audit_log` table storing user ID, action, timestamp, entity type, and delta payload.

---

## Operational Procedures (SOB / COB)

To ensure day-to-day data integrity, the system implements **Start-of-Business (SOB)** and **Close-of-Business (COB)** checkpoints:
- **SOB Verification:** Verifies morning headcount sync, supplier dispatch notifications, and opening kitchen inventory before meals are prepared.
- **COB Reconciliation:** Compares daily meals served vs. verified student attendance, records closing commodity weights, calculates variance deltas, and seals daily ledger hashes.

---

## Git Version Control & Branching Strategy

- **Remote Repository:** [https://github.com/ErediAlvin/Fraud-System.git](https://github.com/ErediAlvin/Fraud-System.git)
- **Branching Workflow:**
  - `main`: Protected production branch; only tagged, peer-reviewed releases are merged.
  - `dev`: Active integration and feature development branch.
  - `feat/*`: Topic branches for specific features and module endpoints.

---

## Project Roadmap & Implementation Status

- [x] **Phase 1: Foundation & Data Layer**
  - [x] 24-table relational MySQL 8 schema with indexing and foreign keys
  - [x] Async SQLAlchemy 2.0 connection engine & session pool
  - [x] High-fidelity synthetic data generator (`seed_db.py`, `seed_users.py`)
- [x] **Phase 2: Core API & User Interface**
  - [x] JWT Authentication + TOTP 2FA Verification flow
  - [x] Executive Dashboard, KPIs & Geographic risk concentration
  - [x] Fraud alerts triage and filtering system
  - [x] Beneficiaries & ghost student detection views
  - [x] Transaction & supply chain delivery monitors
  - [x] System settings, RBAC provisioning & immutable audit logs
- [ ] **Phase 3: Deep ML & Blockchain Integration**
  - [x] Synthetic data generator with Faker (10,000 transactions, 4 fraud vectors)
  - [x] Data cleaning & feature preprocessing pipeline (cyclical hour encoding, log scaling)
  - [x] Isolation Forest tabular anomaly detection model (ROC-AUC 0.9422, calibrated scoring)
  - [ ] Autoencoder & temporal LSTM reconstruction models
  - [ ] Graph Neural Network (GNN) entity relationship engine
  - [ ] Real-time scoring inference service (`POST /api/ml/score-transaction`)
  - [ ] Cryptographic ledger audit verification
  - [ ] Full interactive Kanban drag-and-drop state mutation & investigator comment threads

---

## Academic & Project Metadata

- **Institution:** Strathmore University / Information Systems Capstone 2026
- **Project Title:** Digital School Feeding Management Platform (DSFMP) — Fraud Detection System
- **Focus Area:** Machine Learning Anomaly Detection, Blockchain Ledger Auditing, Enterprise Information Systems
- **Maintainer:** Alvin Eredi ([GitHub Profile](https://github.com/ErediAlvin))

---

*© 2026 DSFMP Project Team. Built for transparency, accountability, and the protection of vulnerable school feeding resources.*
