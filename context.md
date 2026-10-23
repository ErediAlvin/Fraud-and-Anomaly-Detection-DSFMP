# DSFMP Fraud Detection Module — Backend Context & Progress Tracker

**Digital School Feeding Management Platform | ICS C4 Capstone 2026**  
**Document Status:** Live Architecture & Task Status Reference  
**Last Updated:** October 2026  
**Active Working Branch:** `feature/ml-synthetic-data-isolation-forest`

---

## 1. Executive Summary & Current State

The backend is built using **FastAPI**, **MySQL 8.0** (via async SQLAlchemy 2.0 & aiomysql), and **Redis 7**. 

As of October 2026:
- **Phase 1 Infrastructure & Database:** **100% Complete** (Full 24-table schema, docker-compose, connection pooling, Redis caching/token blacklist, seed scripts).
- **Core API Layer (Read, Write & Interactive Routes):** **~88% Complete** (Auth with 2FA, Dashboard, Alerts, Cases, Beneficiaries, Transactions, Supply Chain with graph topology & actions, Risk Profiles with dossiers & status transitions, Reports with streaming CSV exports, Settings).
- **Interactive Case Workflow & Management Actions:** **~35% Complete** (Read and filter working; Kanban stage queries functional; status transitions, comment threads, alert-to-case conversion pending).
- **Phase 2 — ML Anomaly Detection Engine (`backend/ml/`):** **~40% Complete** (Synthetic data generator with Faker [10,000 records], robust data cleaner and feature preprocessor operational, Isolation Forest trained & calibrated with ROC-AUC 0.9422, serialized artifact `isolation_forest_v1.joblib` saved; Autoencoder, LSTM, GNN, and real-time inference endpoint pending).
- **Phase 3 — Blockchain Record Integrity Layer (`backend/blockchain/`):** **0% Complete** (Folder initialized; schema columns and mock hashes present, but ledger client/verification pending).
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
| **Case Management** | `/api/cases` | ✅ Complete | `GET /` (list, search, Kanban stats, SLA tracking)<br>`GET /{id}` (full forensic dossier, linked alerts, SLA timers)<br>`POST /` (open case or convert from fraud alert)<br>`PATCH /{id}/status` (stage progression & closure reasons)<br>`POST /{id}/assign` (investigator assignment with in-app notification)<br>`GET/POST /{id}/comments` (collaboration thread) |
| **Beneficiaries** | `/api/beneficiaries` | ✅ Working | `GET /` — County/tier filtering, enrollment trend.<br>`POST /{id}/flag`, `POST /{id}/clear` |
| **Transactions** | `/api/transactions` | ✅ Working | `GET /` — Filter by type, tier, search, hourly volume, amount distribution.<br>`POST /{id}/investigate`, `POST /{id}/clear` |
| **Supply Chain** | `/api/supply-chain` | ✅ Working | `GET /` — Active/flagged supplier counts, delivery variance stats.<br>`GET /suppliers/{id}` — Full supplier dossier, orders, deliveries, schools.<br>`POST /suppliers/{id}/flag` — Elevate supplier risk tier to CRITICAL.<br>`POST /suppliers/{id}/clear` — Reset supplier risk to LOW.<br>`GET /network` — Topological graph data (nodes & links) for supplier-school network. |
| **Risk Profiles** | `/api/risk-profiles` | ✅ Working | `GET /` — Risk scores, tier breakdowns, monitored count.<br>`GET /{id}` — Entity profile dossier with 90-day score history and radar chart breakdown.<br>`PATCH /{id}/status` — Status modification (`CLEAN`, `WATCHLIST`, `SUSPENDED`) with audit logging.<br>`POST /{id}/recalculate` — Trigger on-demand score recalculation. |
| **Reports** | `/api/reports` | ✅ Working | `GET /` — Summary stats, 30-day alert trend, county alert frequency, financial exposure, resolution performance.<br>`GET /export` — Streaming CSV dynamic download for executive & audit reports. |
| **System Settings** | `/api/settings` | ✅ Complete | Categorized config (`GET /api/settings`, `PUT /api/settings/{category}`), user management (`GET /users`, `POST /users`, `PATCH /users/{id}`), audit log (`GET /audit-log`). |
| **Blockchain** | `/api/blockchain` | 🔴 Pending | Commented out in `main.py`. Frontend page currently relies on mock records. |
| **Model Performance** | `/api/models` | 🔴 Pending | Commented out in `main.py`. Frontend page currently relies on mock records. |
| **SOB / COB Procedures** | `/api/procedures` | 🔴 Pending | Commented out in `main.py`. Frontend page currently relies on mock records. |

