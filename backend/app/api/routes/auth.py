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

@router.post("/register")
def register(req: RegisterRequest):
    mgr = get_user_manager()
    user = mgr.create_user(req.username, req.password, role="viewer", email=req.email)
    if not user:
        raise HTTPException(status_code=409, detail="Username already exists")
    return {"user_id": user.user_id, "username": user.username, "role": user.role}
