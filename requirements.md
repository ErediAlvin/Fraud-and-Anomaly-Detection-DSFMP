# DSFMP Fraud Detection Module — System Requirements Specification (SRS)

**Digital School Feeding Management Platform | ICS C4 Capstone 2026**  
**Standard Compliance:** ISO/IEC/IEEE 29148:2018 (Requirements Engineering) & ISO/IEC 25010:2023 (Systems and Software Quality Requirements and Evaluation — SQuaRE)  
**Document Status:** Approved Baseline Specification  
**Last Updated:** September 2026  

---

## 1. Introduction & Scope

The Digital School Feeding Management Platform (DSFMP) manages government subsidies, donor funding, and food supply chains for primary and secondary schools across Kenya. The **DSFMP Fraud Detection Module** provides automated, intelligent, and tamper-resilient oversight to eliminate four primary fraud vectors:
1. **Ghost Beneficiaries:** Fictitious or duplicate student registrations inflating meal claims.
2. **Payment & Subsidy Fraud:** Irregular transactions, split payments, round-number velocity spikes, and off-hour subsidy releases.
3. **Supply Chain & Procurement Anomalies:** Inflated delivery quantities, ghost deliveries, supplier-school collusion, and procurement monopolies.
4. **Record Tampering & Unauthorized Modifications:** Post-hoc alteration of transaction databases or beneficiary registers.

The system employs a **hybrid architecture** combining a multi-model **Machine Learning Anomaly Detection Layer** (watching behavioral patterns) and a **Permissioned Blockchain Integrity Layer** (guaranteeing cryptographic record immutability).

The system requirements identified for this project are presented in the following subsections.

---

## 2. Requirements Catalogue Summary

