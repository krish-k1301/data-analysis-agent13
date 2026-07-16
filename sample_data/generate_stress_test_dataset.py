"""
Generates a synthetic accounts-payable transaction dataset sized to trigger
all 15 audit rules in backend/app/services/audit_rules/ under their DEFAULT
config thresholds (materiality=50000, dormant=180d, new_vendor_window=30d,
new_vendor_high_value=10000, vendor_concentration=40%, benford_p=0.05,
business_hours=07:00-19:00, backdated_threshold=30d, duplicate_payment_window=7d,
round_dollar_min=1000, split_transaction_min_rows=2).

Column names are chosen to auto-map onto the app's canonical schema roles
(backend/app/services/schema_service.py ROLE_KEYWORDS): vendor, amount,
date, invoice_no, entry_date, timestamp.
"""
import random
import numpy as np
import pandas as pd

RNG_SEED = 42
random.seed(RNG_SEED)
np.random.seed(RNG_SEED)

START_DATE = pd.Timestamp("2023-01-01")
END_DATE = pd.Timestamp("2024-12-31")
TOTAL_DAYS = (END_DATE - START_DATE).days

N_BASE = 6300

VENDORS = [
    "Acme Industrial Supply", "Beacon Freight Co", "Cedarline Manufacturing", "Delta Office Products",
    "Evergreen Facilities Mgmt", "Fairpoint Consulting", "Granite Hardware Group", "Harbor Logistics",
    "Ironclad Security Services", "Junction Tech Solutions", "Keystone Packaging", "Lakeside Catering",
    "Meridian Marketing Partners", "Northgate Distributors", "Oakwood Legal Services", "Pinnacle IT Systems",
    "Quarry Stone Supply", "Riverside Cleaning Co", "Summit Engineering", "Trailhead Staffing",
    "Union Fleet Maintenance", "Vantage Print & Design", "Westbrook Utilities", "Xenon Chemical Supply",
    "Yellowbrick Construction", "Zenith Insurance Brokers", "Ashcroft Telecom", "Briarwood Landscaping",
    "Crestline Data Services", "Dunmore Wholesale", "Elmwood Repairs", "Fenwick Consulting Group",
    "Glenmark Equipment Rental", "Hollowfield Transport", "Ivywood Office Interiors", "Jasperton Analytics",
    "Kingsley Waste Management", "Larkspur HR Solutions", "Millbrook Software", "Nightingale Medical Supply",
]

PRODUCTS = [
    "Office Supplies", "IT Equipment", "Facility Maintenance", "Consulting Services", "Freight & Shipping",
    "Raw Materials", "Marketing Services", "Staffing Services", "Cleaning Services", "Insurance Premium",
]
REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
PAYMENT_METHODS = ["ACH", "Wire", "Check", "Card"]

HOLIDAYS_MMDD = ["01-01", "07-04", "12-25", "11-11", "06-19"]


def random_date():
    return START_DATE + pd.Timedelta(days=random.randint(0, TOTAL_DAYS))


def random_business_time():
    hour = random.randint(7, 18)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def random_afterhours_time():
    hour = random.choice(list(range(0, 7)) + list(range(19, 24)))
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def natural_amount():
    # log-uniform in [20, 15000] -> approximately Benford-consistent leading digits
    return round(10 ** random.uniform(1.3, 4.2), 2)


rows = []

# ---------------------------------------------------------------------------
# 1. Base population (majority of rows) — sequential invoice numbers with a
#    deliberate ~10% gap for SEQUENTIAL_GAP, natural log-uniform amounts for
#    Benford baseline, weekday-biased-but-not-exclusive dates.
# ---------------------------------------------------------------------------
invoice_pool = list(range(100001, 100001 + int(N_BASE * 1.12)))
random.shuffle(invoice_pool)
n_drop = int(len(invoice_pool) * 0.10)
invoice_pool = invoice_pool[n_drop:]
invoice_pool = sorted(invoice_pool)[:N_BASE]

