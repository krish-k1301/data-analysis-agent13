from fastapi import APIRouter

from app.services.audit_rules.registry import get_rule_metadata

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("")
def list_rules():
    return get_rule_metadata()