| Requirement ID | Category | Title | Priority | Verification Method & Status |
|---|---|---|---|---|
| **FR-01** | Authentication & Security | Role-Based User Authentication & 2FA Enforcement | Must Have | ✅ Verified (Bcrypt + TOTP + JWT) |
| **FR-02** | Authentication & Security | Token Invalidation & Session Blacklisting | Must Have | ✅ Verified (Redis Token Blacklist) |
| **FR-03** | Anomaly Detection | Multi-Model Real-Time Transaction Scoring | Must Have | 🟡 In Progress (Isolation Forest Operational; AE/LSTM/GNN in progress) |
| **FR-04** | Anomaly Detection | Composite Risk Score & Dynamic Tier Classification | Must Have | ✅ Verified (Threshold Calibration & Settings Tier Mapping) |
| **FR-05** | Alert Management | Automated Alert Ingestion & Filtering | Must Have | ✅ Verified (Alerts API & React Filtering) |
| **FR-06** | Alert Management | False Positive Dismissal with ML Feedback Capture | Must Have | 🟡 In Progress (Dismissal & Feedback Store) |
| **FR-07** | Alert Management | Single-Click Alert-to-Case Escalation | Must Have | ✅ Verified (Case Creation from Alert) |
| **FR-08** | Case Management | Interactive Lifecycle Stage Transition & SLA Tracking | Must Have | ✅ Verified (Kanban Drag-Drop & SLA Tracking) |
| **FR-09** | Case Management | Multi-User Comment Threads & Case Assignment | Must Have | ✅ Verified (Comments & Investigator Assignment) |
| **FR-10** | Beneficiary Registry | Ghost Student & Duplicate Enrollment Detection | Must Have | ✅ Verified (Enrollment Variance & Ratios) |
| **FR-11** | Financial Monitoring | Subsidy Velocity & Payment Anomaly Detection | Must Have | ✅ Verified (On-demand Re-evaluation & Transaction Monitor) |
| **FR-12** | Supply Chain | Delivery Reconciliation & Shortage Detection | Must Have | ✅ Verified (Weight Variance & Supplier Dossiers) |
| **FR-13** | Batch Procedures | Start-of-Business (SOB) Automated Procedure | Must Have | 🔴 Pending Implementation |
| **FR-14** | Batch Procedures | Close-of-Business (COB) Automated Procedure | Must Have | 🔴 Pending Implementation |
| **FR-15** | Blockchain Integrity | Cryptographic Record Hashing & Ledger Sync | Must Have | 🔴 Pending (Phase 3 Ledger Integration) |
| **FR-16** | Blockchain Integrity | On-Demand Database Tamper Audit & Mismatch Flagging | Must Have | 🔴 Pending (Phase 3 Audit Service) |
| **FR-17** | ML Governance | Model Performance Metrics & Drift Monitoring | Should Have | ✅ Verified (Live Model Sandbox & Diagnostics UI) |
| **FR-18** | Analytics & Reporting | Visual Analytics Dashboard & Data Aggregation | Must Have | ✅ Verified (Executive Dashboard & Risk Heatmap) |
| **FR-19** | Analytics & Reporting | Forensic Export Generation (CSV / PDF) | Should Have | ✅ Verified (Dynamic Streaming CSV Export) |
| **FR-20** | Administration | Dynamic Risk Parameter & System Configuration | Must Have | ✅ Verified (System Settings & Audit Logging) |
| **NFR-01** | Performance | Real-Time Scoring API Response Latency | Must Have | ✅ Measured (20–95 ms, comfortably $\le 500\text{ ms}$) |
| **NFR-02** | Performance | High-Throughput Batch Processing Capacity | Must Have | Measurement & Load Testing |
| **NFR-03** | Security | Cryptographic Hashing & Encryption Standards | Must Have | Inspection & Code Audit |
| **NFR-04** | Security | Granular Role-Based Access Control (RBAC) | Must Have | Security Testing |
| **NFR-05** | Reliability | Transactional Consistency & Atomic Database Rollback | Must Have | Fault Injection Testing |
| **NFR-06** | Availability | High Service Availability & Operational Uptime | Must Have | Measurement |
| **NFR-07** | Usability | Responsive User Interface & WCAG Compliance | Should Have | Inspection & User Acceptance |
| **NFR-08** | Interoperability | Standardized RESTful JSON Communication | Must Have | Inspection & Contract Testing |
| **NFR-09** | Maintainability | Decoupled Architecture & Automated Test Coverage | Must Have | ✅ Verified (Modular Architecture & Pytest Suite) |
| **NFR-10** | Model Quality | ML Detection Performance Benchmark Thresholds | Must Have | ✅ Measured (ROC-AUC 0.9422 on Test Benchmarks) |
| **NFR-11** | Explainability | Model Transparency & Feature Importance Scoring | Should Have | ✅ Verified (Live Anomaly Reasons & Feature Breakdown) |
| **NFR-12** | Auditability | Immutable System-Wide Audit Logging | Must Have | Inspection & Testing |

---

## 3. Functional Requirements (FR)

### 3.1 Authentication, Authorization & Session Management

#### FR-01: Role-Based User Authentication & 2FA Enforcement
- **Actor:** System Users (`fraud_analyst`, `county_officer`, `system_admin`, `supervisor`, `school_admin`).
- **Trigger:** User submits email, password, and TOTP verification code.
- **Expected Behavior:** The system shall validate user credentials against salted bcrypt password hashes. If valid, the system shall require and verify a Time-based One-Time Password (TOTP) compliant with RFC 6238 before issuing short-lived JSON Web Tokens (Access Token: 30 minutes, Refresh Token: 7 days).
- **Output:** Authenticated user session with specific role claims and redirect to the appropriate dashboard view.
- **Exceptions:** Invalid credentials, unverified 2FA token, or inactive account status returns HTTP 401 Unauthorized.
- **Rationale:** Ensures strict perimeter defense for sensitive anti-fraud data.
- **Verification Method:** Testing and Demonstration.

#### FR-02: Token Invalidation & Session Blacklisting
- **Actor:** Authenticated User / System Admin.
- **Trigger:** User initiates logout or an administrator revokes a compromised session.
- **Expected Behavior:** The system shall register the revoked JWT identifier (`jti`) into a Redis-backed token blacklist with a TTL matching the token expiry window. Subsequent requests presenting the blacklisted token shall be rejected by middleware.
- **Output:** HTTP 200 OK confirmation of revocation and immediate termination of client access.
- **Exceptions:** Redis unavailability forces fallback to synchronous database session revocation.
- **Verification Method:** Automated API Testing.

