from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class RetentionPeriod(str, Enum):
    ACTIVE_USERS = "active_users"
    INACTIVE_USERS = "inactive_users"
    DELETED_USERS = "deleted_users"
    LOGS = "logs"
    FINANCIAL = "financial"
    CUSTOM = "custom"


RETENTION_POLICY_CONFIG = {
    RetentionPeriod.ACTIVE_USERS: {
        "pii": 365,
        "financial": 2555,
        "analytics": 730,
        "operational": 1095,
    },
    RetentionPeriod.INACTIVE_USERS: {
        "pii": 730,
        "financial": 2555,
        "analytics": 180,
        "operational": 365,
    },
    RetentionPeriod.DELETED_USERS: {
        "pii": 30,
        "financial": 2555,
        "analytics": 0,
        "operational": 30,
    },
    RetentionPeriod.LOGS: {
        "access": 90,
        "security": 365,
        "audit": 730,
        "error": 90,
    },
    RetentionPeriod.FINANCIAL: {
        "transactions": 2555,
        "invoices": 2555,
        "tax_records": 2555,
        "audit_logs": 2555,
    },
}


class RetentionRule(BaseModel):
    data_type: str
    retention_days: int
    legal_basis: str
    jurisdiction: str
    applies_to_active: bool = True
    applies_to_inactive: bool = True
    applies_to_deleted: bool = False
    legal_hold_exempt: bool = False


class RetentionPolicy(BaseModel):
    policy_id: str
    rules: List[RetentionRule]
    enforce_deletion: bool = True
    deletion_check_interval_hours: int = 24


class DeletionTask(BaseModel):
    task_id: str
    data_type: str
    user_id: Optional[str] = None
    record_id: Optional[str] = None
    scheduled_deletion_date: datetime
    legal_hold: bool = False
    status: str = "pending"


class RetentionManager:
    def __init__(self):
        self._policies: Dict[str, RetentionPolicy] = {}
        self._deletion_tasks: Dict[str, List[DeletionTask]] = {}
        self._legal_holds: Dict[str, bool] = {}

    def add_policy(self, policy: RetentionPolicy) -> None:
        self._policies[policy.policy_id] = policy

    def create_retention_rule(
        self,
        data_type: str,
        retention_days: int,
        legal_basis: str,
        jurisdiction: str,
    ) -> RetentionRule:
        return RetentionRule(
            data_type=data_type,
            retention_days=retention_days,
            legal_basis=legal_basis,
            jurisdiction=jurisdiction,
        )

    def schedule_deletion(
        self,
        data_type: str,
        user_id: Optional[str] = None,
        record_id: Optional[str] = None,
        jurisdiction: str = "default",
    ) -> DeletionTask:
        policy = self._get_applicable_policy(jurisdiction, data_type)
        retention_days = self._get_retention_days(policy, data_type, user_id)

        task = DeletionTask(
            task_id=f"del_{datetime.utcnow().timestamp()}",
            data_type=data_type,
            user_id=user_id,
            record_id=record_id,
            scheduled_deletion_date=datetime.utcnow() + timedelta(days=retention_days),
            legal_hold=self.is_under_legal_hold(user_id or record_id or data_type),
        )

        if user_id:
            if user_id not in self._deletion_tasks:
                self._deletion_tasks[user_id] = []
            self._deletion_tasks[user_id].append(task)

        return task

    def cancel_deletion(self, task_id: str, user_id: str) -> bool:
        if user_id in self._deletion_tasks:
            for task in self._deletion_tasks[user_id]:
                if task.task_id == task_id:
                    task.status = "cancelled"
                    return True
        return False

    def apply_legal_hold(self, identifier: str) -> None:
        self._legal_holds[identifier] = True

    def remove_legal_hold(self, identifier: str) -> None:
        self._legal_holds[identifier] = False

    def is_under_legal_hold(self, identifier: str) -> bool:
        return self._legal_holds.get(identifier, False)

    def get_pending_deletions(self, user_id: str) -> List[DeletionTask]:
        if user_id not in self._deletion_tasks:
            return []
        return [
            t for t in self._deletion_tasks[user_id]
            if t.status == "pending" and not t.legal_hold
        ]

    def get_retention_summary(self, user_id: str) -> Dict[str, Any]:
        now = datetime.utcnow()
        return {
            "user_id": user_id,
            "legal_hold": self.is_under_legal_hold(user_id),
            "pending_deletions": len(self.get_pending_deletions(user_id)),
            "next_deletion": (
                min(
                    (t.scheduled_deletion_date for t in self.get_pending_deletions(user_id)),
                    default=None,
                )
            ),
            "data_categories": {
                "pii": self._calculate_deletion_date(user_id, "pii"),
                "financial": self._calculate_deletion_date(user_id, "financial"),
                "analytics": self._calculate_deletion_date(user_id, "analytics"),
            },
        }

    def _get_applicable_policy(self, jurisdiction: str, data_type: str) -> Optional[RetentionPolicy]:
        for policy in self._policies.values():
            if any(rule.data_type == data_type for rule in policy.rules):
                return policy
        return None

    def _get_retention_days(
        self, policy: Optional[RetentionPolicy], data_type: str, user_id: Optional[str]
    ) -> int:
        if policy:
            for rule in policy.rules:
                if rule.data_type == data_type:
                    return rule.retention_days

        for period_type, config in RETENTION_POLICY_CONFIG.items():
            if data_type in config:
                return config[data_type]

        return 365

    def _calculate_deletion_date(self, user_id: str, data_type: str) -> Optional[datetime]:
        pending = [
            t.scheduled_deletion_date for t in self.get_pending_deletions(user_id)
            if t.data_type == data_type
        ]
        return min(pending) if pending else None
