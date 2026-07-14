"""Generate adversarial sample datasets for the audit engine.

These are deliberately messy — not clean toy CSVs — so they exercise the
cleaning/schema-fitting/statistics/rules pipeline against real breaking
points: mixed date formats, currency formatting variants, null-token
variety, formula-injection payloads, near-duplicate-vs-exact-duplicate
collisions, column-name ambiguity, Benford's-law violation, extreme
outliers, unicode, and full-row exact duplicates.

Run: python generate_sample_data.py
Outputs: sample_payments.csv, sample_journal_entries.csv (this directory)
"""

import random
from datetime import datetime, timedelta

import pandas as pd

random.seed(1337)

NULL_TOKENS = ["", "NA", "N/A", "null", "None", "NaN", "-", "--"]
FORMULA_PAYLOADS = ["=SUM(A1:A10)", "+CMD|'/c calc'!A1", "-2+3+cmd", "@SUM(1+1)*cmd"]

VENDORS = [
    "Acme Global Holdings", "Northwind Traders", "Umbrella Logistics",
    "Contoso Manufacturing", "Fabrikam Supplies", "Initech Consulting",
    "Globex Industrial", "Wayne Enterprises", "Stark Materials Co.",
    "Wonka Distribution", "Hooli Cloud Services", "Soylent Foods Ltd.",
    "Cyberdyne Systems", "Massive Dynamic", "Oscorp Chemical",
    "Ünïcode Vendörs Ltd.", "北京贸易公司", "🚀 Rocket Supplies Inc.",
    "Pied Piper Compression", "Aperture Science", "Dunder Mifflin Paper",
    "Vandelay Industries", "Gekko & Co Capital", "Sterling Cooper Ads",
    "Prestige Worldwide", "Los Pollos Hermanos", "Bluth Company",
    "Tyrell Corporation", "Weyland-Yutani Corp", "Genco Pura Olive Oil",
]

DEPARTMENTS = ["Procurement", "Operations", "Finance", "IT", "Facilities", "Marketing", ""]

DATE_FORMATS = [
    lambda d: d.strftime("%Y-%m-%d"),
    lambda d: d.strftime("%m/%d/%Y"),
    lambda d: d.strftime("%d/%m/%Y"),
    lambda d: d.strftime("%B %d, %Y"),
    lambda d: d.strftime("%Y-%m-%dT%H:%M:%S"),
    lambda d: d.strftime("%d-%b-%Y"),
]


def messy_date(d: datetime) -> str:
    return random.choice(DATE_FORMATS)(d)


def messy_amount(value: float) -> str:
    """Render a numeric amount in one of several real-world messy formats."""
    style = random.random()
    if style < 0.15:
        return f"(${abs(value):,.2f})" if value < 0 else f"${value:,.2f}"
    if style < 0.3:
        return f"{value:,.2f}"
    if style < 0.4:
        return f" {value:.2f} "  # padding whitespace
    return f"{value:.2f}"


def maybe_null(value: str, p: float = 0.02) -> str:
    if random.random() < p:
        return random.choice(NULL_TOKENS)
    return value


def maybe_formula_injection(value: str, p: float = 0.01) -> str:
    if random.random() < p:
        return random.choice(FORMULA_PAYLOADS)
    return value


def pad_whitespace(value: str, p: float = 0.1) -> str:
    if random.random() < p:
        return f"  {value}  "
    return value


def uniform_amount(low: float = 100, high: float = 45000) -> float:
    """Linear-uniform (NOT log-uniform) amount generator. Deliberately
    violates Benford's Law across the corpus, unlike naturally-occurring
    log-uniform transaction data — this is the intended adversarial signal
    for the BENFORDS_LAW rule.
    """
    return round(random.uniform(low, high), 2)