---

### 3.2 Machine Learning Anomaly Detection & Risk Scoring

#### FR-03: Multi-Model Real-Time Transaction Scoring
- **Actor:** Core Ingestion Pipeline / External Transaction Dispatcher / Fraud Analyst.
- **Trigger:** Ingestion of a financial transaction, meal disbursement claim, or manual on-demand scoring request.
- **Expected Behavior:** The system shall execute four distinct ML models across the event payload:
  1. **Isolation Forest (25% weight):** Identifies tabular anomalies and outlier values (Active artifact: `isolation_forest_v1.joblib` served via `/api/models/isolation-forest/infer`).
  2. **Autoencoder (30% weight):** Computes deep reconstruction error for multivariate behavioral deviations and round-number drains.
  3. **LSTM Autoencoder (25% weight):** Evaluates sequence deviations against 30-day temporal school baselines and velocity bursts.
  4. **Graph Neural Network (20% weight):** Calculates graph centrality deviations across Supplier ↔ School ↔ Procurement Officer relationships.
- **Output:** Individual model anomaly scores (bounded $[0.0000, 1.0000]$), binary anomaly decision against threshold $\tau$, execution latency, and explainability reasons.
- **Exceptions:** If feature extraction fails due to malformed payload, fallback to deterministic heuristic rules and log warning.
- **Implementation Status:** Operational for Isolation Forest (`ml/models/scoring_engine.py`, `POST /api/models/isolation-forest/infer`, `POST /api/transactions/{id}/evaluate-isolation-forest`).
- **Verification Method:** Unit and Integration Testing with benchmark datasets (9/9 automated tests passing in `test_model_inference.py`).

#### FR-04: Composite Risk Score & Dynamic Tier Classification
- **Actor:** Composite Risk Engine.
- **Trigger:** Completion of multi-model scoring for an entity or transaction.
- **Expected Behavior:** The system shall calculate the weighted composite risk score:
  $$\text{Score} = 0.25(\text{IF}) + 0.30(\text{AE}) + 0.25(\text{LSTM}) + 0.20(\text{GNN})$$
  The system shall dynamically classify the entity into one of four operational risk tiers via `settings.get_risk_tier()`:
  - **CRITICAL** ($\ge 0.80$): Auto-generate high-priority alert and flag entity for immediate freeze.
  - **HIGH** ($0.60 - 0.79$): Auto-generate alert queued for senior fraud analyst review.
  - **MEDIUM** ($0.40 - 0.59$): Flag record for watchlist monitoring over a 7-day window.
  - **LOW** ($< 0.40$): Persist score without generating active alerts.
- **Output:** Updated risk score stored in `risk_profiles` and historical tracking row in `risk_history`.
- **Implementation Status:** Calibrated and operational with dynamic user thresholds in API and frontend.
- **Verification Method:** Automated Unit Testing with synthetic edge-case data.

---

### 3.3 Fraud Alert & Triage Lifecycle

#### FR-05: Automated Alert Ingestion & Filtering
- **Actor:** Fraud Analyst, Supervisor.
- **Trigger:** An anomaly score crosses configured alert thresholds.
- **Expected Behavior:** The system shall insert a structured record into `fraud_alerts` containing severity tier, entity reference, confidence score, and root-cause indicators. The frontend shall provide real-time filtering by county, alert type, severity tier, and date range.
- **Output:** Rendered list of fraud alerts with visual urgency indicators.
- **Verification Method:** Demonstration and UI integration testing.

#### FR-06: False Positive Dismissal with ML Feedback Capture
- **Actor:** Fraud Analyst, Supervisor.
- **Trigger:** User reviews an alert and identifies it as a false positive.
- **Expected Behavior:** The system shall prompt the user for a dismissal rationale (e.g., "Legitimate School Event", "System Configuration Error"), update alert status to `DISMISSED`, record the analyst ID, and push a negative label (`is_true_positive = 0`) to the supervised feedback dataset (XGBoost retrain store).
- **Output:** Status updated to `DISMISSED` and logged in `audit_log`.
- **Exceptions:** Unauthorized role cannot dismiss CRITICAL tier alerts without Supervisor approval.
- **Verification Method:** Demonstration and Database verification.

