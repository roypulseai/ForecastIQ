"""JWT authentication dependency for protected routes."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..core.jwt import decode_access_token
from ..core.users import get_user_manager, User

security = HTTPBearer(auto_error=False)

async def require_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = get_user_manager().get_user(user_id)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

def require_role(action: str):
    async def _check(user: User = Depends(require_jwt)):
        if not user.has_permission(action):
            raise HTTPException(status_code=403, detail=f"Insufficient permissions for '{action}'")
        return user
    return _check
