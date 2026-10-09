from typing import Literal, Optional
from pydantic import BaseModel, Field

UserRole = Literal["bank_officer", "insurance_agent", "farmer"]


class UserProfile(BaseModel):
    id: str
    role: UserRole
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linked_borrower_id: Optional[str] = None
    is_active: bool = True
    created_at: str


class UserRegisterRequest(BaseModel):
    role: UserRole
    name: str = Field(..., min_length=2)
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    linked_borrower_id: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class OTPSendRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15, description="Farmer 10-digit mobile number")


class OTPSendResponse(BaseModel):
    status: str = "success"
    message: str
    phone: str
    otp: str  # Included in demo mode for frictionless testing
    expires_in_seconds: int


class OTPVerifyRequest(BaseModel):
    phone: str
    otp: str
    name: Optional[str] = None
    linked_borrower_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


class DemoAccount(BaseModel):
    role: UserRole
    role_label: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    linked_borrower_id: Optional[str] = None
    description: str
