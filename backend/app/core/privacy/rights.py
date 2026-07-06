from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid
from pydantic import BaseModel, Field


class RightsType(str, Enum):
    ACCESS = "access"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    RESTRICTION = "restriction"
    PORTABILITY = "portability"
    OBJECT = "object"
    AUTOMATED_DECISIONS = "automated_decisions"
    GRIEVANCE = "grievance"
    NOMINATION = "nomination"


class RightsRequestStatus(str, Enum):
    PENDING = "pending"
    VERIFYING = "verifying"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DENIED = "denied"
    PARTIALLY_COMPLETED = "partially_completed"


RIGHTS_BY_JURISDICTION = {
    "usa": [
        RightsType.ACCESS,
        RightsType.RECTIFICATION,
        RightsType.ERASURE,
        RightsType.GRIEVANCE,
    ],
    "eu": [
        RightsType.ACCESS,
        RightsType.RECTIFICATION,
        RightsType.ERASURE,
        RightsType.RESTRICTION,
        RightsType.PORTABILITY,
        RightsType.OBJECT,
        RightsType.AUTOMATED_DECISIONS,
    ],
    "ch": [
        RightsType.ACCESS,
        RightsType.RECTIFICATION,
        RightsType.ERASURE,
        RightsType.OBJECT,
        RightsType.PORTABILITY,
    ],
    "in": [
        RightsType.ACCESS,
        RightsType.RECTIFICATION,
        RightsType.ERASURE,
        RightsType.GRIEVANCE,
        RightsType.NOMINATION,
    ],
}

RESPONSE_TIMEFRAME_DAYS = {
    "usa": 45,
    "eu": 30,
    "ch": 30,
    "in": 30,
}


class RightsRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    rights_requested: List[RightsType]
    jurisdiction: str
    status: RightsRequestStatus = RightsRequestStatus.PENDING
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    denial_reason: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    notes: str = ""


class RightsResponse(BaseModel):
    request_id: str
    status: RightsRequestStatus
    rights_addressed: List[RightsType]
    data_provided: Optional[Dict[str, Any]] = None
    completion_date: datetime
    next_steps: Optional[str] = None


class DataSubjectRightsManager:
    def __init__(self):
        self._requests: Dict[str, RightsRequest] = {}
        self._user_requests: Dict[str, List[str]] = {}

    def submit_request(
        self,
        user_id: str,
        rights_requested: List[RightsType],
        jurisdiction: str,
        ip_address: Optional[str] = None,
    ) -> RightsRequest:
        valid_rights = self._validate_rights(rights_requested, jurisdiction)

        if not valid_rights:
            raise ValueError(f"Invalid rights requested for jurisdiction: {jurisdiction}")

        timeframe_days = RESPONSE_TIMEFRAME_DAYS.get(jurisdiction, 30)
        request = RightsRequest(
            user_id=user_id,
            rights_requested=valid_rights,
            jurisdiction=jurisdiction,
            deadline=datetime.utcnow(),
            ip_address=ip_address,
        )

        self._requests[request.request_id] = request

        if user_id not in self._user_requests:
            self._user_requests[user_id] = []
        self._user_requests[user_id].append(request.request_id)

        return request

    def verify_request(self, request_id: str) -> bool:
        if request_id in self._requests:
            self._requests[request_id].status = RightsRequestStatus.VERIFYING
            self._requests[request_id].verified_at = datetime.utcnow()
            return True
        return False

    def process_request(
        self,
        request_id: str,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> RightsResponse:
        if request_id not in self._requests:
            raise ValueError(f"Request not found: {request_id}")

        request = self._requests[request_id]
        request.status = RightsRequestStatus.PROCESSING
        request.response_data = response_data

        return RightsResponse(
            request_id=request_id,
            status=RightsRequestStatus.PROCESSING,
            rights_addressed=request.rights_requested,
            completion_date=request.deadline or datetime.utcnow(),
        )

    def complete_request(
        self,
        request_id: str,
        data_provided: Optional[Dict[str, Any]] = None,
        denied_rights: Optional[List[RightsType]] = None,
        denial_reason: Optional[str] = None,
    ) -> RightsResponse:
        if request_id not in self._requests:
            raise ValueError(f"Request not found: {request_id}")

        request = self._requests[request_id]

        if denied_rights:
            request.status = RightsRequestStatus.PARTIALLY_COMPLETED
            request.denial_reason = denial_reason
        else:
            request.status = RightsRequestStatus.COMPLETED

        request.completed_at = datetime.utcnow()

        addressed_rights = [
            r for r in request.rights_requested
            if denied_rights is None or r not in denied_rights
        ]

        return RightsResponse(
            request_id=request_id,
            status=request.status,
            rights_addressed=addressed_rights,
            data_provided=data_provided,
            completion_date=request.completed_at,
        )

    def deny_request(self, request_id: str, reason: str) -> bool:
        if request_id in self._requests:
            self._requests[request_id].status = RightsRequestStatus.DENIED
            self._requests[request_id].denial_reason = reason
            self._requests[request_id].completed_at = datetime.utcnow()
            return True
        return False

    def get_request(self, request_id: str) -> Optional[RightsRequest]:
        return self._requests.get(request_id)

    def get_user_requests(self, user_id: str) -> List[RightsRequest]:
        request_ids = self._user_requests.get(user_id, [])
        return [self._requests[rid] for rid in request_ids if rid in self._requests]

    def get_pending_requests(self, jurisdiction: Optional[str] = None) -> List[RightsRequest]:
        pending = [
            r for r in self._requests.values()
            if r.status in [RightsRequestStatus.PENDING, RightsRequestStatus.VERIFYING]
        ]

        if jurisdiction:
            pending = [r for r in pending if r.jurisdiction == jurisdiction]

        return sorted(pending, key=lambda r: r.submitted_at)

    def is_request_overdue(self, request_id: str) -> bool:
        if request_id not in self._requests:
            return False

        request = self._requests[request_id]
        if request.completed_at or not request.deadline:
            return False

        return datetime.utcnow() > request.deadline

    def _validate_rights(self, rights: List[RightsType], jurisdiction: str) -> List[RightsType]:
        allowed_rights = RIGHTS_BY_JURISDICTION.get(jurisdiction.lower(), [])
        return [r for r in rights if r in allowed_rights]

    def get_available_rights(self, jurisdiction: str) -> List[RightsType]:
        return RIGHTS_BY_JURISDICTION.get(jurisdiction.lower(), [])

    def get_request_summary(self, user_id: str) -> Dict[str, Any]:
        requests = self.get_user_requests(user_id)
        return {
            "user_id": user_id,
            "total_requests": len(requests),
            "pending": len([r for r in requests if r.status == RightsRequestStatus.PENDING]),
            "completed": len([r for r in requests if r.status == RightsRequestStatus.COMPLETED]),
            "denied": len([r for r in requests if r.status == RightsRequestStatus.DENIED]),
            "overdue": len([self.is_request_overdue(r.request_id) for r in requests]),
        }
