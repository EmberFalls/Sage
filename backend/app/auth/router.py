from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.auth.models import (
    DemoAccount,
    OTPSendRequest,
    OTPSendResponse,
    OTPVerifyRequest,
    TokenResponse,
    UserLoginRequest,
    UserProfile,
    UserRegisterRequest,
)
from app.auth.service import (
    create_access_token,
    create_otp_session,
    create_user,
    get_user_by_email,
    get_user_by_phone,
    verify_otp,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
def register(req: UserRegisterRequest):
    """Register a new user account (Bank Officer, Insurance Agent, or Farmer)."""
    if req.role in ("bank_officer", "insurance_agent"):
        if not req.email or not req.password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email and password are required for institutional accounts.",
            )
        if get_user_by_email(req.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with email '{req.email}' already exists.",
            )
    elif req.role == "farmer":
        if not req.phone:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Phone number is required for farmer accounts.",
            )
        if get_user_by_phone(req.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with phone '{req.phone}' already exists. Please login with OTP.",
            )

    user = create_user(
        role=req.role,
        name=req.name,
        email=req.email,
        phone=req.phone,
        password=req.password,
        linked_borrower_id=req.linked_borrower_id,
    )

    token = create_access_token(
        user_id=user["id"],
        role=user["role"],
        extra_data={"name": user["name"], "linked_borrower_id": user.get("linked_borrower_id")},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfile(
            id=user["id"],
            role=user["role"],
            name=user["name"],
            email=user.get("email"),
            phone=user.get("phone"),
            linked_borrower_id=user.get("linked_borrower_id"),
            is_active=bool(user.get("is_active", 1)),
            created_at=user["created_at"],
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest):
    """Authenticate bank officers and insurance agents using email and password."""
    user = get_user_by_email(req.email)
    if not user or not user.get("password_hash"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact platform admin.",
        )

    token = create_access_token(
        user_id=user["id"],
        role=user["role"],
        extra_data={"name": user["name"], "linked_borrower_id": user.get("linked_borrower_id")},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfile(
            id=user["id"],
            role=user["role"],
            name=user["name"],
            email=user.get("email"),
            phone=user.get("phone"),
            linked_borrower_id=user.get("linked_borrower_id"),
            is_active=bool(user.get("is_active", 1)),
            created_at=user["created_at"],
        ),
    )


@router.post("/otp/send", response_model=OTPSendResponse)
def send_otp(req: OTPSendRequest):
    """Generate a 6-digit OTP for farmer mobile login."""
    phone = req.phone.strip()
    if len(phone) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please provide a valid 10-digit mobile number.",
        )

    session_id, raw_otp, expires_in_sec = create_otp_session(phone)

    return OTPSendResponse(
        status="success",
        message=f"OTP generated for +91 {phone[-10:]}. Use the code shown on screen.",
        phone=phone,
        otp=raw_otp,
        expires_in_seconds=expires_in_sec,
    )


@router.post("/otp/verify", response_model=TokenResponse)
def verify_farmer_otp(req: OTPVerifyRequest):
    """Verify OTP and authenticate farmer. Auto-registers farmer profile if first time."""
    phone = req.phone.strip()
    if not verify_otp(phone, req.otp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code. Please request a new one.",
        )

    user = get_user_by_phone(phone)
    if not user:
        # First time farmer login -> auto register
        farmer_name = req.name or f"Farmer (+91 {phone[-4:]})"
        # If demo phone matches known records, link automatically
        linked_id = req.linked_borrower_id
        if not linked_id:
            if phone.endswith("3210"):
                linked_id = "B-DEMO-001"
            elif phone.endswith("3211"):
                linked_id = "B-DEMO-002"

        user = create_user(
            role="farmer",
            name=farmer_name,
            phone=phone,
            linked_borrower_id=linked_id,
        )

    token = create_access_token(
        user_id=user["id"],
        role=user["role"],
        extra_data={"name": user["name"], "linked_borrower_id": user.get("linked_borrower_id")},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfile(
            id=user["id"],
            role=user["role"],
            name=user["name"],
            email=user.get("email"),
            phone=user.get("phone"),
            linked_borrower_id=user.get("linked_borrower_id"),
            is_active=bool(user.get("is_active", 1)),
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserProfile)
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Fetch profile of currently authenticated user."""
    return UserProfile(
        id=current_user["id"],
        role=current_user["role"],
        name=current_user["name"],
        email=current_user.get("email"),
        phone=current_user.get("phone"),
        linked_borrower_id=current_user.get("linked_borrower_id"),
        is_active=bool(current_user.get("is_active", 1)),
        created_at=current_user["created_at"],
    )


@router.get("/demo-accounts", response_model=List[DemoAccount])
def list_demo_accounts():
    """Return list of quick-access demo credentials for seamless presentation."""
    return [
        DemoAccount(
            role="bank_officer",
            role_label="Bank Credit Officer",
            name="Aditi Rao",
            email="officer@bank.demo",
            password="password123",
            description="Full read/write portfolio management, stress test simulation & restructuring approval",
        ),
        DemoAccount(
            role="insurance_agent",
            role_label="Agri Insurance Underwriter",
            name="Rajesh Varma",
            email="agent@insurance.demo",
            password="password123",
            description="Read-only portfolio risk & climate vulnerability monitoring",
        ),
        DemoAccount(
            role="farmer",
            role_label="Farmer (Nashik - Wheat)",
            name="Ramesh Patil",
            phone="9876543210",
            password="OTP: 654321",
            linked_borrower_id="B-DEMO-001",
            description="Mobile OTP access for loan schedule, climate advisory & payment status",
        ),
        DemoAccount(
            role="farmer",
            role_label="Farmer (Pune - Maize)",
            name="Sunita Bai",
            phone="9876543211",
            password="OTP: 789123",
            linked_borrower_id="B-DEMO-002",
            description="Mobile OTP access for loan schedule & climate risk score",
        ),
    ]



