# DSFMP Fraud Detection Module — Backend Context & Progress Tracker

**Digital School Feeding Management Platform | ICS C4 Capstone 2026**  
**Document Status:** Live Architecture & Task Status Reference  
**Last Updated:** September 2026  

---

## 1. Executive Summary & Current State

The backend is built using **FastAPI**, **MySQL 8.0** (via async SQLAlchemy 2.0 & aiomysql), and **Redis 7**. 

As of today:
- **Phase 1 Infrastructure & Database:** **100% Complete** (Full 24-table schema, docker-compose, connection pooling, Redis caching/token blacklist, seed scripts).
- **Core API Layer (Read & Basic Action Routes):** **~75% Complete** (Auth with 2FA, Dashboard, Alerts, Cases, Beneficiaries, Transactions, Supply Chain, Risk Profiles, Reports).
- **Interactive Case Workflow & Management Actions:** **~30% Complete** (Read and filter working; status transitions, comment threads, alert-to-case conversion pending).
- **Phase 2 — ML Anomaly Detection Engine (`backend/ml/`):** **0% Complete** (Folder empty; models and inference pipeline pending).
- **Phase 3 — Blockchain Record Integrity Layer (`backend/blockchain/`):** **0% Complete** (Folder empty; schema columns and mock hashes present, but ledger client/verification pending).
- **SOB/COB Procedures & Model Performance APIs:** **0% Complete** (Commented out in `main.py`).

---

## 2. Detailed Progress Matrix

### 2.1 Infrastructure & Core Services

| Component | Status | Details |
|---|---|---|
| **Docker Compose** | ✅ Done | FastAPI + MySQL 8.0 + Redis 7 alpine with volume persistence and health checks |
| **MySQL Schema (`database/schema.sql`)** | ✅ Done | 24 relational tables covering users, geographic hierarchy, schools, beneficiaries, suppliers, transactions, meal records, fraud alerts, cases, risk profiles, ML metrics, procedures, blockchain ledger |
| **Database Seeder (`seed_db.py`)** | ✅ Done | Generates realistic Kenyan school feeding data (Nairobi, Mombasa, Kisumu, etc.), transactions, alerts, and cases |
| **Async DB Engine (`database/connection.py`)** | ✅ Done | Async SQLAlchemy 2.0 engine with `aiomysql`, connection recycling, and `get_db` session dependency |
| **Redis Layer (`database/redis.py`)** | ✅ Done | Connection pooling, token blacklist checking, namespace key factories |
| **Configuration (`config/settings.py`)** | ✅ Done | Pydantic v2 settings for DB, Redis, JWT secrets, risk score weights, and tier thresholds |
| **Security & Auth (`config/security.py`)** | ✅ Done | Password hashing (bcrypt), JWT access/refresh tokens, TOTP 2FA handling (pyotp) |
| **Auth Middleware (`middleware/dependencies.py`)** | ✅ Done | `get_current_user`, token validation against Redis blacklist, `require_role` RBAC |

---

### 2.2 API Routers (`backend/routes/`)

| Router | Route Prefix | Status | Implemented Endpoints & Notes |
|---|---|---|---|
| **Auth** | `/api/auth` | ✅ Complete | `POST /login`, `POST /verify-2fa`, `POST /refresh`, `POST /logout`, `GET /me` |
| **Dashboard** | `/api/dashboard` | ✅ Complete | `GET /` — Stat card metrics, recent alerts, risk distribution (pie chart), county concentration, SOB/COB status, top flagged entities, 14-day trend |
| **Fraud Alerts** | `/api/alerts` | 🟡 Partial | `GET /` — Filters (tier, status, alert_type, search).<br>*(Pending: Dismiss alert, acknowledge, escalate alert to case)* |
| **Case Management** | `/api/cases` | 🟡 Partial | `GET /` — Stage breakdown for Kanban and list view, SLA counters.<br>*(Pending: Change stage, add comments, upload attachments, assign investigator)* |
| **Beneficiaries** | `/api/beneficiaries` | ✅ Working | `GET /` — County/tier filtering, enrollment trend.<br>`POST /{id}/flag`, `POST /{id}/clear` |
| **Transactions** | `/api/transactions` | ✅ Working | `GET /` — Filter by type, tier, search, hourly volume, amount distribution.<br>`POST /{id}/investigate`, `POST /{id}/clear` |
| **Supply Chain** | `/api/supply-chain` | 🟡 Read Only | `GET /` — Active/flagged supplier counts, delivery variance stats.<br>*(Pending: Supplier order details, delivery confirmation validation)* |
| **Risk Profiles** | `/api/risk-profiles` | 🟡 Read Only | `GET /` — Risk scores, tier breakdowns, monitored count.<br>*(Pending: Manual tier adjustment, watchlist toggling)* |
| **Reports** | `/api/reports` | 🟡 Read Only | `GET /` — Summary stats, 30-day alert trend, county alert frequency.<br>*(Pending: Export CSV/PDF generation)* |
| **Blockchain** | `/api/blockchain` | 🔴 Pending | Commented out in `main.py`. Frontend page currently relies on mock records. |
| **Model Performance** | `/api/models` | 🔴 Pending | Commented out in `main.py`. Frontend page currently relies on mock records. |
| **SOB / COB Procedures** | `/api/procedures` | 🔴 Pending | Commented out in `main.py`. Frontend page currently relies on mock records. |
| **System Settings** | `/api/settings` | ✅ Complete | Categorized config (`GET /api/settings`, `PUT /api/settings/{category}`), user management (`GET /users`, `POST /users`, `PATCH /users/{id}`), audit log (`GET /audit-log`). |