#### FR-07: Single-Click Alert-to-Case Escalation
- **Actor:** Fraud Analyst.
- **Trigger:** Analyst determines an alert represents actionable fraud.
- **Expected Behavior:** The system shall generate a new row in `cases` directly from the alert, linking all evidence, suspect entity IDs, severity tier, and anomaly scores, setting initial case status to `DETECTED` and linking `alert_id`.
- **Output:** Newly created Case with unique case reference (e.g., `CASE-2026-XXXX`).
- **Verification Method:** Demonstration and API Testing.

---

### 3.4 Interactive Case Management & Forensic Workflow

#### FR-08: Interactive Lifecycle Stage Transition & SLA Tracking
- **Actor:** Fraud Analyst, Supervisor, County Officer.
- **Trigger:** Analyst advances an investigation.
- **Expected Behavior:** The system shall enforce sequential case stage transitions:
  $$\text{DETECTED} \longrightarrow \text{TRIAGED} \longrightarrow \text{UNDER\_INVESTIGATION} \longrightarrow \text{ESCALATED} \longrightarrow \text{RESOLVED}$$
  The system shall maintain countdown timers against predefined Service Level Agreements (SLAs):
  - **CRITICAL:** 24-hour resolution SLA.
  - **HIGH:** 72-hour resolution SLA.
  - **MEDIUM:** 7-day resolution SLA.
- **Output:** Updated stage in Kanban/table views and SLA countdown display.
- **Exceptions:** Reopening a `RESOLVED` case requires Supervisor role authorization.
- **Verification Method:** Demonstration and SLA countdown measurement testing.

#### FR-09: Multi-User Comment Threads & Case Assignment
- **Actor:** Fraud Analyst, Supervisor.
- **Trigger:** User posts an investigation note or assigns a case.
- **Expected Behavior:** The system shall persist timestamped case notes into `case_comments`, record file attachments in `case_evidence`, and update the `assigned_to` investigator, dispatching in-app notifications to the assignee.
- **Output:** Real-time comment thread rendered in case details view.
- **Verification Method:** Demonstration and User Acceptance.

---

### 3.5 Operational Domain Monitoring

#### FR-10: Ghost Student & Duplicate Enrollment Detection
- **Actor:** Fraud Detection Engine.
- **Trigger:** Daily meal log ingestion or student registration event.
- **Expected Behavior:** The system shall flag a school with a `GHOST_STUDENT` alert when:
  1. Total meals served in a day exceed the school's total active enrolled students.
  2. Duplicate national student identification or birth certificate numbers appear in multiple schools.
  3. Meal claims are recorded on weekends or official school holidays without an authorized program waiver.
- **Output:** Generated `GHOST_STUDENT` alert linking affected school and beneficiary IDs.
- **Verification Method:** End-to-End Database and Route Testing.

#### FR-11: Financial Subsidy & Payment Integrity Monitoring
- **Actor:** Fraud Detection Engine / Fraud Analyst.
- **Trigger:** Ingestion of payment disbursements or M-Pesa subsidy records, or manual inspection in Transaction Monitor.
- **Expected Behavior:** The system shall analyze transaction amounts, frequencies, and timestamps. It shall raise immediate alerts and support on-demand re-evaluation for:
  1. **Structuring / Smurfing:** Multiple disbursements just below reporting thresholds within 24 hours.
  2. **Off-Hours Activity:** Subsidy approvals or disbursement releases between 21:00 and 05:00 (100% caught by Isolation Forest).
  3. **Duplicate Payments:** Identical payment reference or disbursement amount to the same vendor account within 60 minutes.
  4. **Live Transaction Re-Scoring:** Allow investigators to trigger real-time re-scoring via `POST /api/transactions/{id}/evaluate-isolation-forest` with fallback support.
- **Output:** `PAYMENT_ANOMALY` alert generated with forensic metadata, and real-time inference scores updated in `transactions.if_score`.
- **Implementation Status:** Operational (`routes/transactions.py`, frontend `TransactionMonitor.tsx`).
- **Verification Method:** Unit Testing and live UI demonstration.