def build_payments_dataset() -> pd.DataFrame:
    rows = []
    base_date = datetime(2023, 1, 1)
    # Pool sized well above the ~610 invoices actually consumed below (500
    # baseline + ~106 anomaly rows), so it also produces gap_pct well above
    # the 5% SEQUENTIAL_GAP threshold from natural sparse sampling alone,
    # on top of the deliberate carved-out block.
    invoice_seq = list(range(10000, 11500))  # 1500 numbers

    # --- carve a deliberate sequential gap block ---
    gap_start = 10600
    gap_end = 10700  # 100 missing numbers, plus natural sparseness below
    invoice_pool = [n for n in invoice_seq if not (gap_start <= n < gap_end)]
    random.shuffle(invoice_pool)

    used_invoices = set()

    def next_invoice() -> str:
        n = invoice_pool.pop()
        used_invoices.add(n)
        return f"INV-{n}"

    # --- baseline population (~500 rows spanning ~2 years, 30 vendors) ---
    for _ in range(500):
        vendor = random.choice(VENDORS)
        txn_date = base_date + timedelta(days=random.randint(0, 730))
        amount = uniform_amount()
        entry_date = txn_date + timedelta(days=random.randint(0, 5))
        ts = txn_date + timedelta(hours=random.randint(7, 18), minutes=random.randint(0, 59))

        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": pad_whitespace(maybe_formula_injection(vendor)),
                "Invoice Amount": messy_amount(amount),
                "Transaction Date": messy_date(txn_date),
                "Entry Date": messy_date(entry_date),
                "Posting Timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "Description": maybe_null(pad_whitespace(f"Purchase order for {vendor}"), p=0.05),
                "Department": maybe_null(random.choice(DEPARTMENTS), p=0.1),
            }
        )

    # --- MISSING_REQUIRED_FIELD: blank out one canonical field on 15 rows ---
    for _ in range(15):
        r = dict(random.choice(rows))
        field = random.choice(["Vendor Name", "Invoice Amount", "Transaction Date", "Invoice #"])
        r[field] = random.choice(NULL_TOKENS)
        if field == "Invoice #":
            r["Invoice #"] = ""  # don't consume a numbered invoice
        rows.append(r)

    # --- DUPLICATE_INVOICE: exact invoice/vendor/amount/date, differing
    #     Description so the pair survives cleaning's exact full-row dedup ---
    for i in range(5):
        vendor = random.choice(VENDORS)
        txn_date = base_date + timedelta(days=random.randint(0, 730))
        amount = uniform_amount()
        shared_inv = next_invoice()
        entry_date = txn_date + timedelta(days=1)
        for copy_idx in range(2):
            rows.append(
                {
                    "Invoice #": shared_inv,
                    "Vendor Name": vendor,
                    "Invoice Amount": messy_amount(amount),
                    "Transaction Date": messy_date(txn_date),
                    "Entry Date": messy_date(entry_date),
                    "Posting Timestamp": (txn_date + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
                    "Description": f"Duplicate test group {i} copy {copy_idx}",
                    "Department": "Procurement",
                }
            )

    # --- DUPLICATE_PAYMENT: same vendor+amount within 7 days, different invoice ---
    for _ in range(5):
        vendor = random.choice(VENDORS)
        amount = uniform_amount()
        d1 = base_date + timedelta(days=random.randint(0, 700))
        d2 = d1 + timedelta(days=random.randint(1, 6))
        for d in (d1, d2):
            rows.append(
                {
                    "Invoice #": next_invoice(),
                    "Vendor Name": vendor,
                    "Invoice Amount": messy_amount(amount),
                    "Transaction Date": messy_date(d),
                    "Entry Date": messy_date(d),
                    "Posting Timestamp": (d + timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S"),
                    "Description": "Possible duplicate payment",
                    "Department": "Finance",
                }
            )

    # --- WEEKEND_POSTING: force 15 rows onto a Saturday/Sunday ---
    for _ in range(15):
        d = base_date + timedelta(days=random.randint(0, 730))
        d -= timedelta(days=d.weekday() - 5) if d.weekday() < 5 else timedelta(0)  # push to Sat
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": random.choice(VENDORS),
                "Invoice Amount": messy_amount(uniform_amount()),
                "Transaction Date": messy_date(d),
                "Entry Date": messy_date(d),
                "Posting Timestamp": (d + timedelta(hours=11)).strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "Weekend posting test",
                "Department": "Operations",
            }
        )

    # --- PUBLIC_HOLIDAY_POSTING: 8 rows on fixed-date US holidays ---
    for holiday_mmdd in ["01-01", "07-04", "12-25", "11-11", "06-19"]:
        year = random.choice([2023, 2024])
        d = datetime.strptime(f"{year}-{holiday_mmdd}", "%Y-%m-%d")
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": random.choice(VENDORS),
                "Invoice Amount": messy_amount(uniform_amount()),
                "Transaction Date": messy_date(d),
                "Entry Date": messy_date(d),
                "Posting Timestamp": (d + timedelta(hours=13)).strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "Holiday posting test",
                "Department": "Operations",
            }
        )

    # --- AFTER_HOURS_ENTRY: 15 rows with timestamp outside 07:00-19:00 ---
    for _ in range(15):
        d = base_date + timedelta(days=random.randint(0, 730))
        hour = random.choice([0, 1, 2, 3, 4, 5, 6, 20, 21, 22, 23])
        ts = d.replace(hour=hour, minute=random.randint(0, 59))
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": random.choice(VENDORS),
                "Invoice Amount": messy_amount(uniform_amount()),
                "Transaction Date": messy_date(d),
                "Entry Date": messy_date(d),
                "Posting Timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "After-hours entry test",
                "Department": "IT",
            }
        )

    # --- BACKDATED_ENTRY: entry_date > 30 days after transaction date ---
    for _ in range(10):
        d = base_date + timedelta(days=random.randint(0, 650))
        entry = d + timedelta(days=random.randint(31, 90))
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": random.choice(VENDORS),
                "Invoice Amount": messy_amount(uniform_amount()),
                "Transaction Date": messy_date(d),
                "Entry Date": messy_date(entry),
                "Posting Timestamp": (entry + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "Backdated entry test",
                "Department": "Finance",
            }
        )

    # --- ROUND_DOLLAR: 20 rows, whole-dollar amounts above $1,000 ---
    for _ in range(20):
        d = base_date + timedelta(days=random.randint(0, 730))
        amount = float(random.choice(range(1500, 30000, 500)))
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": random.choice(VENDORS),
                "Invoice Amount": messy_amount(amount),
                "Transaction Date": messy_date(d),
                "Entry Date": messy_date(d),
                "Posting Timestamp": (d + timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "Round dollar test",
                "Department": "Procurement",
            }
        )

    # --- THRESHOLD_BREACH: 10 rows above default materiality ($50,000) ---
    for _ in range(10):
        d = base_date + timedelta(days=random.randint(0, 730))
        amount = round(random.uniform(55000, 250000), 2)
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": random.choice(VENDORS),
                "Invoice Amount": messy_amount(amount),
                "Transaction Date": messy_date(d),
                "Entry Date": messy_date(d),
                "Posting Timestamp": (d + timedelta(hours=15)).strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "Materiality breach test",
                "Department": "Finance",
            }
        )

    # --- SPLIT_TRANSACTION: 3 same-vendor same-day rows summing to a round
    #     total above the materiality threshold ---
    split_vendor = "Bluth Company"
    split_date = base_date + timedelta(days=400)
    for amount in (20000.00, 20000.00, 20000.00):  # sums to 60000.00
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": split_vendor,
                "Invoice Amount": messy_amount(amount),
                "Transaction Date": messy_date(split_date),
                "Entry Date": messy_date(split_date),
                "Posting Timestamp": (split_date + timedelta(hours=16)).strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "Split transaction test",
                "Department": "Procurement",
            }
        )

    # --- DORMANT_VENDOR: early transaction, then reactivate after >180 days ---
    dormant_vendor = "Tyrell Corporation"
    early = base_date + timedelta(days=20)
    reactivate = early + timedelta(days=220)
    for d in (early, reactivate):
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": dormant_vendor,
                "Invoice Amount": messy_amount(uniform_amount()),
                "Transaction Date": messy_date(d),
                "Entry Date": messy_date(d),
                "Posting Timestamp": (d + timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "Dormant vendor test",
                "Department": "Procurement",
            }
        )

    # --- NEW_VENDOR_HIGH_VALUE: brand-new vendors whose first transaction is high value ---
    for name in ["Aperture Science Test Labs", "Genco Pura Olive Oil (New)"]:
        d = base_date + timedelta(days=random.randint(400, 700))
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": name,
                "Invoice Amount": messy_amount(round(random.uniform(12000, 40000), 2)),
                "Transaction Date": messy_date(d),
                "Entry Date": messy_date(d),
                "Posting Timestamp": (d + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "New vendor high value test",
                "Department": "Procurement",
            }
        )

    # --- SINGLE_VENDOR_CONCENTRATION: dominate total spend. Sized against the
    #     rest of the corpus (~$16.6M) so this vendor alone clears 40% —
    #     needs > ~0.667x the total of everything else, not just "large". ---
    concentration_vendor = "Weyland-Yutani Corp"
    for _ in range(6):
        d = base_date + timedelta(days=random.randint(0, 730))
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": concentration_vendor,
                "Invoice Amount": messy_amount(round(random.uniform(1800000, 2400000), 2)),
                "Transaction Date": messy_date(d),
                "Entry Date": messy_date(d),
                "Posting Timestamp": (d + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "Vendor concentration test",
                "Department": "Procurement",
            }
        )

    # --- Extreme outliers for z-score / IQR statistics ---
    for amount in (0.01, 999999.99, -5000.00):
        d = base_date + timedelta(days=random.randint(0, 730))
        rows.append(
            {
                "Invoice #": next_invoice(),
                "Vendor Name": random.choice(VENDORS),
                "Invoice Amount": messy_amount(amount),
                "Transaction Date": messy_date(d),
                "Entry Date": messy_date(d),
                "Posting Timestamp": (d + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
                "Description": "Outlier stress test",
                "Department": "Finance",
            }
        )

    # --- row where all four canonical fields are null but an optional field
    #     survives, so the row isn't dropped as a blank CSV line ---
    rows.append(
        {
            "Invoice #": "",
            "Vendor Name": "",
            "Invoice Amount": "",
            "Transaction Date": "",
            "Entry Date": "",
            "Posting Timestamp": "",
            "Description": "Row with all canonical fields blank",
            "Department": "Operations",
        }
    )

    # --- exact full-row duplicates, to test cleaning's drop_duplicates ---
    exact_dupe_source = dict(rows[10])
    rows.append(dict(exact_dupe_source))
    rows.append(dict(exact_dupe_source))

    random.shuffle(rows)
    df = pd.DataFrame(rows)

    # Sprinkle stray null tokens / whitespace into Department post-hoc
    df["Department"] = df["Department"].apply(lambda v: maybe_null(v, p=0.05))
    return df


def build_journal_entries_dataset() -> pd.DataFrame:
    """A structurally different second dataset (journal entries): different
    column names/order, ISO-only dates but heavier timing-anomaly density,
    to test that schema inference generalizes across formats/layouts.
    """
    rows = []
    base_date = datetime(2024, 1, 1)
    journal_seq = list(range(500, 900))
    random.shuffle(journal_seq)

    def next_je() -> str:
        return f"JE{journal_seq.pop():04d}"

    for _ in range(280):
        vendor = random.choice(VENDORS)
        d = base_date + timedelta(days=random.randint(0, 365))
        amount = uniform_amount(50, 20000)
        rows.append(
            {
                "je_number": next_je(),
                "payee": maybe_null(pad_whitespace(vendor), p=0.03),
                "net_amount": messy_amount(amount),
                "posting_date": d.strftime("%Y-%m-%d"),
                "document_date": (d + timedelta(days=random.randint(0, 3))).strftime("%Y-%m-%d"),
                "memo": maybe_formula_injection(f"JE for {vendor}", p=0.02),
            }
        )

    # Weekend-heavy + backdated-heavy for this dataset flavor
    for _ in range(20):
        d = base_date + timedelta(days=random.randint(0, 365))
        d -= timedelta(days=d.weekday() - 5) if d.weekday() < 5 else timedelta(0)
        rows.append(
            {
                "je_number": next_je(),
                "payee": random.choice(VENDORS),
                "net_amount": messy_amount(uniform_amount(50, 20000)),
                "posting_date": d.strftime("%Y-%m-%d"),
                "document_date": d.strftime("%Y-%m-%d"),
                "memo": "Weekend JE",
            }
        )
    for _ in range(15):
        d = base_date + timedelta(days=random.randint(0, 330))
        doc = d + timedelta(days=random.randint(31, 60))
        rows.append(
            {
                "je_number": next_je(),
                "payee": random.choice(VENDORS),
                "net_amount": messy_amount(uniform_amount(50, 20000)),
                "posting_date": d.strftime("%Y-%m-%d"),
                "document_date": doc.strftime("%Y-%m-%d"),
                "memo": "Backdated JE",
            }
        )

    random.shuffle(rows)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    payments = build_payments_dataset()
    payments.to_csv("sample_payments.csv", index=False)
    print(f"Wrote sample_payments.csv: {len(payments)} rows, {len(payments.columns)} columns")

    journal = build_journal_entries_dataset()
    journal.to_csv("sample_journal_entries.csv", index=False)
    print(f"Wrote sample_journal_entries.csv: {len(journal)} rows, {len(journal.columns)} columns")