for i in range(N_BASE):
    d = random_date()
    entry_d = d + pd.Timedelta(days=random.randint(0, 3))
    rows.append({
        "invoice_no": f"INV-{invoice_pool[i]}",
        "vendor_name": random.choice(VENDORS),
        "amount": natural_amount(),
        "transaction_date": d.strftime("%Y-%m-%d"),
        "entry_date": entry_d.strftime("%Y-%m-%d"),
        "timestamp": f"{d.strftime('%Y-%m-%d')} {random_business_time()}",
        "product_category": random.choice(PRODUCTS),
        "region": random.choice(REGIONS),
        "payment_method": random.choice(PAYMENT_METHODS),
        "quantity": random.randint(1, 200),
    })

df = pd.DataFrame(rows)

# Running counter for all "special scenario" invoice numbers below, kept
# contiguous with the base range so SEQUENTIAL_GAP stays realistic (~10-15%)
# instead of sprawling across disjoint blocks.
extra_invoice_counter = [max(invoice_pool) + 500]


def next_invoice():
    extra_invoice_counter[0] += 1
    return extra_invoice_counter[0]

# ---------------------------------------------------------------------------
# 2. BENFORDS_LAW — force ~33% of amounts to lead with digit 4 (expected ~9.7%)
# ---------------------------------------------------------------------------
benford_idx = df.sample(n=2000, random_state=RNG_SEED).index
df.loc[benford_idx, "amount"] = [round(random.uniform(4000, 4999.99), 2) for _ in benford_idx]

# ---------------------------------------------------------------------------
# 3. AFTER_HOURS_ENTRY — ~200 rows outside 07:00-19:00
# ---------------------------------------------------------------------------
ah_idx = df.sample(n=200, random_state=1).index
for i in ah_idx:
    date_part = df.loc[i, "timestamp"].split(" ")[0]
    df.loc[i, "timestamp"] = f"{date_part} {random_afterhours_time()}"

# ---------------------------------------------------------------------------
# 4. BACKDATED_ENTRY — ~100 rows where entry_date is 31-90 days after transaction_date
# ---------------------------------------------------------------------------
bd_idx = df.sample(n=100, random_state=2).index
for i in bd_idx:
    d = pd.Timestamp(df.loc[i, "transaction_date"])
    new_entry = d + pd.Timedelta(days=random.randint(31, 90))
    df.loc[i, "entry_date"] = new_entry.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# 5. PUBLIC_HOLIDAY_POSTING — ~30 rows dated on a recognized holiday
# ---------------------------------------------------------------------------
ph_idx = df.sample(n=30, random_state=3).index
for i in ph_idx:
    year = random.choice([2023, 2024])
    mmdd = random.choice(HOLIDAYS_MMDD)
    new_date = pd.Timestamp(f"{year}-{mmdd}")
    df.loc[i, "transaction_date"] = new_date.strftime("%Y-%m-%d")
    df.loc[i, "entry_date"] = new_date.strftime("%Y-%m-%d")
    df.loc[i, "timestamp"] = f"{new_date.strftime('%Y-%m-%d')} {random_business_time()}"

# ---------------------------------------------------------------------------
# 6. ROUND_DOLLAR — ~150 rows with an exact round-dollar amount > 1000
# ---------------------------------------------------------------------------
rd_idx = df.sample(n=150, random_state=4).index
df.loc[rd_idx, "amount"] = [float(random.choice([2000, 3500, 5000, 7500, 10000, 12000, 15000, 20000])) for _ in rd_idx]

# ---------------------------------------------------------------------------
# 7. MISSING_REQUIRED_FIELD — ~80 rows missing one of vendor/amount/date/invoice_no
# ---------------------------------------------------------------------------
mf_idx = df.sample(n=80, random_state=5).index
mf_fields = ["vendor_name", "amount", "transaction_date", "invoice_no"]
for i in mf_idx:
    field = random.choice(mf_fields)
    df.loc[i, field] = np.nan

