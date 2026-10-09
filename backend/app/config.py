import os
from pathlib import Path

# Auto-load .env from backend directory
_env_path = Path(__file__).resolve().parents[1] / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_env_path)
    except ImportError:
        pass

PRODUCT_NAME = os.getenv("PRODUCT_NAME", "Sage")
DEMO_SEED = int(os.getenv("DEMO_SEED", "20261009"))
ENGINE_VERSION = "risk-engine-v2-demo.5"

# Authentication settings
APP_MODE = os.getenv("SAGE_MODE", "demo").lower()
JWT_SECRET = os.getenv("JWT_SECRET", "sage-demo-super-secret-key-2026" if APP_MODE == "demo" else "")
if APP_MODE == "hosted" and len(JWT_SECRET) < 32:
    raise RuntimeError("Hosted mode requires JWT_SECRET with at least 32 characters")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60" if APP_MODE == "hosted" else "1440"))
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "10"))

