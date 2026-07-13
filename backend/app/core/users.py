"""Simple file-based user management."""
import json
import os
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from .jwt import hash_password, verify_password
from ..core.config import settings

@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    role: str = "viewer"  # admin, analyst, viewer
    email: str = ""
    created_at: float = 0.0
    active: bool = True

    def has_permission(self, action: str) -> bool:
        permissions = {
            "admin": ["read", "write", "delete", "manage_users", "manage_api_keys"],
            "analyst": ["read", "write"],
            "viewer": ["read"],
        }
        return action in permissions.get(self.role, [])

class UserManager:
    def __init__(self):
        self._users: dict = {}
        self._lock = threading.RLock()
        self._path = os.path.join(settings.DATA_DIR, "users.json")
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            with open(self._path, "r") as f:
                data = json.load(f)
                for uid, udata in data.items():
                    self._users[uid] = User(**udata)

    def _persist(self):
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w") as f:
            json.dump({uid: asdict(u) for uid, u in self._users.items()}, f, indent=2)

    def create_user(self, username: str, password: str, role: str = "viewer", email: str = "") -> Optional[User]:
        import uuid, time
        with self._lock:
            if any(u.username == username for u in self._users.values()):
                return None
            uid = uuid.uuid4().hex[:12]
            user = User(
                user_id=uid,
                username=username,
                password_hash=hash_password(password),
                role=role,
                email=email,
                created_at=time.time(),
            )
            self._users[uid] = user
            self._persist()
            return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        with self._lock:
            for user in self._users.values():
                if user.username == username and user.active:
                    if verify_password(password, user.password_hash):
                        return user
            return None

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def list_users(self) -> List[User]:
        return list(self._users.values())

    def delete_user(self, user_id: str) -> bool:
        with self._lock:
            if user_id in self._users:
                del self._users[user_id]
                self._persist()
                return True
            return False

_user_manager: Optional[UserManager] = None

def get_user_manager() -> UserManager:
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager
