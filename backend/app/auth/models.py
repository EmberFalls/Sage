from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

UserRole = Literal["bank_officer", "branch_lead", "insurance_agent", "farmer", "admin"]


class UserProfile(BaseModel):
    id: str
    role: UserRole
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linked_borrower_id: Optional[str] = None
    branch_id: Optional[str] = None
    is_active: bool = True
    created_at: str


class AuthInput(BaseModel):
    @field_validator('phone', check_fields=False)
    @classmethod
    def normalize_phone(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value.isascii() or not value.isdigit() or len(value) != 10:
            raise ValueError('Phone must contain exactly 10 digits')
        return value

    @field_validator('email', 'name', check_fields=False)
    @classmethod
    def normalize_text(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError('Value cannot be blank')
        return value

    @field_validator('password', check_fields=False)
    @classmethod
    def password_bytes(cls, value):
        if value is not None and len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be at most 72 UTF-8 bytes')
        return value


class UserRegisterRequest(AuthInput):
    role: UserRole
    name: str = Field(..., min_length=2)
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    linked_borrower_id: Optional[str] = None


class UserLoginRequest(AuthInput):
    email: str
    password: str


class OTPSendRequest(AuthInput):
    phone: str = Field(..., min_length=10, max_length=15, description="Farmer 10-digit mobile number")


class OTPSendResponse(BaseModel):
    status: str = "success"
    message: str
    phone: str
    otp: str  # Included in demo mode for frictionless testing
    expires_in_seconds: int


class OTPVerifyRequest(AuthInput):
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
