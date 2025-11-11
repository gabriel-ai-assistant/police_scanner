import time
from .auth import generate_jwt

_cached_token = None
_expiry = 0

def get_jwt_token():
    global _cached_token, _expiry
    now = time.time()
    if _cached_token and now < _expiry:
        return _cached_token
    _cached_token = generate_jwt()
    _expiry = now + 3500  # refresh ~1h
    return _cached_token
