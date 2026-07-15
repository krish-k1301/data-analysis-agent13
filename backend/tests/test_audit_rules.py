import pandas as pd
import pytest

from app.services.audit_rules.after_hours_entry import AfterHoursEntryRule
from app.services.audit_rules.backdated_entry import BackdatedEntryRule
from app.services.audit_rules.benfords_law import BenfordsLawRule
from app.services.audit_rules.dormant_vendor import DormantVendorRule
from app.services.audit_rules.duplicate_invoice import DuplicateInvoiceRule
from app.services.audit_rules.duplicate_payment import DuplicatePaymentRule
from app.services.audit_rules.missing_required_field import MissingRequiredFieldRule
from app.services.audit_rules.new_vendor_high_value import NewVendorHighValueRule
from app.services.audit_rules.public_holiday_posting import PublicHolidayPostingRule
from app.services.audit_rules.registry import REGISTRY
from app.services.audit_rules.round_dollar import RoundDollarRule
from app.services.audit_rules.sequential_gap import SequentialGapRule
from app.services.audit_rules.single_vendor_concentration import SingleVendorConcentrationRule
from app.services.audit_rules.split_transaction import SplitTransactionRule
from app.services.audit_rules.threshold_breach import ThresholdBreachRule
from app.services.audit_rules.weekend_posting import WeekendPostingRule


# ---------------------------------------------------------------------------
# Generic cross-rule contracts: every rule must degrade gracefully.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule", REGISTRY.values(), ids=lambda r: r.rule_id)
def test_no_findings_on_clean_data(rule, clean_amount_df, rule_config):
    findings = rule.evaluate(clean_amount_df, rule_config)
    assert findings == []


@pytest.mark.parametrize("rule", REGISTRY.values(), ids=lambda r: r.rule_id)
def test_missing_columns_returns_empty_not_raises(rule, rule_config):
    empty_df = pd.DataFrame({"unrelated_col": [1, 2, 3]})
    findings = rule.evaluate(empty_df, rule_config)
    assert findings == []


@pytest.mark.parametrize("rule", REGISTRY.values(), ids=lambda r: r.rule_id)
def test_empty_dataframe_returns_empty_not_raises(rule, rule_config):
    findings = rule.evaluate(pd.DataFrame(), rule_config)
    assert findings == []


def test_registry_has_all_15_rules():
    assert len(REGISTRY) == 15
    assert len({r.rule_id for r in REGISTRY.values()}) == 15  # unique IDs


# ---------------------------------------------------------------------------
# Category 1 — Duplicate and Completeness
# ---------------------------------------------------------------------------


def test_duplicate_invoice_triggers(rule_config):
    df = pd.DataFrame(
        {
            "invoice_no": ["INV-1", "INV-1", "INV-2"],
            "vendor": ["Acme", "Acme", "Acme"],
            "amount": [500.0, 500.0, 700.0],
            "date": pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03"]),
        }
    )
    findings = DuplicateInvoiceRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "DUPLICATE_INVOICE"
    assert len(findings[0]["flagged_rows"]) == 2
    assert findings[0]["supporting_metrics"]["duplicate_count"] == 2


def test_duplicate_payment_triggers_for_different_invoice_same_week(rule_config):
    df = pd.DataFrame(
        {
            "invoice_no": ["INV-1", "INV-2"],
            "vendor": ["Acme", "Acme"],
            "amount": [500.0, 500.0],
            "date": pd.to_datetime(["2024-01-02", "2024-01-05"]),
        }
    )
    findings = DuplicatePaymentRule().evaluate(df, rule_config)
    assert len(findings) == 1


def test_duplicate_payment_ignores_same_invoice(rule_config):
    # Same invoice_no across both rows -> DUPLICATE_INVOICE's job, not this rule's.
    df = pd.DataFrame(
        {
            "invoice_no": ["INV-1", "INV-1"],
            "vendor": ["Acme", "Acme"],
            "amount": [500.0, 500.0],
            "date": pd.to_datetime(["2024-01-02", "2024-01-05"]),
        }
    )
    findings = DuplicatePaymentRule().evaluate(df, rule_config)
    assert findings == []


def test_sequential_gap_triggers_above_5pct(rule_config):
    numbers = list(range(1000, 1020))  # 20 contiguous
    numbers = [n for n in numbers if n < 1010 or n >= 1013]  # drop 3/20 = 15% gap
    df = pd.DataFrame({"invoice_no": [f"INV-{n}" for n in numbers]})
    findings = SequentialGapRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["supporting_metrics"]["gap_pct"] > 5


def test_sequential_gap_handles_non_numeric_invoice_numbers_without_crashing(rule_config):
    # Regression test: Series.apply() previously upcast int/None mixes to
    # float64, turning missing values into NaN, which passed an
    # `is not None` filter and crashed range() with a float bound.
    df = pd.DataFrame({"invoice_no": [f"INV-{n}" for n in range(1000, 1015)] + [None, "", "NOT-A-NUMBER-XYZ"]})
    findings = SequentialGapRule().evaluate(df, rule_config)
    assert isinstance(findings, list)  # must not raise


