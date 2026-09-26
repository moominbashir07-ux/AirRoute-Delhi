"""
EmailJS REST API Integration for AirRoute Delhi.
Dispatches OTP verification emails server-to-server.
Ensures private keys and plaintext OTP codes are never exposed to browser JavaScript.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from typing import Tuple, Dict, Any, Optional
from dotenv import dotenv_values, load_dotenv

logger = logging.getLogger(__name__)

EMAILJS_API_URL = "https://api.emailjs.com/api/v1.0/email/send"

# Load environment variables from .env files
_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
_backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
if os.path.exists(_root_env):
    load_dotenv(_root_env)
if os.path.exists(_backend_env):
    load_dotenv(_backend_env)


def get_emailjs_config() -> Dict[str, str]:
    """Retrieve EmailJS credentials from environment variables."""
    # Ensure fresh read from environment / .env
    vals = {}
    if os.path.exists(_root_env):
        vals.update(dotenv_values(_root_env))
    if os.path.exists(_backend_env):
        vals.update(dotenv_values(_backend_env))
    vals.update(os.environ)

    return {
        "service_id": str(vals.get("EMAILJS_SERVICE_ID", "")).strip(),
        "template_id": str(vals.get("EMAILJS_TEMPLATE_ID", "")).strip(),
        "public_key": str(vals.get("EMAILJS_PUBLIC_KEY", "")).strip(),
        "private_key": str(vals.get("EMAILJS_PRIVATE_KEY", "")).strip(),
    }


def is_emailjs_configured() -> bool:
    """Check if mandatory EmailJS configuration parameters are set."""
    cfg = get_emailjs_config()
    return bool(cfg["service_id"] and cfg["template_id"] and cfg["public_key"])


def send_otp_email(
    to_email: str,
    otp: str,
    to_name: Optional[str] = None,
    timeout_seconds: float = 10.0
) -> Tuple[bool, str]:
    """
    Send a 6-digit OTP verification code to the recipient via EmailJS REST API.

    Template parameters passed to EmailJS include:
        to_email, email: Recipient email address
        to_name, name: Recipient display name
        otp, otp_code, code: 6-digit numeric verification code
        message: Pre-formatted informational message

    Returns:
        (success: bool, message: str)
    """
    cfg = get_emailjs_config()
    environment = os.getenv("ENVIRONMENT", "development").lower()

    # In development or test mode without credentials, allow simulated delivery
    if not is_emailjs_configured():
        if environment in ("development", "test"):
            logger.info(
                f"[SIMULATED EMAIL] Delivery simulated for recipient {to_email} "
                f"(EmailJS credentials not configured in {environment} environment)."
            )
            return True, "Simulated email delivery (development mode)."
        else:
            logger.error("EmailJS credentials (SERVICE_ID, TEMPLATE_ID, PUBLIC_KEY) missing in production.")
            return False, "Email service is not configured on the server."

    display_name = to_name.strip() if to_name and to_name.strip() else to_email.split("@")[0]

    payload: Dict[str, Any] = {
        "service_id": cfg["service_id"],
        "template_id": cfg["template_id"],
        "user_id": cfg["public_key"],
        "template_params": {
            "to_email": to_email,
            "to_name": display_name,
            "otp": otp,
            "message": f"Your AirRoute Delhi verification code is {otp}. It is valid for 5 minutes.",
            # Compatible aliases for EmailJS templates
            "OTP": otp,
            "passcode": otp,
            "token": otp,
            "otp_code": otp,
            "code": otp,
            "email": to_email,
            "name": display_name,
            "company_name": "AirRoute Delhi",
            "company": "AirRoute Delhi",
            "time": "5 minutes",
        }
    }

    if cfg["private_key"]:
        payload["accessToken"] = cfg["private_key"]

    req_data = json.dumps(payload).encode("utf-8")
    origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").strip() or "http://localhost:3000"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": origin,
    }

    req = urllib.request.Request(
        EMAILJS_API_URL,
        data=req_data,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8", errors="replace")
            if 200 <= status_code < 300:
                logger.info(f"OTP email successfully dispatched to {to_email} via EmailJS (status: {status_code}).")
                return True, f"OTP email dispatched successfully (status {status_code})."
            else:
                logger.error(f"EmailJS returned HTTP {status_code}: {response_body}")
                return False, f"Email delivery provider returned status {status_code}: {response_body}"
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace").strip()
        logger.error(f"EmailJS HTTP error {e.code}: {err_msg}")
        return False, f"Email delivery provider returned HTTP {e.code}: {err_msg}"
    except urllib.error.URLError as e:
        logger.error(f"EmailJS connection error: {e.reason}")
        return False, "Could not connect to email delivery provider."
    except Exception as e:
        logger.error(f"Unexpected error while sending OTP email: {e}")
        return False, "An unexpected error occurred during email dispatch."
