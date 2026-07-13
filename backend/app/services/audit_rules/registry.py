from app.services.audit_rules.after_hours_entry import AfterHoursEntryRule
from app.services.audit_rules.backdated_entry import BackdatedEntryRule
from app.services.audit_rules.base import AuditRule
from app.services.audit_rules.benfords_law import BenfordsLawRule
from app.services.audit_rules.dormant_vendor import DormantVendorRule
from app.services.audit_rules.duplicate_invoice import DuplicateInvoiceRule
from app.services.audit_rules.duplicate_payment import DuplicatePaymentRule
from app.services.audit_rules.missing_required_field import MissingRequiredFieldRule
from app.services.audit_rules.new_vendor_high_value import NewVendorHighValueRule
from app.services.audit_rules.public_holiday_posting import PublicHolidayPostingRule
from app.services.audit_rules.round_dollar import RoundDollarRule
from app.services.audit_rules.sequential_gap import SequentialGapRule
from app.services.audit_rules.single_vendor_concentration import SingleVendorConcentrationRule
from app.services.audit_rules.split_transaction import SplitTransactionRule
from app.services.audit_rules.threshold_breach import ThresholdBreachRule
from app.services.audit_rules.weekend_posting import WeekendPostingRule

RULE_CLASSES: list[type[AuditRule]] = [
    DuplicateInvoiceRule,
    DuplicatePaymentRule,
    SequentialGapRule,
    MissingRequiredFieldRule,
    WeekendPostingRule,
    PublicHolidayPostingRule,
    AfterHoursEntryRule,
    BackdatedEntryRule,
    RoundDollarRule,
    ThresholdBreachRule,
    SplitTransactionRule,
    BenfordsLawRule,
    DormantVendorRule,
    NewVendorHighValueRule,
    SingleVendorConcentrationRule,
]

REGISTRY: dict[str, AuditRule] = {cls.rule_id: cls() for cls in RULE_CLASSES}

ALL_RULE_IDS: list[str] = list(REGISTRY.keys())


def get_rule_metadata() -> list[dict]:
    return [
        {
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "severity": rule.severity,
            "category": rule.category,
            "required_columns": rule.required_columns,
        }
        for rule in REGISTRY.values()
    ]


def get_enabled_rules(enabled_rule_ids: list[str] | None) -> list[AuditRule]:
    if not enabled_rule_ids:
        return list(REGISTRY.values())
    return [REGISTRY[rid] for rid in enabled_rule_ids if rid in REGISTRY]