#### FR-12: Supply Chain Reconciliation & Shortage Detection
- **Actor:** Supply Chain Monitoring Service.
- **Trigger:** Supplier delivery submission vs. School meal distribution logs.
- **Expected Behavior:** The system shall compute delivery variance by comparing procurement order quantities against confirmed delivery weigh-ins. If variance exceeds $\pm 10\%$ or ration quantities cannot mathematically support recorded meal counts, the supplier and school shall be flagged.
- **Output:** Supply Chain Risk index update and `SUPPLY_CHAIN_ANOMALY` alert generation.
- **Verification Method:** Automated Calculation Verification.

---

### 3.6 Automated Batch Procedures (SOB / COB)

#### FR-13: Start-of-Business (SOB) Automated Procedure
- **Actor:** System Scheduler (Cron) or Authorized Supervisor.
- **Trigger:** Daily schedule at 06:00 East Africa Time (EAT) or manual trigger.
- **Expected Behavior:** The system shall execute the MySQL stored procedure `sp_run_sob_procedure`, performing:
  1. Database and Redis connectivity health verification.
  2. Refreshing 30-day baseline risk profile averages for all schools and suppliers.
  3. Evaluation of open case SLA deadlines and dispatching overdue alerts.
  4. Scanning for unauthorized overnight transactions.
  5. Initializing daily counter metrics.
- **Output:** Atomic entry written to `sob_cob_procedures` with execution duration and step status JSON.
- **Verification Method:** Stored Procedure Execution and API Route Verification.

#### FR-14: Close-of-Business (COB) Automated Procedure
- **Actor:** System Scheduler (Cron) or Authorized Supervisor.
- **Trigger:** Daily schedule at 18:00 East Africa Time (EAT) or manual trigger.
- **Expected Behavior:** The system shall execute the MySQL stored procedure `sp_run_cob_procedure`, performing:
  1. Reconciling total daily meals claimed against enrolled student counts per school.
  2. Executing ledger audit verifying that all transactions today have committed blockchain hashes.
  3. Generating daily aggregated fraud summary statistics.
  4. Auto-escalating un-triaged high-severity cases past 24 hours.
  5. Harvesting investigator labels from resolved cases for model retraining.
- **Output:** Atomic entry in `sob_cob_procedures` marked `COMPLETED` or `FAILED`.
- **Verification Method:** Stored Procedure Execution and API Route Verification.

---

### 3.7 Blockchain Integrity & Cryptographic Auditing

#### FR-15: Cryptographic Record Hashing & Ledger Sync
- **Actor:** Asynchronous Blockchain Dispatcher Worker.
- **Trigger:** Creation of beneficiary enrollment, subsidy disbursement, or supplier delivery record.
- **Expected Behavior:** The system shall compute a SHA-256 hash of the canonical record payload, submit the transaction to the permissioned ledger (Hyperledger Fabric channel `dsfmp-channel`), and persist `blockchain_hash`, `blockchain_tx_id`, and `blockchain_status = 'COMMITTED'` into MySQL.
- **Output:** Validated transaction receipt on the permissioned ledger.
- **Exceptions:** If ledger write fails or times out, set `blockchain_status = 'FAILED'`, queue for retry, and log warning without blocking primary API response.
- **Verification Method:** Integration Testing with ledger mock / Fabric client.

#### FR-16: On-Demand Database Tamper Audit & Mismatch Flagging
- **Actor:** System Admin, Fraud Analyst, External Auditor.
- **Trigger:** User initiates cryptographic integrity audit via API or UI.
- **Expected Behavior:** The system shall re-hash existing MySQL table rows and execute cryptographic comparison against the immutable ledger hash (`blockchain_ledger.payload_hash`). Any disparity indicates direct database tampering and shall immediately generate a `CRITICAL` alert with entity details and timestamps.
- **Output:** Verification status report indicating `VERIFIED` or `TAMPERED` for each audited record.
- **Verification Method:** Demonstration with simulated database injection / tampering test.

---

### 3.8 Model Governance, Administration & Analytics