# ---------------------------------------------------------------------------
# 8. DUPLICATE_INVOICE — 15 exact duplicate postings (same invoice/vendor/amount/date)
# ---------------------------------------------------------------------------
dup_src = df[df["invoice_no"].notna() & df["vendor_name"].notna() & df["amount"].notna() & df["transaction_date"].notna()]
dup_rows = dup_src.sample(n=15, random_state=6).copy()
df = pd.concat([df, dup_rows], ignore_index=True)

# ---------------------------------------------------------------------------
# 9. DUPLICATE_PAYMENT — 15 pairs: same vendor+amount, different invoice_no, <=7 days apart
# ---------------------------------------------------------------------------
pay_src = df[df["vendor_name"].notna() & df["amount"].notna() & df["transaction_date"].notna()]
pay_rows = pay_src.sample(n=15, random_state=7).copy()
new_rows = []
for k, (_, r) in enumerate(pay_rows.iterrows()):
    d = pd.Timestamp(r["transaction_date"]) + pd.Timedelta(days=random.randint(1, 6))
    new_rows.append({
        "invoice_no": f"INV-{next_invoice()}",
        "vendor_name": r["vendor_name"],
        "amount": r["amount"],
        "transaction_date": d.strftime("%Y-%m-%d"),
        "entry_date": d.strftime("%Y-%m-%d"),
        "timestamp": f"{d.strftime('%Y-%m-%d')} {random_business_time()}",
        "product_category": random.choice(PRODUCTS),
        "region": random.choice(REGIONS),
        "payment_method": random.choice(PAYMENT_METHODS),
        "quantity": random.randint(1, 200),
    })
df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

# ---------------------------------------------------------------------------
# 10. DORMANT_VENDOR — 5 dedicated vendors: active early, silent >180d, reactivate
# ---------------------------------------------------------------------------
dormant_vendors = ["Aldergate Reclaimed Timber", "Brightfield Signage Co", "Coppervale Auditors",
                    "Driftwood Event Staffing", "Emberline Fire Safety"]
dormant_rows = []
for v in dormant_vendors:
    active_dates = [pd.Timestamp("2023-01-10") + pd.Timedelta(days=random.randint(0, 20)),
                    pd.Timestamp("2023-02-15") + pd.Timedelta(days=random.randint(0, 20))]
    reactivate_dates = [pd.Timestamp("2023-09-20") + pd.Timedelta(days=random.randint(0, 20)),
                         pd.Timestamp("2023-10-15") + pd.Timedelta(days=random.randint(0, 20))]
    for d in active_dates + reactivate_dates:
        dormant_rows.append({
            "invoice_no": f"INV-{next_invoice()}",
            "vendor_name": v,
            "amount": natural_amount(),
            "transaction_date": d.strftime("%Y-%m-%d"),
            "entry_date": d.strftime("%Y-%m-%d"),
            "timestamp": f"{d.strftime('%Y-%m-%d')} {random_business_time()}",
            "product_category": random.choice(PRODUCTS),
            "region": random.choice(REGIONS),
            "payment_method": random.choice(PAYMENT_METHODS),
            "quantity": random.randint(1, 200),
        })
df = pd.concat([df, pd.DataFrame(dormant_rows)], ignore_index=True)

# ---------------------------------------------------------------------------
# 11. NEW_VENDOR_HIGH_VALUE — 6 dedicated vendors, first seen then high-value <=30d later
# ---------------------------------------------------------------------------
new_vendors = ["Foxglove Rapid Builders", "Graywolf Import Export", "Halcyon Data Centers",
               "Ironbridge Capital Leasing", "Juniper Rare Materials", "Kestrel Aviation Parts"]
