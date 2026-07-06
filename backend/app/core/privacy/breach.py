from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid
from pydantic import BaseModel, Field


class BreachRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


BREACH_RISK_CONFIG = {
    BreachRiskLevel.LOW: {
        "notification_required": False,
        "authority_notification": False,
        "data_subject_notification": False,
        "examples": [
            "Encrypted data, encryption key not compromised",
            "Temporary technical issue, no data accessed",
        ],
    },
    BreachRiskLevel.MEDIUM: {
        "notification_required": True,
        "authority_notification": True,
        "data_subject_notification": False,
        "examples": [
            "Internal system breach, no data exfiltrated",
            "Unauthorized access, quickly contained",
        ],
    },
    BreachRiskLevel.HIGH: {
        "notification_required": True,
        "authority_notification": True,
        "data_subject_notification": True,
        "examples": [
            "Unencrypted PII exposed",
            "Financial data accessed",
            "Sensitive personal data compromised",
        ],
    },
    BreachRiskLevel.CRITICAL: {
        "notification_required": True,
        "authority_notification": True,
        "data_subject_notification": True,
        "data_subject_notification_deadline_hours": 24,
        "examples": [
            "Large-scale data breach",
            "Special category data exposed",
            "Active exploitation detected",
        ],
    },
}


class BreachNotification(BaseModel):
    breach_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    reported_at: Optional[datetime] = None
    description: str
    data_types_affected: List[str]
    records_affected: int
    individuals_affected: int
    risk_level: BreachRiskLevel
    causes: List[str] = []
    containment_actions: List[str] = []
    remediation_steps: List[str] = []
    authority_notified: bool = False
    authority_notification_date: Optional[datetime] = None
    data_subjects_notified: bool = False
    data_subject_notification_date: Optional[datetime] = None
    status: str = "investigating"
    jurisdiction: str
    internal_review: bool = True
    external_audit_required: bool = False


class BreachReport(BaseModel):
    breach_id: str
    report_date: datetime
    reported_to: str
    report_content: Dict[str, Any]
    response_actions: List[str]
    follow_up_required: bool = False