#### FR-17: Model Performance Metrics, Drift Monitoring & Live Inference Testing
- **Actor:** System Admin, ML Engineer, Fraud Analyst.
- **Trigger:** Scheduled weekly evaluation, post-retraining event, or interactive manual inspection.
- **Expected Behavior:** The system shall query `ml_models` and `ml_model_metrics`, exposing live precision, recall, F1-score, False Positive Rate (FPR), and Kolmogorov-Smirnov / PSI drift indicators. Furthermore, the system shall provide an interactive live inference sandbox (`IsolationForestTester.tsx`) allowing analysts to inject arbitrary or preset fraud vectors, adjust decision thresholds dynamically, and visualize real-time feature attributions and latency.
- **Output:** Model governance dashboard view with drift health badges and real-time interactive inference tester (`/model-performance`).
- **Implementation Status:** Operational (`routes/model_performance.py`, `Frontend/src/app/pages/ModelPerformance.tsx`, `IsolationForestTester.tsx`).
- **Verification Method:** Demonstration and Statistical Verification (9/9 automated test pass).

#### FR-18: Visual Analytics Dashboard & Data Aggregation
- **Actor:** Fraud Analyst, County Officer, Executive Stakeholder.
- **Trigger:** User loads Dashboard view.
- **Expected Behavior:** The system shall serve aggregated statistics: Active Alerts count, Monitored Funds at Risk (KES), 14-day alert trend line, Geographic Risk Heatmap across Kenyan counties, and Top Flagged Entities.
- **Output:** Interactive dashboard with cached response delivery ($< 250\text{ ms}$).
- **Verification Method:** Demonstration and User Acceptance.

#### FR-19: Forensic Export Generation (CSV / PDF)
- **Actor:** Fraud Analyst, Compliance Officer.
- **Trigger:** User requests export of alert list, case audit history, or county summary.
- **Expected Behavior:** The system shall compile and stream a sanitized CSV or cryptographically watermarked PDF report containing the filtered dataset, timestamp, and generating user watermark.
- **Output:** Downloadable file stream (`.csv` or `.pdf`).
- **Verification Method:** Demonstration and File Format Inspection.

#### FR-20: Dynamic Risk Parameter & System Configuration
- **Actor:** System Admin.
- **Trigger:** Administrator updates risk weights, tier thresholds, or SLA hours.
- **Expected Behavior:** The system shall update the `system_settings` table, invalidate active Redis configuration caches, log old and new parameter values in `audit_log`, and apply new parameters to all subsequent scoring runs without server restart.
- **Output:** HTTP 200 OK and updated active configuration state.
- **Verification Method:** Demonstration and Configuration Test.

---

## 4. Non-Functional Requirements (NFR)

*Structured according to the ISO/IEC 25010:2023 Product Quality Model.*

```
ISO/IEC 25010:2023 Quality Model Breakdown
├── 1. Performance Efficiency (Latency, Throughput, Resource Utilization)
├── 2. Security & Privacy (Confidentiality, Integrity, Non-repudiation, RBAC)
├── 3. Reliability & Availability (Fault Tolerance, Recoverability, Transactional Atomicity)
├── 4. Usability & Accessibility (Operability, Error Protection, WCAG 2.1 AA)
├── 5. Compatibility & Interoperability (API Standards, Protocol Conformance)
├── 6. Maintainability & Testability (Modularity, Code Quality, Test Coverage)
├── 7. AI/ML Quality & Explainability (Precision, Robustness, Explainability)
└── 8. Safety & Accountability (Human-in-the-loop, Immutable Audit Trails)
```

---

### 4.1 Performance Efficiency

#### NFR-01: Real-Time Scoring API Response Latency
- **Requirement:** Under normal operational load (up to 50 concurrent requests), the API endpoint `POST /api/models/isolation-forest/infer` and composite scoring dispatcher shall complete feature extraction, multi-model scoring, composite risk calculation, and database persistence within **$\le 500\text{ ms}$ for $95\%$ of requests ($p95$)**, and $\le 1000\text{ ms}$ for $99\%$ of requests ($p99$).
- **Rationale:** Ensures financial transactions and meal logs are evaluated in near-real-time without causing gateway timeouts.
- **Implementation Status:** Verified for active Isolation Forest pipeline; single-sample inference latency consistently measures between **$20\text{--}95\text{ ms}$** via FastAPI pre-warmed lifespan cache.
- **Verification Method:** Automated load testing and microsecond performance profiling (`test_model_inference.py`).