---

### 2.3 Machine Learning Layer (`backend/ml/`)

**Current Status:** 🟡 **In Progress (~40% Complete — Data Pipeline & Isolation Forest Operational)**  
**Handout Requirements & Implementation Breakdown:**

1. **Synthetic Data Generator (`ml/datasets/generate_synthetic_data.py`):**
   - ✅ Generated 10,000 synthetic transaction records using Python `Faker` simulating Kenyan counties, schools, procurement categories, and feeding program budgets.
   - ✅ Injected 4 distinct fraud vectors: Off-hours disbursements, abnormal transaction spikes, ghost student subsidy leakage, and split payments (structuring).
   - ✅ Exported datasets:
     - `ml/datasets/synthetic_transactions_full.csv` (10,000 rows)
     - `ml/datasets/synthetic_transactions_train.csv` (8,000 rows, 80% split)
     - `ml/datasets/synthetic_transactions_test.csv` (2,000 rows, 20% split)

2. **Data Cleaning Pipeline (`ml/features/cleaning.py`):**
   - ✅ `TransactionDataCleaner`: Deduplication, extreme negative value clipping, missing value imputation (e.g. missing suppliers in direct school subsidies), and ratio sanitization to prevent zero-division errors.

3. **Feature Engineering Pipeline (`ml/features/preprocessing.py`):**
   - ✅ `TransactionPreprocessor`: Extracts cyclical hour representations (`hour_sin`, `hour_cos`), log-transformed transaction amounts, school/supplier deviation ratios against historical medians, and applies `RobustScaler` to handle extreme outliers.

4. **Isolation Forest Outlier Model (25% Weight in Final Score):**
   - ✅ Model Wrapper (`ml/models/isolation_forest.py`): 200 estimators, 5% contamination, random seed 42. Calibrates raw decision scores into a standardized $[0.0, 1.0]$ anomaly score.
   - ✅ Training & Evaluation Pipeline (`ml/training/train_outlier_model.py`):
     - **ROC-AUC Score:** `0.9422`
     - **Precision:** `33.61%` (0.3361)
     - **Recall:** `82.65%` (0.8265 — 81/98 fraud records caught)
     - **F1-Score:** `0.4779`
     - **Confusion Matrix:** TN: 1,742 | FP: 160 | FN: 17 | TP: 81
   - ✅ Model Artifact: Persisted and ready for inference at `ml/saved_models/isolation_forest_v1.joblib` (~2.8 MB).

5. **Autoencoder (30% Weight):**
   - 🔴 Deep reconstruction error model for multivariate behavioral anomalies across food weights, student counts, and invoices. *(Pending implementation)*

6. **LSTM Autoencoder (25% Weight):**
   - 🔴 Temporal sequence modeling per school (detecting abnormal daily/weekly meal serving patterns). *(Pending implementation)*

7. **Graph Neural Network (20% Weight):**
   - 🔴 Entity relationship graph (Supplier ↔ School ↔ Procurement Officer) to flag collusion rings and procurement monopolies. *(Pending implementation)*

8. **Supervised Feedback Model (XGBoost):**
   - 🔴 Continuous refinement based on investigator labels (`is_true_positive` from closed cases). *(Pending implementation)*

9. **Composite Risk Engine:**
   - Formula: $\text{Score} = 0.25(\text{IF}) + 0.30(\text{AE}) + 0.25(\text{LSTM}) + 0.20(\text{GNN})$
   - Tiers: `CRITICAL` ($\ge 0.80$), `HIGH` ($0.60-0.79$), `MEDIUM` ($0.40-0.59$), `LOW` ($< 0.40$).
   - *(Pending: Real-time API inference endpoint `POST /api/ml/score-transaction`)*