class BreachManager:
    def __init__(self):
        self._breaches: Dict[str, BreachNotification] = {}
        self._incident_contacts: Dict[str, List[str]] = {}

    def register_breach(
        self,
        description: str,
        data_types: List[str],
        records_affected: int,
        individuals_affected: int,
        risk_level: BreachRiskLevel,
        jurisdiction: str,
    ) -> BreachNotification:
        breach = BreachNotification(
            description=description,
            data_types_affected=data_types,
            records_affected=records_affected,
            individuals_affected=individuals_affected,
            risk_level=risk_level,
            jurisdiction=jurisdiction,
        )

        self._breaches[breach.breach_id] = breach
        return breach

    def assess_risk(
        self,
        data_types: List[str],
        is_encrypted: bool,
        encryption_compromised: bool,
        was_accessed: bool,
        was_exfiltrated: bool,
    ) -> BreachRiskLevel:
        pii_indicators = ["pii", "personal", "name", "email", "address", "phone"]
        special_indicators = ["health", "financial", "biometric", "genetic", "political"]
        financial_indicators = ["payment", "credit", "bank", "account"]

        affected_special = any(indicator in " ".join(data_types).lower() for indicator in special_indicators)
        affected_financial = any(indicator in " ".join(data_types).lower() for indicator in financial_indicators)
        affected_pii = any(indicator in " ".join(data_types).lower() for indicator in pii_indicators)

        if not was_accessed:
            return BreachRiskLevel.LOW

        if not is_encrypted or encryption_compromised:
            if affected_special or affected_financial:
                return BreachRiskLevel.CRITICAL
            if affected_pii:
                return BreachRiskLevel.HIGH

        if was_exfiltrated:
            return BreachRiskLevel.HIGH

        if was_accessed:
            return BreachRiskLevel.MEDIUM

        return BreachRiskLevel.LOW

    def notify_authority(
        self,
        breach_id: str,
        authority: str,
        report_content: Dict[str, Any],
    ) -> BreachReport:
        if breach_id not in self._breaches:
            raise ValueError(f"Breach not found: {breach_id}")

        breach = self._breaches[breach_id]
        breach.authority_notified = True
        breach.authority_notification_date = datetime.utcnow()

        report = BreachReport(
            breach_id=breach_id,
            report_date=breach.authority_notification_date,
            reported_to=authority,
            report_content=report_content,
            response_actions=breach.containment_actions,
        )

        return report

    def notify_data_subjects(
        self,
        breach_id: str,
        notification_content: Dict[str, Any],
    ) -> bool:
        if breach_id not in self._breaches:
            raise ValueError(f"Breach not found: {breach_id}")

        breach = self._breaches[breach_id]

        if breach.risk_level not in [BreachRiskLevel.HIGH, BreachRiskLevel.CRITICAL]:
            return False

        breach.data_subjects_notified = True
        breach.data_subject_notification_date = datetime.utcnow()
        return True

    def update_breach_status(
        self,
        breach_id: str,
        status: str,
        containment_actions: Optional[List[str]] = None,
        remediation_steps: Optional[List[str]] = None,
    ) -> bool:
        if breach_id not in self._breaches:
            return False

        breach = self._breaches[breach_id]
        breach.status = status

        if containment_actions:
            breach.containment_actions.extend(containment_actions)

        if remediation_steps:
            breach.remediation_steps.extend(remediation_steps)

        return True

    def get_breach(self, breach_id: str) -> Optional[BreachNotification]:
        return self._breaches.get(breach_id)

    def get_breaches_by_status(self, status: str) -> List[BreachNotification]:
        return [b for b in self._breaches.values() if b.status == status]

    def get_all_breaches(self) -> List[BreachNotification]:
        return list(self._breaches.values())

    def requires_notification(self, breach_id: str) -> bool:
        if breach_id not in self._breaches:
            return False

        breach = self._breaches[breach_id]
        config = BREACH_RISK_CONFIG[breach.risk_level]
        return config["notification_required"]

    def is_authority_notification_required(self, breach_id: str) -> bool:
        if breach_id not in self._breaches:
            return False

        breach = self._breaches[breach_id]
        config = BREACH_RISK_CONFIG[breach.risk_level]
        return config["authority_notification"]

    def is_data_subject_notification_required(self, breach_id: str) -> bool:
        if breach_id not in self._breaches:
            return False

        breach = self._breaches[breach_id]
        config = BREACH_RISK_CONFIG[breach.risk_level]
        return config["data_subject_notification"]

    def get_notification_deadline_hours(self, breach_id: str) -> int:
        if breach_id not in self._breaches:
            return 72

        breach = self._breaches[breach_id]
        config = BREACH_RISK_CONFIG[breach.risk_level]
        return config.get("data_subject_notification_deadline_hours", 72)

    def generate_breach_report(self, breach_id: str) -> Dict[str, Any]:
        if breach_id not in self._breaches:
            raise ValueError(f"Breach not found: {breach_id}")

        breach = self._breaches[breach_id]
        return {
            "breach_id": breach.breach_id,
            "detected_at": breach.detected_at.isoformat(),
            "description": breach.description,
            "data_types_affected": breach.data_types_affected,
            "records_affected": breach.records_affected,
            "individuals_affected": breach.individuals_affected,
            "risk_level": breach.risk_level.value,
            "risk_assessment": BREACH_RISK_CONFIG[breach.risk_level],
            "containment_actions": breach.containment_actions,
            "remediation_steps": breach.remediation_steps,
            "notification_status": {
                "authority_notified": breach.authority_notified,
                "authority_date": (
                    breach.authority_notification_date.isoformat()
                    if breach.authority_notification_date
                    else None
                ),
                "data_subjects_notified": breach.data_subjects_notified,
                "data_subject_date": (
                    breach.data_subject_notification_date.isoformat()
                    if breach.data_subject_notification_date
                    else None
                ),
            },
            "status": breach.status,
        }