#### NFR-02: High-Throughput Batch Processing Capacity
- **Requirement:** The Start-of-Business (SOB) and Close-of-Business (COB) stored procedures shall process up to **$50,000$ daily transaction records within $\le 30\text{ seconds}$** total execution time when running on standard server hardware (4 vCPUs, 8 GB RAM).
- **Rationale:** Guarantees that daily opening and closing batch procedures do not delay operational school feeding hours.
- **Verification Method:** Measurement of procedure duration across synthetic test datasets.

---

### 4.2 Security & Privacy

#### NFR-03: Cryptographic Hashing & Password Storage
- **Requirement:** All user passwords shall be hashed using **bcrypt** with a minimum work factor (cost) of **12**. All cryptographic ledger hashes and record digests shall use **SHA-256**. All data in transit shall be encrypted using **TLS 1.3**.
- **Rationale:** Complies with Kenya Data Protection Act (KDPA 2019) and OWASP Application Security Verification Standards.
- **Verification Method:** Security Inspection and Cryptographic Configuration Audit.

#### NFR-04: Role-Based Access Control (RBAC) & Least Privilege
- **Requirement:** Access to API endpoints and UI modules shall strictly enforce RBAC. Any attempt by a user with role `fraud_analyst` to access administrator configuration endpoints (`/api/settings/*`) shall be blocked and return **HTTP 403 Forbidden**, while logging a security event in `audit_log`.
- **Rationale:** Enforces segregation of duties between investigators and system administrators.
- **Verification Method:** Automated Security Permission Test Matrix.

---

### 4.3 Reliability & Availability

#### NFR-05: Transactional Consistency & Atomic Database Rollback
- **Requirement:** All multi-table mutations (including SOB/COB procedures, case creation from alerts, and user updates) shall execute within ACID-compliant database transactions. In the event of an unhandled exception or network failure, the system shall **roll back $100\%$ of partial changes**, leaving zero orphaned or corrupted records.
- **Rationale:** Prevents financial ledger discrepancies and corrupted audit states.
- **Verification Method:** Fault injection testing during batch execution.

#### NFR-06: System Availability & Operational Uptime
- **Requirement:** The system shall maintain an operational availability of **$\ge 99.5\%$ uptime** during core business hours (06:00 to 20:00 EAT, Monday through Saturday), excluding pre-announced scheduled maintenance windows.
- **Rationale:** Ensures uninterrupted fraud surveillance during school meal distribution and supplier delivery cycles.
- **Verification Method:** Continuous uptime monitoring and health check endpoint measurement.

---

### 4.4 Usability & Accessibility

#### NFR-07: User Interface Design & Accessibility Standards
- **Requirement:** The React dashboard shall adhere to **WCAG 2.1 Level AA** guidelines for color contrast (minimum contrast ratio of 4.5:1 for standard text) and keyboard navigability. Severity tiers shall use distinct iconography alongside color coding (`CRITICAL` Red, `HIGH` Amber, `MEDIUM` Blue, `LOW` Gray) to accommodate color-blind investigators.
- **Rationale:** Ensures usability for diverse government and county field personnel.
- **Verification Method:** Automated accessibility audit (Lighthouse / axe-core) and user evaluation.

---

### 4.5 Compatibility & Interoperability

#### NFR-08: Standardized RESTful JSON Interoperability
- **Requirement:** All public and internal APIs shall strictly conform to OpenAPI (Swagger 3.0) specifications, utilizing standard HTTP status codes (`200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity`, `500 Internal Error`) and standard `application/json` payload encoding.
- **Rationale:** Facilitates seamless integration with external DSFMP sub-modules and future Hyperledger Fabric gateway nodes.
- **Verification Method:** Automated OpenAPI schema contract validation.

---

### 4.6 Maintainability & Testability

