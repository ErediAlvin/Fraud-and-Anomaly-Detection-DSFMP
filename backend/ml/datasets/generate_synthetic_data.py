"""
DSFMP Fraud Detection System — Synthetic Data Generator
Uses Python's Faker library to generate realistic synthetic school feeding
transaction records with embedded fraud patterns for training anomaly detection
models (specifically Isolation Forest).

Features:
- Realistic Kenyan school feeding operational domain (Schools, Counties, Suppliers, M-Pesa).
- Ground truth labeling (is_fraud = 0 or 1) with specific fraud pattern typologies.
- Tabular feature extraction suitable for Isolation Forest training.
- Export to CSV format for training and evaluation.
"""

import argparse
import os
import uuid
import random
import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np
from faker import Faker

# Initialize Faker with Kenyan locale context
fake = Faker(['en_US'])
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# ────────────────────────────────────────────────────────────
# Domain Reference Data
# ────────────────────────────────────────────────────────────

COUNTIES = [
    {"name": "Nairobi", "code": 47, "sub_counties": ["Westlands", "Kibra", "Dagoretti North", "Embakasi East", "Kasarani"]},
    {"name": "Mombasa", "code": 1, "sub_counties": ["Mvita", "Nyali", "Changamwe", "Likoni", "Kisauni"]},
    {"name": "Kisumu", "code": 42, "sub_counties": ["Kisumu Central", "Kisumu East", "Kisumu West", "Nyando", "Seme"]},
    {"name": "Nakuru", "code": 32, "sub_counties": ["Nakuru Town East", "Nakuru Town West", "Naivasha", "Rongai"]},
    {"name": "Kilifi", "code": 3, "sub_counties": ["Kilifi North", "Malindi", "Magarini", "Kaloleni"]},
    {"name": "Turkana", "code": 23, "sub_counties": ["Turkana Central", "Turkana West", "Loima", "Turkana North"]},
    {"name": "Machakos", "code": 16, "sub_counties": ["Machakos Town", "Mavoko", "Kangundo", "Kathiani"]},
    {"name": "Uasin Gishu", "code": 27, "sub_counties": ["Ainabkoi", "Kapseret", "Kesses", "Soy"]}
]

SCHOOL_NAMES_PREFIX = [
    "Moi", "Kenyatta", "Olympic", "Highway", "St. Peters", "St. Anne's", "Barani",
    "Highlands", "Valley View", "Kilimani", "Pumwani", "Makini", "Lakeview",
    "Hillcrest", "Sunrise", "Nyali", "Kibera", "Westlands", "Langata", "Eldoret"
]

SCHOOL_TYPES = ["Primary School", "Junior Secondary School", "Day Secondary School", "Academy"]

TRANSACTION_TYPES = [
    "SUBSIDY_DISBURSEMENT",
    "SUPPLIER_PAYMENT",
    "PARENTAL_CONTRIBUTION",
    "MPESA_PAYMENT",
    "REFUND",
    "ADJUSTMENT"
]

PAYMENT_METHODS = ["MPESA", "BANK_TRANSFER", "CHEQUE", "CASH", "SYSTEM"]

SUPPLIER_CATEGORIES = ["FOOD", "LOGISTICS", "EQUIPMENT", "CLEANING", "SERVICES"]

FOOD_ITEMS = [
    "Dry Maize & Beans (Githeri mix)", "Fortified Porridge Flour (Wimbi)",
    "White Long Grain Rice", "Green Grams (Ndengu)", "Fortified Vegetable Cooking Oil",
    "Fresh Cow Milk", "Vegetable Assortment (Kales & Cabbages)", "Iodized Table Salt"
]

# ────────────────────────────────────────────────────────────
# Entity Generators
# ────────────────────────────────────────────────────────────

