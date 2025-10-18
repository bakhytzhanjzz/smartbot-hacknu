# candidates/utils.py
import jwt
from datetime import datetime, timedelta
from django.conf import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

def create_chat_token(application_id: int, expires_minutes: int = 10) -> str:
    payload = {
        "application_id": application_id,
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_chat_token(token: str) -> dict:
    import jwt
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
