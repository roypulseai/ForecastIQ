from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Jurisdiction(str, Enum):
    USA = "usa"
    EU = "eu"
    SWITZERLAND = "ch"
    INDIA = "in"


class JurisdictionConfig(BaseModel):
    jurisdiction: Jurisdiction
    display_name: str
    primary_law: str
    regulator: str

    requires_consent: bool = True
    consent_type: str = "explicit"

    requires_dpo: bool = False
    requires_dpia: bool = False

    data_retention_days: int = 365
    breach_notification_hours: int = 72

    cross_border_transfer_allowed: bool = True
    cross_border_transfer_mechanisms: List[str] = []

    data_subject_rights: List[str] = []
    automated_decisions_allowed: bool = False

    minor_age: int = 16

    data_localization_required: bool = False
    localization_countries: List[str] = []

    sanctions: Dict[str, Any] = {}


JURISDICTION_CONFIGS: Dict[Jurisdiction, JurisdictionConfig] = {
    Jurisdiction.USA: JurisdictionConfig(
        jurisdiction=Jurisdiction.USA,
        display_name="United States",
        primary_law="Sector-specific (CCPA, HIPAA, GLBA)",
        regulator="FTC, State Attorneys General",
        requires_consent=True,
        consent_type="opt_out",
        requires_dpo=False,
        requires_dpia=False,
        data_retention_days=2555,
        breach_notification_hours=72,
        cross_border_transfer_allowed=True,
        cross_border_transfer_mechanisms=["Standard Contractual Clauses"],
        data_subject_rights=["access", "deletion", "correction", "opt_out"],
        automated_decisions_allowed=True,
        minor_age=13,
        sanctions={"civil": 7500, "unit": "USD per violation"},
    ),
    Jurisdiction.EU: JurisdictionConfig(
        jurisdiction=Jurisdiction.EU,
        display_name="European Union",
        primary_law="General Data Protection Regulation (GDPR)",
        regulator="European Data Protection Board, National DPAs",
        requires_consent=True,
        consent_type="explicit",
        requires_dpo=True,
        requires_dpia=True,
        data_retention_days=730,
        breach_notification_hours=72,
        cross_border_transfer_allowed=False,
        cross_border_transfer_mechanisms=["Adequacy Decision", "Standard Contractual Clauses", "BCRs"],
        data_subject_rights=[
            "access",
            "rectification",
            "erasure",
            "restriction",
            "portability",
            "object",
            "automated_decisions",
        ],
        automated_decisions_allowed=False,
        minor_age=16,
        data_localization_required=False,
        sanctions={"maximum": "€20 million or 4% global turnover"},
    ),
    Jurisdiction.SWITZERLAND: JurisdictionConfig(
        jurisdiction=Jurisdiction.SWITZERLAND,
        display_name="Switzerland",
        primary_law="Federal Act on Data Protection (FADP) 2023",
        regulator="Federal Data Protection and Information Commissioner (FDPIC)",
        requires_consent=True,
        consent_type="explicit",
        requires_dpo=True,
        requires_dpia=True,
        data_retention_days=3650,
        breach_notification_hours=72,
        cross_border_transfer_allowed=False,
        cross_border_transfer_mechanisms=["Adequacy", "SCCs", "BCRs"],
        data_subject_rights=["access", "correction", "erasure", "object", "portability"],
        automated_decisions_allowed=False,
        minor_age=16,
        data_localization_required=False,
        sanctions={"maximum": "CHF 250,000 (FADP); higher under criminal provisions"},
    ),
    Jurisdiction.INDIA: JurisdictionConfig(
        jurisdiction=Jurisdiction.INDIA,
        display_name="India",
        primary_law="Digital Personal Data Protection Act 2023",
        regulator="Data Protection Board of India",
        requires_consent=True,
        consent_type="affirmative",
        requires_dpo=False,
        requires_dpia=True,
        data_retention_days=1825,
        breach_notification_hours=72,
        cross_border_transfer_allowed=True,
        cross_border_transfer_mechanisms=["Allowed with restrictions"],
        data_subject_rights=["access", "correction", "erasure", "grievance", "nomination"],
        automated_decisions_allowed=False,
        minor_age=18,
        data_localization_required=True,
        localization_countries=["in"],
        sanctions={"maximum": "₹250 crore (≈$30M)"},
    ),
}


def get_jurisdiction_config(jurisdiction: Jurisdiction) -> JurisdictionConfig:
    return JURISDICTION_CONFIGS[jurisdiction]


def get_applicable_jurisdictions(user_region: str) -> List[Jurisdiction]:
    region_mapping = {
        "US": Jurisdiction.USA,
        "CA": Jurisdiction.USA,
        "EU": Jurisdiction.EU,
        "DE": Jurisdiction.EU,
        "FR": Jurisdiction.EU,
        "GB": Jurisdiction.EU,
        "CH": Jurisdiction.SWITZERLAND,
        "IN": Jurisdiction.INDIA,
    }
    return [region_mapping.get(user_region.upper(), Jurisdiction.USA)]
