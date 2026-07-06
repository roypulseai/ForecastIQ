from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import hashlib
import uuid
from pydantic import BaseModel, Field


class ConsentPurpose(str, Enum):
    ESSENTIAL = "essential"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    PROFILING = "profiling"
    THIRD_PARTY_SHARING = "third_party_sharing"
    IMPROVEMENTS = "improvements"


class ConsentCategory(str, Enum):
    ESSENTIAL = "essential"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    PROFILING = "profiling"
    THIRD_PARTY = "third_party"


class ConsentRecord(BaseModel):
    consent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    purposes: List[ConsentPurpose]
    legal_basis: str
    consent_given_at: datetime = Field(default_factory=datetime.utcnow)
    consent_updated_at: datetime = Field(default_factory=datetime.utcnow)
    consent_withdrawn_at: Optional[datetime] = None
    jurisdiction: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    proof: str = ""
    version: str = "1.0"

    def generate_proof(self) -> str:
        data = f"{self.user_id}:{','.join(self.purposes)}:{self.consent_given_at.isoformat()}:{self.jurisdiction}"
        return hashlib.sha256(data.encode()).hexdigest()


class ConsentRequest(BaseModel):
    user_id: str
    purposes: List[ConsentPurpose]
    jurisdiction: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ConsentResponse(BaseModel):
    consent_id: str
    status: str
    purposes: List[ConsentPurpose]
    consent_given_at: datetime
    withdrawable: bool


CONSENT_CATEGORIES_CONFIG = {
    ConsentCategory.ESSENTIAL: {
        "required": True,
        "withdrawable": False,
        "description": "Core platform functionality including data processing for forecasting",
    },
    ConsentCategory.ANALYTICS: {
        "required": False,
        "withdrawable": True,
        "description": "Usage analytics and platform improvements",
    },
    ConsentCategory.MARKETING: {
        "required": False,
        "withdrawable": True,
        "description": "Promotional communications and updates",
    },
    ConsentCategory.PROFILING: {
        "required": False,
        "withdrawable": True,
        "description": "Automated decision-making and profiling",
    },
    ConsentCategory.THIRD_PARTY: {
        "required": False,
        "withdrawable": True,
        "description": "Sharing data with third-party partners",
    },
}


class ConsentManager:
    def __init__(self):
        self._consents: Dict[str, ConsentRecord] = {}

    def grant_consent(self, request: ConsentRequest) -> ConsentRecord:
        record = ConsentRecord(
            user_id=request.user_id,
            purposes=request.purposes,
            legal_basis="consent",
            jurisdiction=request.jurisdiction,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
        )
        record.proof = record.generate_proof()
        self._consents[record.consent_id] = record
        return record

    def withdraw_consent(self, consent_id: str) -> bool:
        if consent_id in self._consents:
            self._consents[consent_id].consent_withdrawn_at = datetime.utcnow()
            self._consents[consent_id].consent_updated_at = datetime.utcnow()
            return True
        return False

    def get_consent(self, consent_id: str) -> Optional[ConsentRecord]:
        return self._consents.get(consent_id)

    def get_user_consents(self, user_id: str) -> List[ConsentRecord]:
        return [
            c for c in self._consents.values()
            if c.user_id == user_id and c.consent_withdrawn_at is None
        ]

    def has_valid_consent(self, user_id: str, purpose: ConsentPurpose) -> bool:
        user_consents = self.get_user_consents(user_id)
        return any(purpose in c.purposes for c in user_consents)

    def check_all_consents_valid(
        self, user_id: str, required_purposes: List[ConsentPurpose]
    ) -> Dict[str, bool]:
        user_consents = self.get_user_consents(user_id)
        active_purposes = set()
        for c in user_consents:
            active_purposes.update(c.purposes)

        return {
            purpose.value: purpose in active_purposes
            for purpose in required_purposes
        }

    def get_consent_summary(self, user_id: str) -> Dict[str, Any]:
        consents = self.get_user_consents(user_id)
        return {
            "user_id": user_id,
            "active_consents": len(consents),
            "purposes": list(set(p for c in consents for p in c.purposes)),
            "has_essential": ConsentPurpose.ESSENTIAL in set(
                p for c in consents for p in c.purposes
            ),
        }