nv_rows = []
for v in new_vendors:
    first_seen = START_DATE + pd.Timedelta(days=random.randint(60, TOTAL_DAYS - 60))
    second = first_seen + pd.Timedelta(days=random.randint(5, 25))
    for d, amt in [(first_seen, natural_amount()), (second, round(random.uniform(15000, 60000), 2))]:
        nv_rows.append({
            "invoice_no": f"INV-{next_invoice()}",
            "vendor_name": v,
            "amount": amt,
            "transaction_date": d.strftime("%Y-%m-%d"),
            "entry_date": d.strftime("%Y-%m-%d"),
            "timestamp": f"{d.strftime('%Y-%m-%d')} {random_business_time()}",
            "product_category": random.choice(PRODUCTS),
            "region": random.choice(REGIONS),
            "payment_method": random.choice(PAYMENT_METHODS),
            "quantity": random.randint(1, 200),
        })
df = pd.concat([df, pd.DataFrame(nv_rows)], ignore_index=True)

# ---------------------------------------------------------------------------
# 12. SPLIT_TRANSACTION — 8 vendor+date groups of 3 rows summing to a round total > 50000
# ---------------------------------------------------------------------------
split_rows = []
for g in range(8):
    v = f"Split-Pattern Vendor {g + 1}"
    d = START_DATE + pd.Timedelta(days=random.randint(30, TOTAL_DAYS - 30))
    per_txn = 20000.0
    for _ in range(3):
        split_rows.append({
            "invoice_no": f"INV-{next_invoice()}",
            "vendor_name": v,
            "amount": per_txn,
            "transaction_date": d.strftime("%Y-%m-%d"),
            "entry_date": d.strftime("%Y-%m-%d"),
            "timestamp": f"{d.strftime('%Y-%m-%d')} {random_business_time()}",
            "product_category": random.choice(PRODUCTS),
            "region": random.choice(REGIONS),
            "payment_method": random.choice(PAYMENT_METHODS),
            "quantity": random.randint(1, 200),
        })
df = pd.concat([df, pd.DataFrame(split_rows)], ignore_index=True)

# ---------------------------------------------------------------------------
# 13. THRESHOLD_BREACH — 40 rows with abs(amount) > 50000
# ---------------------------------------------------------------------------
tb_rows = []
for _ in range(40):
    d = random_date()
    tb_rows.append({
        "invoice_no": f"INV-{next_invoice()}",
        "vendor_name": random.choice(VENDORS),
        "amount": round(random.uniform(55000, 180000), 2),
        "transaction_date": d.strftime("%Y-%m-%d"),
        "entry_date": d.strftime("%Y-%m-%d"),
        "timestamp": f"{d.strftime('%Y-%m-%d')} {random_business_time()}",
        "product_category": random.choice(PRODUCTS),
        "region": random.choice(REGIONS),
        "payment_method": random.choice(PAYMENT_METHODS),
        "quantity": random.randint(1, 200),
    })
df = pd.concat([df, pd.DataFrame(tb_rows)], ignore_index=True)

# ---------------------------------------------------------------------------
# 14. SINGLE_VENDOR_CONCENTRATION — mega vendor sized to exceed 40% of total spend
# ---------------------------------------------------------------------------
current_total = df["amount"].astype(float).abs().sum()
# want mega_sum / (current_total + mega_sum) > 0.40  =>  mega_sum > (0.40/0.60) * current_total
target_mega_sum = (0.40 / 0.60) * current_total * 1.15  # 15% margin over the exact breakeven
N_MEGA = 40
per_mega = round(target_mega_sum / N_MEGA, 2)
mega_rows = []
for _ in range(N_MEGA):
    d = random_date()
    mega_rows.append({
        "invoice_no": f"INV-{next_invoice()}",
        "vendor_name": "Titan Global Logistics",
        "amount": per_mega,
        "transaction_date": d.strftime("%Y-%m-%d"),
        "entry_date": d.strftime("%Y-%m-%d"),
        "timestamp": f"{d.strftime('%Y-%m-%d')} {random_business_time()}",
        "product_category": "Freight & Shipping",
        "region": random.choice(REGIONS),
        "payment_method": random.choice(PAYMENT_METHODS),
        "quantity": random.randint(1, 200),
    })
