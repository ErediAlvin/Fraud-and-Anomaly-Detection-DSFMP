-- ============================================================
-- DSFMP FRAUD DETECTION MODULE — DATABASE SCHEMA
-- Digital School Feeding Management Platform
-- ICS C4 Capstone 2026
-- Engine: MySQL 8.x
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ────────────────────────────────────────────────────────────
-- 1. USERS & AUTHENTICATION
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `users` (
  `id`              CHAR(36)        NOT NULL COMMENT 'UUID v4',
  `email`           VARCHAR(255)    NOT NULL,
  `password_hash`   VARCHAR(255)    NOT NULL,
  `first_name`      VARCHAR(100)    NOT NULL,
  `last_name`       VARCHAR(100)    NOT NULL,
  `role`            ENUM(
                      'fraud_analyst',
                      'county_officer',
                      'system_admin',
                      'supervisor',
                      'school_admin'
                    )               NOT NULL DEFAULT 'fraud_analyst',
  `phone`           VARCHAR(20)     NULL,
  `avatar_url`      VARCHAR(512)    NULL,
  `is_active`       BOOLEAN         NOT NULL DEFAULT TRUE,
  `two_fa_secret`   VARCHAR(255)    NULL     COMMENT 'TOTP secret for 2FA',
  `two_fa_enabled`  BOOLEAN         NOT NULL DEFAULT FALSE,
  `last_login_at`   TIMESTAMP       NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS `sessions` (
  `id`              CHAR(36)        NOT NULL,
  `user_id`         CHAR(36)        NOT NULL,
  `token_hash`      VARCHAR(255)    NOT NULL,
  `ip_address`      VARCHAR(45)     NULL,
  `user_agent`      VARCHAR(512)    NULL,
  `expires_at`      TIMESTAMP       NOT NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_sessions_user` (`user_id`),
  KEY `idx_sessions_token` (`token_hash`),
  CONSTRAINT `fk_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS `audit_log` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`         CHAR(36)        NULL,
  `action`          VARCHAR(100)    NOT NULL COMMENT 'e.g. LOGIN, CASE_UPDATE, ALERT_DISMISS',
  `entity_type`     VARCHAR(50)     NULL     COMMENT 'Table/resource affected',
  `entity_id`       VARCHAR(100)    NULL     COMMENT 'PK of affected record',
  `details`         JSON            NULL     COMMENT 'Freeform change payload',
  `ip_address`      VARCHAR(45)     NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audit_user` (`user_id`),
  KEY `idx_audit_action` (`action`),
  KEY `idx_audit_entity` (`entity_type`, `entity_id`),
  CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 2. GEOGRAPHIC HIERARCHY
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `counties` (
  `id`              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  `name`            VARCHAR(100)    NOT NULL,
  `code`            VARCHAR(10)     NOT NULL COMMENT 'County code e.g. 047',
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_counties_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS `sub_counties` (
  `id`              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  `county_id`       INT UNSIGNED    NOT NULL,
  `name`            VARCHAR(100)    NOT NULL,
  `code`            VARCHAR(20)     NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_subcounty_county` (`county_id`),
  CONSTRAINT `fk_subcounty_county` FOREIGN KEY (`county_id`) REFERENCES `counties`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 3. SCHOOLS
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `schools` (
  `id`              CHAR(36)        NOT NULL,
  `name`            VARCHAR(255)    NOT NULL,
  `nemis_code`      VARCHAR(20)     NOT NULL COMMENT 'National Education Management Information System code',
  `county_id`       INT UNSIGNED    NOT NULL,
  `sub_county_id`   INT UNSIGNED    NULL,
  `level`           ENUM('primary','secondary','special') NOT NULL DEFAULT 'primary',
  `enrollment_count` INT UNSIGNED   NOT NULL DEFAULT 0,
  `latitude`        DECIMAL(10,7)   NULL,
  `longitude`       DECIMAL(10,7)   NULL,
  `contact_phone`   VARCHAR(20)     NULL,
  `contact_email`   VARCHAR(255)    NULL,
  `is_active`       BOOLEAN         NOT NULL DEFAULT TRUE,
  `risk_tier`       ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'LOW',
  `blockchain_hash`    VARCHAR(256) NULL COMMENT 'Cryptographic record hash on Hyperledger',
  `blockchain_tx_id`   VARCHAR(256) NULL COMMENT 'Ledger transaction reference',
  `blockchain_status`  ENUM('PENDING','CONFIRMED','FAILED') NULL,
  `ledger_written_at`  TIMESTAMP    NULL COMMENT 'When blockchain write completed',
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_schools_nemis` (`nemis_code`),
  KEY `idx_schools_county` (`county_id`),
  KEY `idx_schools_risk` (`risk_tier`),
  CONSTRAINT `fk_schools_county` FOREIGN KEY (`county_id`) REFERENCES `counties`(`id`),
  CONSTRAINT `fk_schools_subcounty` FOREIGN KEY (`sub_county_id`) REFERENCES `sub_counties`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 4. BENEFICIARIES (Students)
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `beneficiaries` (
  `id`              CHAR(36)        NOT NULL,
  `school_id`       CHAR(36)        NOT NULL,
  `first_name`      VARCHAR(100)    NOT NULL,
  `last_name`       VARCHAR(100)    NOT NULL,
  `date_of_birth`   DATE            NULL,
  `gender`          ENUM('M','F','OTHER') NULL,
  `guardian_name`   VARCHAR(200)    NULL,
  `guardian_phone`  VARCHAR(20)     NULL,
  `grade`           VARCHAR(20)     NULL,
  `status`          ENUM('ACTIVE','GRADUATED','TRANSFERRED','SUSPENDED','REMOVED') NOT NULL DEFAULT 'ACTIVE',
  `enrollment_date` DATE            NOT NULL,
  `identity_hash`   VARCHAR(256)    NULL     COMMENT 'Fuzzy-match fingerprint for ghost detection',
  `risk_score`      DECIMAL(5,4)    NULL     COMMENT 'ML composite risk score 0.0000–1.0000',
  `risk_tier`       ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'LOW',
  `blockchain_hash`    VARCHAR(256) NULL,
  `blockchain_tx_id`   VARCHAR(256) NULL,
  `blockchain_status`  ENUM('PENDING','CONFIRMED','FAILED') NULL,
  `ledger_written_at`  TIMESTAMP    NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_benef_school` (`school_id`),
  KEY `idx_benef_status` (`status`),
  KEY `idx_benef_risk` (`risk_tier`),
  KEY `idx_benef_identity` (`identity_hash`),
  CONSTRAINT `fk_benef_school` FOREIGN KEY (`school_id`) REFERENCES `schools`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 5. SUPPLIERS
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `suppliers` (
  `id`              CHAR(36)        NOT NULL,
  `name`            VARCHAR(255)    NOT NULL,
  `registration_no` VARCHAR(50)     NOT NULL COMMENT 'Business registration number',
  `county_id`       INT UNSIGNED    NULL,
  `contact_person`  VARCHAR(200)    NULL,
  `contact_phone`   VARCHAR(20)     NULL,
  `contact_email`   VARCHAR(255)    NULL,
  `category`        ENUM('FOOD','LOGISTICS','EQUIPMENT','OTHER') NOT NULL DEFAULT 'FOOD',
  `is_active`       BOOLEAN         NOT NULL DEFAULT TRUE,
  `risk_score`      DECIMAL(5,4)    NULL,
  `risk_tier`       ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'LOW',
  `blockchain_hash`    VARCHAR(256) NULL,
  `blockchain_tx_id`   VARCHAR(256) NULL,
  `blockchain_status`  ENUM('PENDING','CONFIRMED','FAILED') NULL,
  `ledger_written_at`  TIMESTAMP    NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_suppliers_reg` (`registration_no`),
  KEY `idx_suppliers_county` (`county_id`),
  KEY `idx_suppliers_risk` (`risk_tier`),
  CONSTRAINT `fk_suppliers_county` FOREIGN KEY (`county_id`) REFERENCES `counties`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 6. TRANSACTIONS (Payments & Subsidies)
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `transactions` (
  `id`              CHAR(36)        NOT NULL,
  `school_id`       CHAR(36)        NOT NULL,
  `supplier_id`     CHAR(36)        NULL     COMMENT 'NULL for subsidy/government payments',
  `type`            ENUM(
                      'SUBSIDY_DISBURSEMENT',
                      'SUPPLIER_PAYMENT',
                      'PARENTAL_CONTRIBUTION',
                      'MPESA_PAYMENT',
                      'REFUND',
                      'ADJUSTMENT'
                    )               NOT NULL,
  `amount`          DECIMAL(14,2)   NOT NULL,
  `currency`        CHAR(3)         NOT NULL DEFAULT 'KES',
  `reference_no`    VARCHAR(100)    NULL     COMMENT 'M-Pesa confirmation, bank ref, etc.',
  `description`     TEXT            NULL,
  `payment_method`  ENUM('MPESA','BANK_TRANSFER','CHEQUE','CASH','SYSTEM') NOT NULL DEFAULT 'SYSTEM',
  `status`          ENUM('PENDING','COMPLETED','FAILED','REVERSED','FLAGGED') NOT NULL DEFAULT 'PENDING',
  `period_start`    DATE            NULL     COMMENT 'Feeding period this payment covers',
  `period_end`      DATE            NULL,
  `approved_by`     CHAR(36)        NULL,
  `approved_at`     TIMESTAMP       NULL,
  -- ML risk scoring fields
  `risk_score`      DECIMAL(5,4)    NULL     COMMENT 'Composite ML score 0.0000–1.0000',
  `risk_tier`       ENUM('LOW','MEDIUM','HIGH','CRITICAL') NULL,
  `if_score`        DECIMAL(5,4)    NULL     COMMENT 'Isolation Forest anomaly score',
  `ae_score`        DECIMAL(5,4)    NULL     COMMENT 'Autoencoder reconstruction error score',
  `lstm_score`      DECIMAL(5,4)    NULL     COMMENT 'LSTM temporal anomaly score',
  `gnn_score`       DECIMAL(5,4)    NULL     COMMENT 'Graph Neural Network anomaly score',
  -- Blockchain integrity fields
  `blockchain_hash`    VARCHAR(256) NULL,
  `blockchain_tx_id`   VARCHAR(256) NULL,
  `blockchain_status`  ENUM('PENDING','CONFIRMED','FAILED') NULL,
  `ledger_written_at`  TIMESTAMP    NULL,
  `transacted_at`   TIMESTAMP       NOT NULL COMMENT 'When the payment actually occurred',
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_txn_school` (`school_id`),
  KEY `idx_txn_supplier` (`supplier_id`),
  KEY `idx_txn_type` (`type`),
  KEY `idx_txn_status` (`status`),
  KEY `idx_txn_risk` (`risk_tier`),
  KEY `idx_txn_date` (`transacted_at`),
  CONSTRAINT `fk_txn_school` FOREIGN KEY (`school_id`) REFERENCES `schools`(`id`),
  CONSTRAINT `fk_txn_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers`(`id`),
  CONSTRAINT `fk_txn_approved_by` FOREIGN KEY (`approved_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 7. SUPPLY CHAIN — PROCUREMENT & DELIVERIES
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `procurement_orders` (
  `id`              CHAR(36)        NOT NULL,
  `school_id`       CHAR(36)        NOT NULL,
  `supplier_id`     CHAR(36)        NOT NULL,
  `order_date`      DATE            NOT NULL,
  `expected_delivery_date` DATE     NULL,
  `total_amount`    DECIMAL(14,2)   NOT NULL,
  `status`          ENUM('DRAFT','SUBMITTED','APPROVED','DELIVERED','CANCELLED','FLAGGED') NOT NULL DEFAULT 'DRAFT',
  `items_json`      JSON            NOT NULL COMMENT 'Array of {item, quantity, unit_price}',
  `risk_score`      DECIMAL(5,4)    NULL,
  `risk_tier`       ENUM('LOW','MEDIUM','HIGH','CRITICAL') NULL,
  `blockchain_hash`    VARCHAR(256) NULL,
  `blockchain_tx_id`   VARCHAR(256) NULL,
  `blockchain_status`  ENUM('PENDING','CONFIRMED','FAILED') NULL,
  `ledger_written_at`  TIMESTAMP    NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_po_school` (`school_id`),
  KEY `idx_po_supplier` (`supplier_id`),
  KEY `idx_po_status` (`status`),
  CONSTRAINT `fk_po_school` FOREIGN KEY (`school_id`) REFERENCES `schools`(`id`),
  CONSTRAINT `fk_po_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS `deliveries` (
  `id`              CHAR(36)        NOT NULL,
  `procurement_order_id` CHAR(36)   NOT NULL,
  `school_id`       CHAR(36)        NOT NULL,
  `supplier_id`     CHAR(36)        NOT NULL,
  `delivered_at`    TIMESTAMP       NOT NULL,
  `received_by`     VARCHAR(200)    NULL     COMMENT 'Name of person who confirmed receipt',
  `quantity_delivered` DECIMAL(10,2) NOT NULL,
  `quantity_ordered`   DECIMAL(10,2) NOT NULL,
  `discrepancy_pct` DECIMAL(5,2)    NULL     COMMENT 'Percentage difference from order',
  `status`          ENUM('CONFIRMED','PARTIAL','DISPUTED','REJECTED') NOT NULL DEFAULT 'CONFIRMED',
  `notes`           TEXT            NULL,
  `risk_score`      DECIMAL(5,4)    NULL,
  `blockchain_hash`    VARCHAR(256) NULL,
  `blockchain_tx_id`   VARCHAR(256) NULL,
  `blockchain_status`  ENUM('PENDING','CONFIRMED','FAILED') NULL,
  `ledger_written_at`  TIMESTAMP    NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_del_po` (`procurement_order_id`),
  KEY `idx_del_school` (`school_id`),
  CONSTRAINT `fk_del_po` FOREIGN KEY (`procurement_order_id`) REFERENCES `procurement_orders`(`id`),
  CONSTRAINT `fk_del_school` FOREIGN KEY (`school_id`) REFERENCES `schools`(`id`),
  CONSTRAINT `fk_del_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 8. MEAL RECORDS
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `meal_records` (
  `id`              CHAR(36)        NOT NULL,
  `school_id`       CHAR(36)        NOT NULL,
  `meal_date`       DATE            NOT NULL,
  `meal_type`       ENUM('BREAKFAST','LUNCH','SNACK') NOT NULL DEFAULT 'LUNCH',
  `students_served` INT UNSIGNED    NOT NULL,
  `recorded_by`     CHAR(36)        NULL,
  `notes`           TEXT            NULL,
  `risk_score`      DECIMAL(5,4)    NULL     COMMENT 'Anomaly score — meals vs enrollment ratio',
  `blockchain_hash`    VARCHAR(256) NULL,
  `blockchain_tx_id`   VARCHAR(256) NULL,
  `blockchain_status`  ENUM('PENDING','CONFIRMED','FAILED') NULL,
  `ledger_written_at`  TIMESTAMP    NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_meals_school` (`school_id`),
  KEY `idx_meals_date` (`meal_date`),
  UNIQUE KEY `uq_meals_school_date_type` (`school_id`, `meal_date`, `meal_type`),
  CONSTRAINT `fk_meals_school` FOREIGN KEY (`school_id`) REFERENCES `schools`(`id`),
  CONSTRAINT `fk_meals_recorded_by` FOREIGN KEY (`recorded_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 9. FRAUD ALERTS
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `fraud_alerts` (
  `id`              CHAR(36)        NOT NULL,
  `alert_type`      ENUM(
                      'GHOST_BENEFICIARY',
                      'PAYMENT_ANOMALY',
                      'SUPPLY_CHAIN_IRREGULARITY',
                      'COLLUSION_DETECTED',
                      'ENROLLMENT_SPIKE',
                      'TEMPORAL_ANOMALY',
                      'DUPLICATE_IDENTITY',
                      'AMOUNT_DEVIATION',
                      'OFF_HOURS_TRANSACTION',
                      'OTHER'
                    )               NOT NULL,
  `severity`        ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL,
  `title`           VARCHAR(255)    NOT NULL,
  `description`     TEXT            NOT NULL,
  `entity_type`     VARCHAR(50)     NOT NULL COMMENT 'transaction, beneficiary, school, supplier, etc.',
  `entity_id`       CHAR(36)        NOT NULL COMMENT 'PK of the flagged record',
  `school_id`       CHAR(36)        NULL,
  `county_id`       INT UNSIGNED    NULL,
  -- ML model scores at time of alert
  `composite_score` DECIMAL(5,4)    NOT NULL COMMENT 'Overall risk score that triggered the alert',
  `if_score`        DECIMAL(5,4)    NULL,
  `ae_score`        DECIMAL(5,4)    NULL,
  `lstm_score`      DECIMAL(5,4)    NULL,
  `gnn_score`       DECIMAL(5,4)    NULL,
  `model_version`   VARCHAR(50)     NULL     COMMENT 'Version tag of the scoring model',
  -- Workflow
  `status`          ENUM('NEW','ACKNOWLEDGED','INVESTIGATING','ESCALATED','RESOLVED','DISMISSED') NOT NULL DEFAULT 'NEW',
  `assigned_to`     CHAR(36)        NULL,
  `resolved_at`     TIMESTAMP       NULL,
  `resolution_notes` TEXT           NULL,
  `is_true_positive` BOOLEAN        NULL     COMMENT 'Feedback for model retraining',
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_alert_type` (`alert_type`),
  KEY `idx_alert_severity` (`severity`),
  KEY `idx_alert_status` (`status`),
  KEY `idx_alert_school` (`school_id`),
  KEY `idx_alert_county` (`county_id`),
  KEY `idx_alert_entity` (`entity_type`, `entity_id`),
  KEY `idx_alert_assigned` (`assigned_to`),
  CONSTRAINT `fk_alert_school` FOREIGN KEY (`school_id`) REFERENCES `schools`(`id`),
  CONSTRAINT `fk_alert_county` FOREIGN KEY (`county_id`) REFERENCES `counties`(`id`),
  CONSTRAINT `fk_alert_assigned` FOREIGN KEY (`assigned_to`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 10. CASE MANAGEMENT
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `cases` (
  `id`              CHAR(36)        NOT NULL,
  `case_number`     VARCHAR(30)     NOT NULL COMMENT 'Human-readable e.g. DSFMP-2026-00042',
  `title`           VARCHAR(255)    NOT NULL,
  `description`     TEXT            NOT NULL,
  `priority`        ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'MEDIUM',
  `status`          ENUM('OPEN','IN_PROGRESS','PENDING_REVIEW','ESCALATED','CLOSED') NOT NULL DEFAULT 'OPEN',
  `category`        ENUM(
                      'GHOST_BENEFICIARY',
                      'PAYMENT_FRAUD',
                      'SUPPLY_CHAIN',
                      'COLLUSION',
                      'DATA_TAMPERING',
                      'OTHER'
                    )               NOT NULL,
  `school_id`       CHAR(36)        NULL,
  `county_id`       INT UNSIGNED    NULL,
  `assigned_to`     CHAR(36)        NULL,
  `created_by`      CHAR(36)        NOT NULL,
  `estimated_loss`  DECIMAL(14,2)   NULL     COMMENT 'Estimated financial impact in KES',
  `actual_loss`     DECIMAL(14,2)   NULL     COMMENT 'Confirmed financial loss',
  `closed_at`       TIMESTAMP       NULL,
  `closure_reason`  TEXT            NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_cases_number` (`case_number`),
  KEY `idx_cases_status` (`status`),
  KEY `idx_cases_priority` (`priority`),
  KEY `idx_cases_school` (`school_id`),
  KEY `idx_cases_assigned` (`assigned_to`),
  CONSTRAINT `fk_cases_school` FOREIGN KEY (`school_id`) REFERENCES `schools`(`id`),
  CONSTRAINT `fk_cases_county` FOREIGN KEY (`county_id`) REFERENCES `counties`(`id`),
  CONSTRAINT `fk_cases_assigned` FOREIGN KEY (`assigned_to`) REFERENCES `users`(`id`),
  CONSTRAINT `fk_cases_created_by` FOREIGN KEY (`created_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS `case_alerts` (
  `case_id`         CHAR(36)        NOT NULL,
  `alert_id`        CHAR(36)        NOT NULL,
  `linked_at`       TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`case_id`, `alert_id`),
  CONSTRAINT `fk_ca_case` FOREIGN KEY (`case_id`) REFERENCES `cases`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ca_alert` FOREIGN KEY (`alert_id`) REFERENCES `fraud_alerts`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS `case_comments` (
  `id`              CHAR(36)        NOT NULL,
  `case_id`         CHAR(36)        NOT NULL,
  `user_id`         CHAR(36)        NOT NULL,
  `content`         TEXT            NOT NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_comments_case` (`case_id`),
  CONSTRAINT `fk_comments_case` FOREIGN KEY (`case_id`) REFERENCES `cases`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comments_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS `case_attachments` (
  `id`              CHAR(36)        NOT NULL,
  `case_id`         CHAR(36)        NOT NULL,
  `uploaded_by`     CHAR(36)        NOT NULL,
  `file_name`       VARCHAR(255)    NOT NULL,
  `file_path`       VARCHAR(512)    NOT NULL,
  `file_size`       INT UNSIGNED    NOT NULL COMMENT 'Bytes',
  `mime_type`       VARCHAR(100)    NOT NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_attach_case` (`case_id`),
  CONSTRAINT `fk_attach_case` FOREIGN KEY (`case_id`) REFERENCES `cases`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_attach_user` FOREIGN KEY (`uploaded_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 11. RISK PROFILES (Per-entity risk snapshots)
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `risk_profiles` (
  `id`              CHAR(36)        NOT NULL,
  `entity_type`     ENUM('SCHOOL','SUPPLIER','BENEFICIARY') NOT NULL,
  `entity_id`       CHAR(36)        NOT NULL,
  `composite_score` DECIMAL(5,4)    NOT NULL,
  `risk_tier`       ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL,
  `status`          ENUM('CLEAN','WATCHLIST','SUSPENDED') NOT NULL DEFAULT 'CLEAN',
  `if_score`        DECIMAL(5,4)    NULL,
  `ae_score`        DECIMAL(5,4)    NULL,
  `lstm_score`      DECIMAL(5,4)    NULL,
  `gnn_score`       DECIMAL(5,4)    NULL,
  `factors_json`    JSON            NULL     COMMENT 'Breakdown of risk contributing factors',
  `trend`           ENUM('IMPROVING','STABLE','DETERIORATING') NULL,
  `last_scored_at`  TIMESTAMP       NOT NULL,
  `model_version`   VARCHAR(50)     NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_risk_entity` (`entity_type`, `entity_id`),
  KEY `idx_risk_tier` (`risk_tier`),
  KEY `idx_risk_score` (`composite_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 12. ML MODEL PERFORMANCE TRACKING
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `ml_models` (
  `id`              CHAR(36)        NOT NULL,
  `name`            VARCHAR(100)    NOT NULL COMMENT 'e.g. isolation_forest, autoencoder, lstm, gnn, xgboost',
  `version`         VARCHAR(50)     NOT NULL,
  `description`     TEXT            NULL,
  `status`          ENUM('TRAINING','ACTIVE','RETIRED','FAILED') NOT NULL DEFAULT 'TRAINING',
  `hyperparams_json` JSON           NULL,
  `artifact_path`   VARCHAR(512)    NULL     COMMENT 'Path to saved model file',
  `trained_at`      TIMESTAMP       NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_model_version` (`name`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS `ml_model_metrics` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `model_id`        CHAR(36)        NOT NULL,
  `metric_name`     VARCHAR(50)     NOT NULL COMMENT 'accuracy, precision, recall, f1, auc_roc, etc.',
  `metric_value`    DECIMAL(8,6)    NOT NULL,
  `dataset`         ENUM('TRAIN','VALIDATION','TEST','PRODUCTION') NOT NULL,
  `sample_size`     INT UNSIGNED    NULL,
  `recorded_at`     TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_metrics_model` (`model_id`),
  KEY `idx_metrics_name` (`metric_name`),
  CONSTRAINT `fk_metrics_model` FOREIGN KEY (`model_id`) REFERENCES `ml_models`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 13. SOB / COB PROCEDURES
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `sob_cob_procedures` (
  `id`              CHAR(36)        NOT NULL,
  `type`            ENUM('SOB','COB')  NOT NULL COMMENT 'Start of Business / Close of Business',
  `procedure_date`  DATE            NOT NULL,
  `performed_by`    CHAR(36)        NOT NULL,
  `status`          ENUM('PENDING','COMPLETED','SKIPPED') NOT NULL DEFAULT 'PENDING',
  `checklist_json`  JSON            NOT NULL COMMENT 'Array of checklist items with completion status',
  `notes`           TEXT            NULL,
  `completed_at`    TIMESTAMP       NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_sobcob_date` (`procedure_date`),
  KEY `idx_sobcob_user` (`performed_by`),
  CONSTRAINT `fk_sobcob_user` FOREIGN KEY (`performed_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 14. BLOCKCHAIN LEDGER LOG (Local mirror of chain events)
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `blockchain_ledger` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tx_id`           VARCHAR(256)    NOT NULL COMMENT 'Hyperledger Fabric transaction ID',
  `block_number`    BIGINT UNSIGNED NULL,
  `channel`         VARCHAR(100)    NOT NULL DEFAULT 'dsfmp-channel',
  `chaincode`       VARCHAR(100)    NOT NULL,
  `function_name`   VARCHAR(100)    NOT NULL,
  `entity_type`     VARCHAR(50)     NOT NULL,
  `entity_id`       CHAR(36)        NOT NULL,
  `payload_hash`    VARCHAR(256)    NOT NULL,
  `status`          ENUM('SUBMITTED','COMMITTED','FAILED') NOT NULL DEFAULT 'SUBMITTED',
  `error_message`   TEXT            NULL,
  `submitted_at`    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `committed_at`    TIMESTAMP       NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ledger_tx` (`tx_id`),
  KEY `idx_ledger_entity` (`entity_type`, `entity_id`),
  KEY `idx_ledger_status` (`status`),
  KEY `idx_ledger_block` (`block_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 15. NOTIFICATIONS
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `notifications` (
  `id`              CHAR(36)        NOT NULL,
  `user_id`         CHAR(36)        NOT NULL,
  `type`            ENUM('ALERT','CASE_UPDATE','SYSTEM','ESCALATION','REMINDER') NOT NULL,
  `title`           VARCHAR(255)    NOT NULL,
  `message`         TEXT            NOT NULL,
  `link`            VARCHAR(512)    NULL     COMMENT 'Deep link to related entity in dashboard',
  `is_read`         BOOLEAN         NOT NULL DEFAULT FALSE,
  `read_at`         TIMESTAMP       NULL,
  `created_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_notif_user` (`user_id`),
  KEY `idx_notif_read` (`user_id`, `is_read`),
  CONSTRAINT `fk_notif_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ────────────────────────────────────────────────────────────
-- 16. SYSTEM SETTINGS
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `system_settings` (
  `key`             VARCHAR(100)    NOT NULL,
  `value`           TEXT            NOT NULL,
  `description`     VARCHAR(255)    NULL,
  `category`        VARCHAR(50)     NOT NULL DEFAULT 'general',
  `updated_by`      CHAR(36)        NULL,
  `updated_at`      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`key`),
  KEY `idx_settings_category` (`category`),
  CONSTRAINT `fk_settings_user` FOREIGN KEY (`updated_by`) REFERENCES `users`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- END OF SCHEMA
-- ============================================================