---

### 2.4 Blockchain Layer (`backend/blockchain/`)

**Current Status:** 🔴 **Unimplemented (Directory initialized)**  
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

### Priority 1: Machine Learning Engine (Phase 2 Delivery)
- [x] **Synthetic Data Generation:** 10,000 Kenyan school feeding transactions generated with Faker (`ml/datasets/generate_synthetic_data.py`).
- [x] **Data Cleaner & Preprocessor:** Pipeline built for deduplication, imputation, cyclical hour encoding, and robust scaling (`ml/features/cleaning.py`, `ml/features/preprocessing.py`).
- [x] **Isolation Forest Model:** Built, calibrated, and trained with ROC-AUC 0.9422 (`ml/models/isolation_forest.py`, `ml/training/train_outlier_model.py`).
- [x] **Model Serialization:** Persisted artifact at `ml/saved_models/isolation_forest_v1.joblib`.
- [ ] **Scoring Inference Endpoint:** Implement `POST /api/ml/score-transaction` to evaluate transactions in real time using the saved Isolation Forest model.
- [ ] **Autoencoder Model:** Multivariate reconstruction error architecture for tabular anomaly detection (`ml/models/autoencoder.py`).
- [ ] **LSTM Autoencoder:** Temporal sequence model for school daily meal record counts (`ml/models/lstm_autoencoder.py`).
- [ ] **Graph Neural Network:** Entity graph modeling for supplier-school-officer collusion detection (`ml/models/gnn_network.py`).
- [ ] **Investigator Feedback Loop:** Feed closed case resolutions (`is_true_positive`) into training store.

### Priority 2: Backend CRUD & Workflow Completeness
- [x] **Supply Chain Actions:** Added `GET /suppliers/{id}`, `POST /flag`, `POST /clear`, and `GET /network` topology graph.
- [x] **Risk Profile Actions:** Added `GET /{id}` dossier, `PATCH /{id}/status` (CLEAN/WATCHLIST/SUSPENDED), and `POST /{id}/recalculate`.
- [x] **Report Generation:** Added `GET /export` streaming dynamic CSV files.
- [x] **Case Management Actions:**
  - `PATCH /api/cases/{id}/status` (Update stage: `DETECTED` $\to$ `TRIAGED` $\to$ `UNDER_INVESTIGATION` $\to$ `ESCALATED` $\to$ `RESOLVED`).
  - `POST /api/cases` (Create case directly or from an existing `fraud_alert`).
  - `GET /api/cases/{id}` (Detailed single-case dossier with linked evidence, timeline, SLA timers).
  - `POST /api/cases/{id}/comments` and `GET /api/cases/{id}/comments` (Investigator collaboration thread).
  - `POST /api/cases/{id}/assign` (Assign to investigator with in-app notification).
- [ ] **Alert Actions:**
  - `POST /api/alerts/{id}/dismiss` (Mark as false positive with reason for model feedback).
  - `POST /api/alerts/{id}/escalate` (Instantly generate a Case from an Alert).
- [ ] **Procedures Router (`routes/procedures.py`):**
  - Implement trigger and status endpoints for Start-of-Business (SOB) and Close-of-Business (COB).
- [ ] **Blockchain Verification Router (`routes/blockchain.py`):**
  - Serve ledger blocks and query verification status against MySQL records.
- [ ] **Model Performance Router (`routes/model_performance.py`):**
  - Expose precision/recall/F1 metrics and drift indicators from `ml_models` and `ml_model_metrics` tables.

### Priority 3: Architecture & Code Refactoring
- [ ] **Decouple SQL from Routes:** Move raw SQL logic out of `routes/*.py` into `services/` and `controllers/`.
- [ ] **SQLAlchemy ORM Models:** Add model definitions for `Case`, `FraudAlert`, `Transaction`, `Beneficiary`, `Supplier`, `School` (currently only `User` is an ORM class).

### Priority 4: Blockchain Record Layer (Phase 3 Delivery)
- [ ] Setup Hyperledger Fabric chaincode or cryptographic hash auditing service.
- [ ] Implement hashing pipeline for student registrations and subsidy payments.
- [ ] Build ledger tamper audit verification endpoint.

