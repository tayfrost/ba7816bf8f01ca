import os
import hmac
import hashlib
import time


SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")


def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    print(f"Timestamp check: {abs(time.time() - int(timestamp))} seconds")
    if abs(time.time() - int(timestamp)) > 60 * 5:
        print("Timestamp too old")
        return False
    
    sig_basestring = f"v0:{timestamp}:{body.decode()}".encode()
    expected_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()
    
    print(f"Expected: {expected_signature}")
    print(f"Received: {signature}")
    
    return hmac.compare_digest(expected_signature, signature)