df = pd.concat([df, pd.DataFrame(mega_rows)], ignore_index=True)

# ---------------------------------------------------------------------------
# Shuffle row order so anomalies aren't visibly clustered, reset a clean RangeIndex
# ---------------------------------------------------------------------------
df = df.sample(frac=1, random_state=RNG_SEED).reset_index(drop=True)

out_path = "stress_test_transactions.csv"
df.to_csv(out_path, index=False)

# ---------------------------------------------------------------------------
# Verification summary
# ---------------------------------------------------------------------------
print(f"Total rows: {len(df)}")
print(f"Total columns: {len(df.columns)}")
print(f"Columns: {list(df.columns)}")

amt = pd.to_numeric(df["amount"], errors="coerce").dropna().abs()
total_spend = amt.sum()
mega_spend = pd.to_numeric(
    df.loc[df["vendor_name"] == "Titan Global Logistics", "amount"], errors="coerce"
).abs().sum()
print(f"\nSINGLE_VENDOR_CONCENTRATION check: Titan Global Logistics = {mega_spend/total_spend*100:.1f}% of total spend (need > 40%)")

leading = amt[amt > 0].apply(lambda v: str(v).lstrip("0.").replace(".", "")[0])
print(f"\nBENFORDS_LAW check: leading digit distribution:\n{leading.value_counts(normalize=True).sort_index() * 100}")

print(f"\nMISSING_REQUIRED_FIELD check: null counts -> vendor={df['vendor_name'].isna().sum()}, "
      f"amount={df['amount'].isna().sum()}, date={df['transaction_date'].isna().sum()}, invoice={df['invoice_no'].isna().sum()}")

print(f"\nROUND_DOLLAR check: rows with integer amount > 1000: "
      f"{((pd.to_numeric(df['amount'], errors='coerce') % 1 == 0) & (pd.to_numeric(df['amount'], errors='coerce').abs() > 1000)).sum()}")

print(f"\nTHRESHOLD_BREACH check: rows with abs(amount) > 50000: {(amt > 50000).sum()}")

dts = pd.to_datetime(df["transaction_date"], errors="coerce")
print(f"\nWEEKEND_POSTING check: rows on Sat/Sun: {(dts.dt.dayofweek >= 5).sum()}")

mmdd = dts.dt.strftime("%m-%d")
print(f"PUBLIC_HOLIDAY_POSTING check: rows on a recognized holiday: {mmdd.isin(HOLIDAYS_MMDD).sum()}")

ts = pd.to_datetime(df["timestamp"], errors="coerce")
hours = ts.dt.hour
print(f"\nAFTER_HOURS_ENTRY check: rows outside 07:00-19:00: {((hours < 7) | (hours >= 19)).sum()}")

ed = pd.to_datetime(df["entry_date"], errors="coerce")
delta = (ed - dts).dt.days
print(f"BACKDATED_ENTRY check: rows with entry_date > 30 days after transaction_date: {(delta > 30).sum()}")

dup_check = df.dropna(subset=["invoice_no", "vendor_name", "amount", "transaction_date"])
dup_counts = dup_check.groupby(["invoice_no", "vendor_name", "amount", "transaction_date"]).size()
print(f"\nDUPLICATE_INVOICE check: exact-duplicate groups: {(dup_counts > 1).sum()}")

import re
nums = sorted({int(m.group()) for v in df["invoice_no"].dropna() if (m := re.search(r"\d+", str(v)))})
expected = nums[-1] - nums[0] + 1
gap_pct = (expected - len(nums)) / expected * 100
print(f"\nSEQUENTIAL_GAP check: {len(nums)} distinct invoice numbers, range {nums[0]}-{nums[-1]}, gap = {gap_pct:.1f}% (need > 5%)")

print(f"\nSaved to: {out_path}")
