import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt

from app.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET,
    OTP_EXPIRY_MINUTES,
)
from app.db import _connect


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, role: str, extra_data: Optional[dict] = None) -> str:
    """Generate a signed JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_data:
        to_encode.update(extra_data)
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as exc:
        raise ValueError("Invalid or expired authentication token") from exc


def get_user_by_id(user_id: str) -> Optional[dict]:
    with _connect() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[dict]:
    with _connect() as con:
        row = con.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip().lower(),)).fetchone()
        return dict(row) if row else None


def get_user_by_phone(phone: str) -> Optional[dict]:
    with _connect() as con:
        row = con.execute("SELECT * FROM users WHERE phone = ?", (phone.strip(),)).fetchone()
        return dict(row) if row else None


def create_user(
    role: str,
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    password: Optional[str] = None,
    linked_borrower_id: Optional[str] = None,
) -> dict:
    user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
    password_hash = hash_password(password) if password else None
    created_at = datetime.now(timezone.utc).isoformat()
    clean_email = email.strip().lower() if email else None
    clean_phone = phone.strip() if phone else None

    with _connect() as con:
        con.execute(
            """INSERT INTO users (id, role, name, email, phone, password_hash, linked_borrower_id, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (user_id, role, name.strip(), clean_email, clean_phone, password_hash, linked_borrower_id, created_at),
        )

    return get_user_by_id(user_id)


def create_otp_session(phone: str) -> tuple[str, str, int]:
    """Generate a 6-digit OTP, store hashed in db, and return raw OTP and session details."""
    clean_phone = phone.strip()
    # Generate 6 digit numeric OTP (deterministic 654321 for known demo phone 9876543210 if desired, or random)
    if clean_phone == "9876543210":
        otp = "654321"
    elif clean_phone == "9876543211":
        otp = "789123"
    else:
        otp = f"{100000 + secrets.randbelow(900000)}"

    session_id = f"OTP-{uuid.uuid4().hex[:8]}"
    otp_hash = hash_password(otp)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()
    created_at = datetime.now(timezone.utc).isoformat()

    with _connect() as con:
        con.execute("UPDATE otp_sessions SET used = 1 WHERE phone = ?", (clean_phone,))
        con.execute(
            """INSERT INTO otp_sessions (id, phone, otp_hash, expires_at, used, created_at)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (session_id, clean_phone, otp_hash, expires_at, created_at),
        )

    expires_in_seconds = OTP_EXPIRY_MINUTES * 60
    return session_id, otp, expires_in_seconds


def verify_otp(phone: str, raw_otp: str) -> bool:
    """Verify OTP against the latest active session for this phone."""
    clean_phone = phone.strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    with _connect() as con:
        # Get latest unused and unexpired OTP session for this phone
        row = con.execute(
            """SELECT id, otp_hash, expires_at, used FROM otp_sessions
               WHERE phone = ?
               ORDER BY created_at DESC LIMIT 1""",
            (clean_phone,),
        ).fetchone()

        if not row or row["used"] or row["expires_at"] <= now_iso:
            return False

        if verify_password(raw_otp.strip(), row["otp_hash"]):
            # Mark session as used
            consumed = con.execute("UPDATE otp_sessions SET used = 1 WHERE id = ? AND used = 0", (row["id"],))
            return consumed.rowcount == 1

    return False


def seed_demo_users():
    """Idempotently seed default demo users for the 3 roles."""
    def ensure_user(**fields):
        existing = get_user_by_email(fields['email']) if fields.get('email') else get_user_by_phone(fields['phone'])
        if not existing:
            create_user(**fields)

    # Seed 1: Bank Credit Officer
    ensure_user(
        role="bank_officer",
        name="Aditi Rao (Credit Officer)",
        email="officer@bank.demo",
        password="password123",
    )

    # Seed 2: Agricultural Insurance Underwriter
    ensure_user(
        role="insurance_agent",
        name="Rajesh Varma (Agri Insurer)",
        email="agent@insurance.demo",
        password="password123",
    )

    # Seed 3: Farmer Ramesh Patil (Linked to B-DEMO-001)
    ensure_user(
        role="farmer",
        name="Ramesh Patil (Nashik Wheat Farmer)",
        phone="9876543210",
        linked_borrower_id="B-DEMO-001",
    )

    # Seed 4: Farmer Sunita Bai (Linked to B-DEMO-002)
    ensure_user(
        role="farmer",
        name="Sunita Bai (Pune Maize Farmer)",
        phone="9876543211",
        linked_borrower_id="B-DEMO-002",
    )
