import os
import hmac
import hashlib
import time
import logging

logger = logging.getLogger(__name__)

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")

if not SLACK_SIGNING_SECRET:
    logger.error("SLACK_SIGNING_SECRET is not configured - signature verification will fail")


def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """
    Verify Slack request signature for security.
    
    Args:
        body: Raw request body
        timestamp: X-Slack-Request-Timestamp header
        signature: X-Slack-Signature header
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not SLACK_SIGNING_SECRET:
        logger.error("Cannot verify signature - SLACK_SIGNING_SECRET not set")
        return False
    
    try:
        timestamp_int = int(timestamp)
    except (ValueError, TypeError):
        logger.warning("Invalid timestamp format received")
        return False
    
    # Check timestamp age (prevent replay attacks)
    time_diff = abs(time.time() - timestamp_int)
    if time_diff > 60 * 5:
        logger.warning(f"Request timestamp too old: {time_diff} seconds")
        return False
    
    # Build signature
    sig_basestring = f"v0:{timestamp}:{body.decode()}".encode()
    expected_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (constant-time comparison)
    is_valid = hmac.compare_digest(expected_signature, signature)
    
    if not is_valid:
        logger.warning("Signature verification failed")
    
    return is_valid