---

### 2.3 Machine Learning Layer (`backend/ml/`)

**Current Status:** 🟡 **In Progress (Synthetic Data Generator & Isolation Forest Complete)**  
**Handout Requirements:**

1. **Isolation Forest (25% Weight):**
   - Tabular anomaly detection for transactions and meal record spikes.
   - ✅ Synthetic transaction dataset generated using Python `Faker` (`ml/datasets/generate_synthetic_data.py`).
   - ✅ Feature extraction & preprocessing pipeline (`ml/features/preprocessing.py`).
   - ✅ Model wrapper with $[0.0, 1.0]$ calibrated scoring (`ml/models/isolation_forest.py`).
   - ✅ Training pipeline with evaluation metrics (`ml/training/train_outlier_model.py`, ROC-AUC: 0.9422).
   - ✅ Model artifact saved to `ml/saved_models/isolation_forest_v1.joblib`.
2. **Autoencoder (30% Weight):**
   - Deep reconstruction error detection for multivariate behavioral anomalies.
3. **LSTM Autoencoder (25% Weight):**
   - Temporal sequence modeling per school (detecting abnormal daily/weekly rhythms).
4. **Graph Neural Network (20% Weight):**
   - Entity relationship graph (Supplier ↔ School ↔ Procurement Officer) to flag collusion rings and monopolies.
5. **Supervised Feedback Model (XGBoost):**
   - Continuous refinement based on investigator labels (`is_true_positive` from closed cases).
6. **Composite Risk Engine:**
   - Calculation: $\text{Score} = 0.25(\text{IF}) + 0.30(\text{AE}) + 0.25(\text{LSTM}) + 0.20(\text{GNN})$
   - Tiers: `CRITICAL` ($\ge 0.80$), `HIGH` ($0.60-0.79$), `MEDIUM` ($0.40-0.59$), `LOW` ($< 0.40$).

---

### 2.4 Blockchain Layer (`backend/blockchain/`)

**Current Status:** 🔴 **Unimplemented (Directory contains only `.gitkeep`)**  
**Handout Requirements:**

1. **Permissioned Ledger Integration (Hyperledger Fabric):**
   - Beneficiary identity registry hashing.
   - Payment release transaction logging.
   - Delivery confirmation smart contract enforcement.
2. **Tamper Verification Service:**
   - Cryptographic comparison between MySQL record fields and ledger transaction hash (`blockchain_hash`).
   - Mismatch detection: Flagging unauthorized database modifications.
3. **Async Ledger Dispatcher:**
   - Background queue worker to write ledger blocks without blocking API request latency.

---

## 3. Pending Tasks Roadmap

### Priority 1: Backend CRUD & Workflow Completeness
- [ ] **Case Management Actions:**
  - `PATCH /api/cases/{id}/status` (Update stage: `DETECTED` $\to$ `TRIAGED` $\to$ `UNDER_INVESTIGATION` $\to$ `ESCALATED` $\to$ `RESOLVED`).
  - `POST /api/cases` (Create case directly or from an existing `fraud_alert`).
  - `POST /api/cases/{id}/comments` and `GET /api/cases/{id}/comments`.
  - `POST /api/cases/{id}/assign` (Assign to investigator).
- [ ] **Alert Actions:**
  - `POST /api/alerts/{id}/dismiss` (Mark as false positive with reason for model feedback).
  - `POST /api/alerts/{id}/escalate` (Instantly generate a Case from an Alert).
- [ ] **Procedures Router (`routes/procedures.py`):**
  - Implement trigger and status endpoints for Start-of-Business (SOB) and Close-of-Business (COB).
- [ ] **Blockchain Verification Router (`routes/blockchain.py`):**
  - Serve ledger blocks and query verification status against MySQL records.
- [ ] **Model Performance Router (`routes/model_performance.py`):**
  - Expose precision/recall/F1 metrics and drift indicators from `ml_models` and `ml_model_metrics` tables.

### Priority 2: Service Layer & Code Quality
- [ ] **Decouple SQL from Routes:** Move raw SQL logic out of `routes/*.py` into `services/` and `controllers/`.
- [ ] **SQLAlchemy ORM Models:** Add model definitions for `Case`, `FraudAlert`, `Transaction`, `Beneficiary`, `Supplier`, `School` (currently only `User` is an ORM class).

### Priority 3: Machine Learning Engine (Phase 1 of Handout)
- [ ] Implement dataset preprocessor & feature extractors.
- [ ] Train/scaffold Isolation Forest & Autoencoder models.
- [ ] Implement scoring pipeline endpoint: `POST /api/ml/score-transaction`.
- [ ] Connect investigator feedback loop (`is_true_positive`) into training label store.

### Priority 4: Blockchain Record Layer (Phase 2 of Handout)
- [ ] Setup Hyperledger Fabric chaincode or cryptographic hash auditing service.
- [ ] Implement hashing pipeline for student registrations and subsidy payments.
- [ ] Build ledger tamper audit verification endpoint.
