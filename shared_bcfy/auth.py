import base64
import hashlib
import hmac
import json
import logging
import os
import time


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def generate_jwt() -> str:
    """Generate Broadcastify JWT using env vars."""
    api_key = os.getenv("BCFY_API_KEY")
    api_key_id = os.getenv("BCFY_API_KEY_ID")
    app_id = os.getenv("BCFY_APP_ID")
    if not all([api_key, api_key_id, app_id]):
        raise RuntimeError("Missing one of: BCFY_API_KEY, BCFY_API_KEY_ID, BCFY_APP_ID")

    header = {"alg": "HS256", "typ": "JWT", "kid": api_key_id}
    iat = int(time.time())
    exp = iat + 3600
    payload = {"iss": app_id, "iat": iat, "exp": exp}

    enc_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    enc_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{enc_header}.{enc_payload}".encode()

    sig = hmac.new(api_key.encode(), signing_input, hashlib.sha256).digest()
    jwt_token = f"{enc_header}.{enc_payload}.{_b64url_encode(sig)}"

    # Debug logging
    logging.debug(f"Generated new JWT: {jwt_token[:50]}...")
    logging.debug(f"API Key ID: {api_key_id}, App ID: {app_id}, IAT: {iat}, EXP: {exp}")
    return jwt_token
