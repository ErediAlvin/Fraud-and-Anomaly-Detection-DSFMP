import asyncio
from database.connection import engine
from sqlalchemy import text

async def run_migration():
    print("Running migration for ingestion pipeline...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("""
                ALTER TABLE transactions 
                MODIFY COLUMN risk_tier ENUM('LOW','MEDIUM','HIGH','CRITICAL','EVALUATING') NULL
            """))
            print("[OK] transactions.risk_tier modified to include 'EVALUATING'")
        except Exception as e:
            print(f"[WARN] Error modifying transactions.risk_tier: {e}")

        try:
            # Check if batch_id column exists
            res = await conn.execute(text("SHOW COLUMNS FROM transactions LIKE 'batch_id'"))
            if not res.fetchone():
                await conn.execute(text("""
                    ALTER TABLE transactions 
                    ADD COLUMN batch_id VARCHAR(64) NULL AFTER status
                """))
                print("[OK] Added batch_id column to transactions")
            else:
                print("[OK] transactions.batch_id already exists")
        except Exception as e:
            print(f"[WARN] Error adding batch_id: {e}")

        try:
            await conn.execute(text("""
                ALTER TABLE fraud_alerts 
                MODIFY COLUMN alert_type ENUM(
                    'GHOST_BENEFICIARY',
                    'PAYMENT_ANOMALY',
                    'SUPPLY_CHAIN_IRREGULARITY',
                    'COLLUSION_DETECTED',
                    'ENROLLMENT_SPIKE',
                    'TEMPORAL_ANOMALY',
                    'DUPLICATE_IDENTITY',
                    'AMOUNT_DEVIATION',
                    'OFF_HOURS_TRANSACTION',
                    'OFF_HOURS_DRAIN',
                    'OTHER'
                ) NOT NULL
            """))
            print("[OK] fraud_alerts.alert_type modified to include 'OFF_HOURS_DRAIN'")
        except Exception as e:
            print(f"[WARN] Error modifying fraud_alerts.alert_type: {e}")

    print("Migration completed.")

if __name__ == "__main__":
    asyncio.run(run_migration())
