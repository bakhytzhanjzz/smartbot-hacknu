# utils/ws_token.py
from django.core import signing
from django.conf import settings
from datetime import timedelta

WS_TOKEN_SALT = "smartbot_ws_token_salt"
WS_TOKEN_MAX_AGE = int(getattr(settings, "WS_TOKEN_MAX_AGE", 600))  # по умолчанию 10 минут

def generate_ws_token(application_id: int, ttl_seconds: int = None) -> str:
    payload = {"application_id": application_id}
    token = signing.dumps(payload, salt=WS_TOKEN_SALT)
    return token

def verify_ws_token(token: str, max_age: int = None):
    if max_age is None:
        max_age = WS_TOKEN_MAX_AGE
    try:
        data = signing.loads(token, salt=WS_TOKEN_SALT, max_age=max_age)
        return data  # dict with application_id
    except signing.BadSignature:
        return None
    except signing.SignatureExpired:
        return None
