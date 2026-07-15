"""JWT authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ...core.jwt import create_access_token
from ...core.users import get_user_manager

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""
    role: str = "viewer"

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    mgr = get_user_manager()
    user = mgr.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.user_id, "role": user.role})
    return LoginResponse(
        access_token=token,
        user_id=user.user_id,
        username=user.username,
        role=user.role,
    )

@router.get("/status")
def auth_status():
    """Return whether any users exist (for auto-login on first run)."""
    mgr = get_user_manager()
    return {"has_users": len(mgr.list_users()) > 0}


@router.post("/demo")
def demo_login():
    """Issue a real admin JWT for demo/testing. Creates a temporary admin
    user on the fly so every API call succeeds."""
    import uuid, time
    mgr = get_user_manager()
    demo_id = f"demo-{uuid.uuid4().hex[:8]}"
    mgr.create_user(demo_id, "demo", role="admin")
    user = mgr.authenticate(demo_id, "demo")
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create demo user")
    token = create_access_token({"sub": user.user_id, "role": user.role})
    return LoginResponse(
        access_token=token,
        user_id=user.user_id,
        username="demo",
        role="admin",
    )


@router.post("/register")
def register(req: RegisterRequest):
    mgr = get_user_manager()
    user = mgr.create_user(req.username, req.password, role="viewer", email=req.email)
    if not user:
        raise HTTPException(status_code=409, detail="Username already exists")
    return {"user_id": user.user_id, "username": user.username, "role": user.role}