def test_missing_required_field_triggers(rule_config):
    df = pd.DataFrame(
        {
            "invoice_no": ["INV-1", None],
            "vendor": ["Acme", "Beta"],
            "amount": [500.0, 700.0],
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        }
    )
    findings = MissingRequiredFieldRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["supporting_metrics"]["affected_row_count"] == 1


# ---------------------------------------------------------------------------
# Category 2 — Timing and Calendar
# ---------------------------------------------------------------------------


def test_weekend_posting_triggers(rule_config):
    df = pd.DataFrame({"date": pd.to_datetime(["2024-01-06", "2024-01-07"])})  # Sat, Sun
    findings = WeekendPostingRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["supporting_metrics"]["weekend_entry_count"] == 2


def test_public_holiday_posting_triggers(rule_config):
    df = pd.DataFrame({"date": pd.to_datetime(["2024-12-25", "2024-06-18"])})  # Xmas, non-holiday
    findings = PublicHolidayPostingRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["supporting_metrics"]["holiday_entry_count"] == 1


def test_after_hours_entry_triggers(rule_config):
    df = pd.DataFrame(
        {"timestamp": pd.to_datetime(["2024-01-02 03:00:00", "2024-01-02 12:00:00"])}
    )
    findings = AfterHoursEntryRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["supporting_metrics"]["after_hours_count"] == 1


def test_backdated_entry_triggers(rule_config):
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
            "entry_date": pd.to_datetime(["2024-01-05", "2024-03-15"]),  # +4d ok, +74d backdated
        }
    )
    findings = BackdatedEntryRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["flagged_rows"][0]["days_backdated"] > 30


# ---------------------------------------------------------------------------
# Category 3 — Amount Patterns
# ---------------------------------------------------------------------------


def test_round_dollar_triggers_above_threshold_only(rule_config):
    df = pd.DataFrame({"amount": [5000.00, 999.00, 1234.56]})  # only first qualifies
    findings = RoundDollarRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["supporting_metrics"]["round_dollar_count"] == 1


def test_threshold_breach_triggers_and_falls_back_to_config_without_statistics(rule_config):
    df = pd.DataFrame({"amount": [75000.0, 1000.0]})
    findings = ThresholdBreachRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["supporting_metrics"]["threshold"] == rule_config["materiality_threshold"]


def test_split_transaction_triggers_on_round_grouped_total(rule_config):
    df = pd.DataFrame(
        {
            "vendor": ["Acme", "Acme", "Acme"],
            "amount": [20000.0, 20000.0, 20000.0],
            "date": pd.to_datetime(["2024-01-02"] * 3),
        }
    )
    findings = SplitTransactionRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["supporting_metrics"]["total_amount"] == 60000.0


def test_benfords_law_flags_uniform_distribution(rule_config):
    # Linear-uniform amounts (not log-uniform) deliberately violate Benford's
    # Law; needs >=100 samples for the chi-squared test to run at all.
    import random

    rng = random.Random(42)
    amounts = [rng.uniform(100, 999) for _ in range(300)]  # first digit ~uniform 1-9
    df = pd.DataFrame({"amount": amounts})
    findings = BenfordsLawRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["supporting_metrics"]["p_value"] < rule_config["benford_p_value"]


def test_benfords_law_skips_small_corpus(rule_config):
    df = pd.DataFrame({"amount": [123.0, 456.0, 789.0]})  # < 100 samples
    findings = BenfordsLawRule().evaluate(df, rule_config)
    assert findings == []


# ---------------------------------------------------------------------------
# Category 4 — Vendor Behaviour
# ---------------------------------------------------------------------------


def test_dormant_vendor_triggers_after_long_gap(rule_config):
    df = pd.DataFrame(
        {
            "vendor": ["Acme", "Acme"],
            "date": pd.to_datetime(["2023-01-01", "2023-09-01"]),  # 243 days apart
        }
    )
    findings = DormantVendorRule().evaluate(df, rule_config)
    assert len(findings) == 1


def test_new_vendor_high_value_triggers_on_first_transaction(rule_config):
    df = pd.DataFrame(
        {
            "vendor": ["NewCo"],
            "date": pd.to_datetime(["2024-01-01"]),
            "amount": [15000.0],
        }
    )
    findings = NewVendorHighValueRule().evaluate(df, rule_config)
    assert len(findings) == 1


def test_single_vendor_concentration_triggers_above_threshold(rule_config):
    df = pd.DataFrame(
        {
            "vendor": ["Dominant"] * 3 + ["Small"] * 3,
            "amount": [10000.0] * 3 + [500.0] * 3,
        }
    )
    findings = SingleVendorConcentrationRule().evaluate(df, rule_config)
    assert len(findings) == 1
    assert findings[0]["supporting_metrics"]["vendor"] == "Dominant"
    assert findings[0]["supporting_metrics"]["concentration_pct"] > 40