def generate_schools(count: int = 40) -> List[Dict[str, Any]]:
    """Generates synthetic schools across Kenyan counties."""
    schools = []
    for i in range(count):
        county_info = random.choice(COUNTIES)
        prefix = random.choice(SCHOOL_NAMES_PREFIX)
        stype = random.choice(SCHOOL_TYPES)
        name = f"{prefix} {stype}"
        sub_county = random.choice(county_info["sub_counties"])
        student_count = random.randint(120, 1400)
        
        # Expected baseline metrics
        daily_meal_budget_per_student = random.uniform(35.0, 65.0)  # KES per student per day
        term_feeding_days = 65
        expected_term_budget = round(student_count * daily_meal_budget_per_student * term_feeding_days, 2)
        
        schools.append({
            "school_id": str(uuid.uuid4()),
            "name": name,
            "county": county_info["name"],
            "sub_county": sub_county,
            "student_count": student_count,
            "expected_term_budget": expected_term_budget,
            "avg_transaction_amount": round(expected_term_budget / random.randint(8, 20), 2)
        })
    return schools


def generate_suppliers(count: int = 25) -> List[Dict[str, Any]]:
    """Generates synthetic suppliers with business profiles."""
    suppliers = []
    supplier_suffixes = ["Ltd", "Enterprises", "Millers & Suppliers", "Food Distributors", "Supplies Co.", "Logistics"]
    
    for i in range(count):
        county_info = random.choice(COUNTIES)
        category = random.choices(SUPPLIER_CATEGORIES, weights=[0.60, 0.20, 0.10, 0.05, 0.05])[0]
        company_name = f"{fake.last_name()} {random.choice(supplier_suffixes)}"
        
        suppliers.append({
            "supplier_id": str(uuid.uuid4()),
            "name": company_name,
            "category": category,
            "county": county_info["name"],
            "registration_no": f"REG-{random.randint(100000, 999999)}",
            "contact_phone": f"+2547{random.randint(10000000, 99999999)}",
            "historical_volume_mean": round(random.uniform(75000, 350000), 2)
        })
    return suppliers


def generate_mpesa_reference() -> str:
    """Generates authentic looking Kenyan M-Pesa transaction codes (e.g. QK83X109Z8)."""
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    digits = "0123456789"
    code = (
        random.choice(letters) +
        random.choice(letters) +
        random.choice(digits) +
        random.choice(digits) +
        random.choice(letters) +
        random.choice(digits) +
        random.choice(digits) +
        random.choice(digits) +
        random.choice(letters) +
        random.choice(digits)
    )
    return code


# ────────────────────────────────────────────────────────────
# Core Synthetic Transaction Generator
# ────────────────────────────────────────────────────────────

