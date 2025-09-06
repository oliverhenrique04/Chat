import os
import time
from typing import Optional, Dict

from passlib.context import CryptContext
import jwt
from dotenv import load_dotenv

load_dotenv()

# Hash de senha (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGO = "HS256"
JWT_EXPIRES_SECONDS = int(os.getenv("JWT_EXPIRES_SECONDS", "604800"))  # 7 dias

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

def sign_token(user: Dict) -> str:
    payload = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRES_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def verify_token(token: Optional[str]) -> Optional[Dict]:
    if not token:
        return None
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return {"id": data["id"], "name": data["name"], "email": data["email"]}
    except Exception:
        return None