#### NFR-09: Codebase Modularity & Automated Test Coverage
- **Requirement:** The backend codebase shall enforce clean architectural separation into `routes`, `services`, `models`, `database`, `ml`, and `blockchain` layers. The codebase shall maintain a minimum of **$\ge 75\%$ automated unit and integration test coverage** across all service endpoints and scoring pipelines.
- **Rationale:** Prevents regression bugs during ongoing maintenance and refactoring.
- **Verification Method:** CI/CD test execution with `pytest --cov`.

---

### 4.7 AI/ML Quality, Robustness & Human Oversight

#### NFR-10: ML Model Performance Benchmark Thresholds
- **Requirement:** The ensemble ML anomaly detection engine shall achieve a minimum **Precision of $\ge 85\%$**, **Recall of $\ge 80\%$**, and a **False Positive Rate (FPR) of $\le 5\%$** on historical evaluation benchmark datasets.
- **Rationale:** Minimizes investigation fatigue caused by excessive false alarms while reliably catching true fraud instances.
- **Verification Method:** Offline model evaluation using cross-validation test splits.

#### NFR-11: Model Transparency & Explainability
- **Requirement:** For every alert or scored transaction with a risk score $\ge 0.60$, the system shall compute and return plain-language contributing fraud drivers (e.g., "Off-hours transaction detected (Hour 2:00)", "Disproportionate amount: 4.5x higher than school average", "Inflated per-student cost: KES 190,000/student"), along with transformed feature values (`hour_of_day`, `amount_to_school_avg_ratio`, `rolling_24h_count`).
- **Rationale:** Supports administrative due process and legal requirements when sanctioning fraudulent suppliers or schools.
- **Implementation Status:** Operational in `scoring_engine.py` and rendered in both the `IsolationForestTester` sandbox and `TransactionMonitor` slide-out drawer.
- **Verification Method:** Demonstration of feature attribution breakdown in Alert Details modal and automated assertions in `test_model_inference.py`.

#### NFR-12: Human-in-the-Loop Principle & Immutable Audit Logging
- **Requirement:** No punitive action (such as freezing school meal allocations or terminating supplier contracts) shall be executed autonomously by the ML engine without explicit human investigator confirmation. Every state change, alert dismissal, parameter edit, and login shall be immutably recorded in `audit_log` containing `user_id`, `action`, `entity_type`, `entity_id`, `ip_address`, and `timestamp`.
- **Rationale:** Guarantees ethical AI deployment and full accountability.
- **Verification Method:** Inspection of `audit_log` records during end-to-end user workflows.

---

## 5. Interface & Data Requirements

### 5.1 External & Internal Interface Requirements (IR)
- **IR-01 (Database Interface):** The backend shall connect to MySQL 8.x using asynchronous connection pooling (`aiomysql` + SQLAlchemy 2.0) with automated connection recycling every 1800 seconds.
- **IR-02 (Cache & Session Store):** The backend shall interface with Redis 7.x for real-time risk score caching and JWT revocation checking with sub-millisecond query latency.
- **IR-03 (Blockchain Gateway):** The system shall expose an asynchronous dispatch queue communicating with the Hyperledger Fabric Node SDK / REST Gateway using gRPC/TLS.
- **IR-04 (Frontend-Backend API):** The React frontend shall communicate with FastAPI using Axios clients with JWT Bearer authentication interceptors and automatic token refresh handling.

### 5.2 Data Requirements (DR)
- **DR-01 (Data Retention):** Active transaction and meal records shall be retained online for a minimum of 7 years in accordance with public sector financial regulations.
- **DR-02 (Data Privacy & Masking):** Personally Identifiable Information (PII) of student beneficiaries (e.g., student full names, guardian phone numbers) shall be masked in analyst views unless explicit forensic drill-down permissions are granted.
- **DR-03 (Data Consistency):** Entity risk scores in `risk_profiles` must strictly match the latest calculation derived from composite model outputs within a maximum synchronization lag of 10 seconds.
- **DR-04 (Blockchain Payload Canonicalization):** All record payloads passed to cryptographic hashing functions must be serialized into deterministic canonical JSON (sorted keys, no extraneous whitespace) to ensure identical hash generation across distributed nodes.

---

*DSFMP Fraud Detection Module | Requirements Specification | Compliant with ISO/IEC/IEEE 29148:2018 & ISO/IEC 25010:2023*