class SyntheticDataGenerator:
    """
    Generates synthetic transaction logs with normal and fraud patterns,
    tailored for training Isolation Forest and tabular anomaly detection.
    """

    def __init__(self, start_date: datetime = None, end_date: datetime = None):
        self.end_date = end_date or datetime.now(timezone.utc)
        self.start_date = start_date or (self.end_date - timedelta(days=365))
        self.schools = generate_schools(count=50)
        self.suppliers = generate_suppliers(count=30)
        
        # Mapping for fast lookup
        self.school_map = {s["school_id"]: s for s in self.schools}
        self.supplier_map = {s["supplier_id"]: s for s in self.suppliers}

    def _random_timestamp(self, is_off_hours: bool = False, force_weekend: bool = False) -> datetime:
        """Returns a timestamp with controllable temporal features."""
        total_seconds = int((self.end_date - self.start_date).total_seconds())
        offset = random.randint(0, total_seconds)
        dt = self.start_date + timedelta(seconds=offset)

        if is_off_hours:
            # Pick midnight to early morning (23:00 to 04:59)
            hour = random.choice([23, 0, 1, 2, 3, 4])
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            dt = dt.replace(hour=hour, minute=minute, second=second)
        else:
            # Normal working hours: 08:00 to 17:30
            hour = random.randint(8, 17)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            dt = dt.replace(hour=hour, minute=minute, second=second)

        if force_weekend and dt.weekday() < 5:
            # Shift to Saturday (5) or Sunday (6)
            days_to_add = 5 - dt.weekday()
            dt = dt + timedelta(days=days_to_add)
            
        return dt

    def generate_normal_transaction(self) -> Dict[str, Any]:
        """Generates a standard, legitimate school feeding transaction."""
        school = random.choice(self.schools)
        txn_type = random.choices(
            TRANSACTION_TYPES,
            weights=[0.15, 0.45, 0.25, 0.10, 0.03, 0.02]
        )[0]

        timestamp = self._random_timestamp(is_off_hours=False)
        student_count = school["student_count"]

        supplier = None
        supplier_id = None
        supplier_name = None
        supplier_cat = "NONE"

        if txn_type == "SUBSIDY_DISBURSEMENT":
            # Government feeding grant to school account
            # Typically KES 1,000 to KES 2,500 per student per tranche
            base_amount = student_count * random.uniform(800.0, 2200.0)
            amount = round(base_amount, 2)
            payment_method = random.choice(["SYSTEM", "BANK_TRANSFER"])
            ref_no = f"TXN-SUB-{random.randint(100000, 999999)}"
            description = f"Term Feeding Subsidy Allocation - {student_count} Enrolled Beneficiaries"

        elif txn_type == "SUPPLIER_PAYMENT":
            supplier = random.choice(self.suppliers)
            supplier_id = supplier["supplier_id"]
            supplier_name = supplier["name"]
            supplier_cat = supplier["category"]
            
            # Payment aligned with reasonable batch sizes
            food_item = random.choice(FOOD_ITEMS)
            # Normal order: KES 15,000 to KES 350,000 depending on school size
            scale = math.sqrt(student_count / 500.0)
            amount = round(random.uniform(25000.0, 280000.0) * scale, 2)
            payment_method = random.choices(["BANK_TRANSFER", "CHEQUE", "MPESA"], weights=[0.70, 0.20, 0.10])[0]
            ref_no = generate_mpesa_reference() if payment_method == "MPESA" else f"BTR-{random.randint(100000, 999999)}"
            description = f"Payment for supply of {food_item} - Inv #{random.randint(100, 9999)}"

        elif txn_type == "PARENTAL_CONTRIBUTION":
            # Small co-pay contributions from parents
            amount = round(random.choice([500.0, 1000.0, 1200.0, 1500.0, 2000.0, 2500.0, 3000.0]), 2)
            payment_method = "MPESA"
            ref_no = generate_mpesa_reference()
            description = f"Parental feeding contribution for Grade {random.randint(1, 8)} pupil"

        elif txn_type == "MPESA_PAYMENT":
            # Routine emergency kitchen ingredient purchase or petty cash
            amount = round(random.uniform(1500.0, 18000.0), 2)
            payment_method = "MPESA"
            ref_no = generate_mpesa_reference()
            description = f"Emergency perishable foodstuffs (vegetables & condiments)"

        elif txn_type == "REFUND":
            amount = round(random.uniform(3000.0, 45000.0), 2)
            payment_method = random.choice(["BANK_TRANSFER", "MPESA"])
            ref_no = f"REF-{random.randint(100000, 999999)}"
            description = "Overpayment reversal / returned goods reconciliation"

        else:  # ADJUSTMENT
            amount = round(random.uniform(500.0, 20000.0), 2)
            payment_method = "SYSTEM"
            ref_no = f"ADJ-{random.randint(100000, 999999)}"
            description = "Quarterly audit ledger reconciliation balance adjustment"

        # Baseline velocity for normal transactions (1 to 4 txns in 24h)
        rolling_24h_count = random.randint(1, 4)
        rolling_24h_amount = round(amount + random.uniform(0, 50000), 2)

        return {
            "transaction_id": str(uuid.uuid4()),
            "school_id": school["school_id"],
            "school_name": school["name"],
            "county": school["county"],
            "student_count": student_count,
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "supplier_category": supplier_cat,
            "type": txn_type,
            "amount": amount,
            "payment_method": payment_method,
            "reference_no": ref_no,
            "description": description,
            "transacted_at": timestamp,
            "rolling_24h_count": rolling_24h_count,
            "rolling_24h_amount": rolling_24h_amount,
            "school_avg_amount": school["avg_transaction_amount"],
            "approved_by_name": fake.name(),
            "status": "COMPLETED",
            "is_fraud": 0,
            "fraud_pattern": "NORMAL"
        }

    def generate_fraud_transaction(self) -> Dict[str, Any]:
        """
        Generates an anomalous / fraudulent transaction modeling specific
        threat typologies that Isolation Forest detects via tabular deviation.
        """
        school = random.choice(self.schools)
        student_count = school["student_count"]
        patterns = [
            "EXTREME_AMOUNT_OUTLIER",
            "OFF_HOURS_DRAIN",
            "VELOCITY_BURST_SMURFING",
            "DISPROPORTIONATE_PER_STUDENT",
            "SUSPICIOUS_PAYMENT_METHOD",
            "ROUND_NUMBER_DRAIN"
        ]
        pattern = random.choice(patterns)
        supplier = random.choice(self.suppliers)
        
        # Default baseline values
        timestamp = self._random_timestamp(is_off_hours=False)
        txn_type = "SUPPLIER_PAYMENT"
        payment_method = "BANK_TRANSFER"
        ref_no = f"BTR-{random.randint(100000, 999999)}"
        description = "Supplier remittance"
        rolling_24h_count = random.randint(1, 3)

        if pattern == "EXTREME_AMOUNT_OUTLIER":
            # Vastly inflated invoice amount (10x-30x normal)
            # e.g., 2.5M to 7.5M KES for standard food delivery
            amount = round(random.uniform(2200000.0, 7800000.0), 2)
            payment_method = random.choice(["BANK_TRANSFER", "CHEQUE"])
            description = "Special catering supplies & dry ration bulk consignment - Urgent"
            rolling_24h_amount = round(amount + random.uniform(10000, 50000), 2)

        elif pattern == "OFF_HOURS_DRAIN":
            # Transacted at 2:00 AM - 4:00 AM on Sunday / weekend off-hours
            timestamp = self._random_timestamp(is_off_hours=True, force_weekend=True)
            # High amount transferred during dormant operational hours
            amount = round(random.uniform(450000.0, 1850000.0), 2)
            payment_method = random.choice(["MPESA", "BANK_TRANSFER"])
            ref_no = generate_mpesa_reference() if payment_method == "MPESA" else f"BTR-{random.randint(100000, 999999)}"
            description = "Off-cycle urgent food replenishment release"
            rolling_24h_amount = amount

        elif pattern == "VELOCITY_BURST_SMURFING":
            # Rapid series of repeated transactions just below approval threshold
            # E.g. KES 95,000 repeated 8-15 times within 24h
            amount = round(random.uniform(88000.0, 99500.0), 2)
            rolling_24h_count = random.randint(8, 22)  # Abnormal velocity spike
            rolling_24h_amount = round(amount * rolling_24h_count, 2)
            payment_method = "MPESA"
            ref_no = generate_mpesa_reference()
            description = f"Direct local vendor purchase tranche #{random.randint(1, 9)}"

        elif pattern == "DISPROPORTIONATE_PER_STUDENT":
            # Very small school (< 180 students) billed massive amount
            small_school = min(self.schools, key=lambda s: s["student_count"])
            school = small_school
            student_count = small_school["student_count"]
            # Amount equating to KES 12,000+ per student for a single delivery
            amount = round(student_count * random.uniform(9500.0, 22000.0), 2)
            payment_method = "BANK_TRANSFER"
            description = f"Consumables invoice claim for {student_count} registered students"
            rolling_24h_amount = amount

        elif pattern == "SUSPICIOUS_PAYMENT_METHOD":
            # Government subsidy or large supplier payment released in physical CASH or personal MPESA
            txn_type = "SUBSIDY_DISBURSEMENT"
            amount = round(random.uniform(600000.0, 2500000.0), 2)
            payment_method = random.choice(["CASH", "MPESA"])  # Highly irregular for subsidies!
            ref_no = generate_mpesa_reference() if payment_method == "MPESA" else f"CSH-VOUCHER-{random.randint(1000, 9999)}"
            description = "Manual subsidy withdrawal and discretionary cash fund disbursement"
            rolling_24h_amount = amount

        else:  # ROUND_NUMBER_DRAIN
            # Repeated exact round numbers, common in embezzlement
            amount = float(random.choice([500000, 750000, 1000000, 1500000, 2000000]))
            payment_method = "BANK_TRANSFER"
            rolling_24h_count = random.randint(3, 7)
            rolling_24h_amount = amount * rolling_24h_count
            description = "General logistics and catering support lump-sum payment"

        return {
            "transaction_id": str(uuid.uuid4()),
            "school_id": school["school_id"],
            "school_name": school["name"],
            "county": school["county"],
            "student_count": student_count,
            "supplier_id": supplier["supplier_id"],
            "supplier_name": supplier["name"],
            "supplier_category": supplier["category"],
            "type": txn_type,
            "amount": amount,
            "payment_method": payment_method,
            "reference_no": ref_no,
            "description": description,
            "transacted_at": timestamp,
            "rolling_24h_count": rolling_24h_count,
            "rolling_24h_amount": rolling_24h_amount,
            "school_avg_amount": school["avg_transaction_amount"],
            "approved_by_name": fake.name(),
            "status": "FLAGGED",
            "is_fraud": 1,
            "fraud_pattern": pattern
        }

    def generate_dataset(self, n_samples: int = 10000, fraud_ratio: float = 0.05) -> pd.DataFrame:
        """
        Generates full synthetic dataset with controllable fraud contamination ratio.
        """
        n_fraud = int(n_samples * fraud_ratio)
        n_normal = n_samples - n_fraud

        print(f"[GEN] Generating {n_samples:,} records ({n_normal:,} Normal, {n_fraud:,} Fraud / {fraud_ratio:.1%})...")

        records = []
        for _ in range(n_normal):
            records.append(self.generate_normal_transaction())

        for _ in range(n_fraud):
            records.append(self.generate_fraud_transaction())

        # Shuffle records to avoid contiguous blocks
        random.shuffle(records)
        df = pd.DataFrame(records)

        # Compute engineered features
        df["hour_of_day"] = df["transacted_at"].apply(lambda dt: dt.hour)
        df["day_of_week"] = df["transacted_at"].apply(lambda dt: dt.weekday())
        df["is_weekend"] = df["day_of_week"].apply(lambda d: 1 if d >= 5 else 0)
        df["is_off_hours"] = df["hour_of_day"].apply(lambda h: 1 if (h < 6 or h >= 22) else 0)
        
        # Financial ratio features
        df["log_amount"] = np.log1p(df["amount"])
        df["amount_per_student"] = df["amount"] / df["student_count"]
        df["log_amount_per_student"] = np.log1p(df["amount_per_student"])
        df["amount_to_school_avg_ratio"] = df["amount"] / (df["school_avg_amount"] + 1.0)
        df["log_rolling_24h_amount"] = np.log1p(df["rolling_24h_amount"])

        # Sort chronologically
        df = df.sort_values(by="transacted_at").reset_index(drop=True)
        return df


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic transaction data for Fraud Detection Isolation Forest.")
    parser.add_argument("--samples", type=int, default=12000, help="Total number of transaction records to generate")
    parser.add_argument("--fraud-ratio", type=float, default=0.06, help="Ratio of anomalous/fraud records (0.01 to 0.20)")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save generated CSV files")
    args = parser.parse_args()

    # Determine default path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = args.output_dir or script_dir
    os.makedirs(output_dir, exist_ok=True)

    generator = SyntheticDataGenerator()
    df = generator.generate_dataset(n_samples=args.samples, fraud_ratio=args.fraud_ratio)

    # 80/20 Train/Test split chronologically or randomly
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    full_csv = os.path.join(output_dir, "synthetic_transactions_full.csv")
    train_csv = os.path.join(output_dir, "synthetic_transactions_train.csv")
    test_csv = os.path.join(output_dir, "synthetic_transactions_test.csv")

    df.to_csv(full_csv, index=False)
    train_df.to_csv(train_csv, index=False)
    test_df.to_csv(test_csv, index=False)

    print("\n[SUCCESS] Synthetic data generation complete!")
    print(f"Total Records: {len(df):,}")
    print(f"Normal: {(df['is_fraud'] == 0).sum():,} ({(df['is_fraud'] == 0).mean():.1%})")
    print(f"Fraud: {(df['is_fraud'] == 1).sum():,} ({(df['is_fraud'] == 1).mean():.1%})")
    print("\nFraud Breakdown:")
    print(df[df["is_fraud"] == 1]["fraud_pattern"].value_counts())
    print("\nOutput Files:")
    print(f" - Full:  {full_csv}")
    print(f" - Train: {train_csv} ({len(train_df):,} rows)")
    print(f" - Test:  {test_csv} ({len(test_df):,} rows)")


if __name__ == "__main__":
    main()
