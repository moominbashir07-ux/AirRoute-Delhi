import os
import sqlite3
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")
logger = logging.getLogger(__name__)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist and perform migrations if necessary."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            is_verified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Inspect existing otps table to migrate if schema is outdated
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='otps'")
    table_exists = cursor.fetchone()

    if table_exists:
        cursor.execute("PRAGMA table_info(otps)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "otp_hash" not in columns:
            logger.info("Migrating legacy otps table to hashed OTP security schema.")
            cursor.execute("DROP TABLE otps")
            cursor.execute("""
                CREATE TABLE otps (
                    email TEXT PRIMARY KEY,
                    otp_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 5,
                    last_sent_at TEXT NOT NULL,
                    request_count INTEGER DEFAULT 1,
                    first_requested_at TEXT NOT NULL
                )
            """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otps (
                email TEXT PRIMARY KEY,
                otp_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 5,
                last_sent_at TEXT NOT NULL,
                request_count INTEGER DEFAULT 1,
                first_requested_at TEXT NOT NULL
            )
        """)

    conn.commit()
    conn.close()
    logger.info("SQLite Database initialized and tables created/verified.")


def hash_password(password: str, salt: str = None) -> str:
    """Hash password using SHA-256 with a cryptographic salt."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored_password: str) -> bool:
    """Verify password matches stored hash using constant-time comparison."""
    try:
        salt, stored_hash = stored_password.split(":", 1)
        hashed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
        return secrets.compare_digest(hashed, stored_hash)
    except Exception:
        return False


def hash_otp(otp: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hash a 6-digit OTP using SHA-256 with a cryptographic salt."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((otp.strip() + salt).encode("utf-8")).hexdigest()
    return hashed, salt


def can_request_otp(
    email: str,
    cooldown_seconds: int = 60,
    max_requests_per_hour: int = 5
) -> Tuple[bool, str, int]:
    """
    Verify whether a user can request a new OTP under rate limiting and resend cooldown.

    Returns:
        (allowed: bool, reason: str, retry_after_seconds: int)
    """
    clean_email = email.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_sent_at, request_count, first_requested_at FROM otps WHERE email = ?",
        (clean_email,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return True, "", 0

    now = datetime.now(timezone.utc)
    try:
        last_sent = datetime.fromisoformat(row["last_sent_at"])
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        elapsed = (now - last_sent).total_seconds()

        # Enforce resend cooldown
        if elapsed < cooldown_seconds:
            remaining = int(cooldown_seconds - elapsed)
            return False, f"Please wait {remaining} seconds before requesting a new code.", remaining

        # Enforce hourly request quota
        first_req = datetime.fromisoformat(row["first_requested_at"])
        if first_req.tzinfo is None:
            first_req = first_req.replace(tzinfo=timezone.utc)
        hour_elapsed = (now - first_req).total_seconds()

        if hour_elapsed < 3600 and row["request_count"] >= max_requests_per_hour:
            retry_in = int(3600 - hour_elapsed)
            return False, f"Too many verification requests. Please try again in {retry_in // 60 + 1} minutes.", retry_in

    except Exception as e:
        logger.warning(f"Error checking OTP rate limits: {e}")

    return True, "", 0


def save_otp(
    email: str,
    otp: str,
    expires_in_seconds: int = 300,
    max_attempts: int = 5
) -> None:
    """Store hashed OTP with cryptographic salt, expiry, and rate limit tracking."""
    clean_email = email.strip().lower()
    otp_hash, salt = hash_otp(otp)

    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=expires_in_seconds)).isoformat()
    last_sent_at = now.isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT request_count, first_requested_at FROM otps WHERE email = ?",
        (clean_email,)
    )
    existing = cursor.fetchone()

    if existing:
        try:
            first_req = datetime.fromisoformat(existing["first_requested_at"])
            if first_req.tzinfo is None:
                first_req = first_req.replace(tzinfo=timezone.utc)
            if (now - first_req).total_seconds() >= 3600:
                # Reset hourly window
                first_requested_at = now.isoformat()
                request_count = 1
            else:
                first_requested_at = existing["first_requested_at"]
                request_count = existing["request_count"] + 1
        except Exception:
            first_requested_at = now.isoformat()
            request_count = 1
    else:
        first_requested_at = now.isoformat()
        request_count = 1

    cursor.execute("""
        INSERT OR REPLACE INTO otps (
            email, otp_hash, salt, expires_at, attempts, max_attempts,
            last_sent_at, request_count, first_requested_at
        ) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)
    """, (
        clean_email, otp_hash, salt, expires_at, max_attempts,
        last_sent_at, request_count, first_requested_at
    ))

    conn.commit()
    conn.close()


def delete_otp(email: str) -> None:
    """Remove pending OTP for an email."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM otps WHERE email = ?", (email.strip().lower(),))
    conn.commit()
    conn.close()


def verify_otp(email: str, code: str) -> Tuple[bool, str]:
    """
    Verify entered OTP against stored cryptographic hash.
    Enforces maximum attempts, expiry, and immediate single-use invalidation.

    Returns:
        (success: bool, message: str)
    """
    clean_email = email.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT otp_hash, salt, expires_at, attempts, max_attempts FROM otps WHERE email = ?",
        (clean_email,)
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False, "No active verification code found. Please request a new OTP."

    otp_hash = row["otp_hash"]
    salt = row["salt"]
    expires_at = row["expires_at"]
    attempts = row["attempts"]
    max_attempts = row["max_attempts"]
    now = datetime.now(timezone.utc)

    # 1. Check max attempts
    if attempts >= max_attempts:
        cursor.execute("DELETE FROM otps WHERE email = ?", (clean_email,))
        conn.commit()
        conn.close()
        return False, "Maximum verification attempts exceeded. Please request a new OTP."

    # 2. Check expiry
    try:
        exp_dt = datetime.fromisoformat(expires_at)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        if exp_dt < now:
            cursor.execute("DELETE FROM otps WHERE email = ?", (clean_email,))
            conn.commit()
            conn.close()
            return False, "Verification code has expired. Please request a new OTP."
    except Exception as e:
        logger.error(f"Error parsing OTP expiry timestamp: {e}")
        cursor.execute("DELETE FROM otps WHERE email = ?", (clean_email,))
        conn.commit()
        conn.close()
        return False, "Invalid verification session. Please request a new OTP."

    # 3. Check hash using constant-time comparison
    computed_hash = hashlib.sha256((code.strip() + salt).encode("utf-8")).hexdigest()
    if secrets.compare_digest(computed_hash, otp_hash):
        # Single-use: immediately invalidate OTP
        cursor.execute("DELETE FROM otps WHERE email = ?", (clean_email,))
        conn.commit()
        conn.close()
        return True, "OTP verified successfully."

    # 4. Incorrect code: increment attempt counter
    new_attempts = attempts + 1
    if new_attempts >= max_attempts:
        cursor.execute("DELETE FROM otps WHERE email = ?", (clean_email,))
        conn.commit()
        conn.close()
        return False, "Invalid verification code. Maximum attempts exceeded. Please request a new OTP."

    cursor.execute("UPDATE otps SET attempts = ? WHERE email = ?", (new_attempts, clean_email))
    conn.commit()
    conn.close()
    remaining = max_attempts - new_attempts
    return False, f"Invalid verification code. {remaining} attempt(s) remaining."


def create_user(email: str, password_raw: str, name: str) -> bool:
    """Register a new user with hashed password."""
    conn = get_connection()
    cursor = conn.cursor()
    password_hashed = hash_password(password_raw)

    try:
        cursor.execute(
            "INSERT INTO users (email, password, name, is_verified) VALUES (?, ?, ?, 1)",
            (email.strip().lower(), password_hashed, name.strip())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetch user dict from DB."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, email, password, name, is_verified, created_at FROM users WHERE email = ?",
        (email.strip().lower(),)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def create_or_get_user(email: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve an existing user, or create a new verified user for OTP authentication."""
    clean_email = email.strip().lower()
    user = get_user_by_email(clean_email)
    if user:
        return user

    display_name = name.strip() if name and name.strip() else clean_email.split("@")[0]
    random_pw = secrets.token_urlsafe(32)
    create_user(clean_email, random_pw, display_name)
    created_user = get_user_by_email(clean_email)
    return created_user or {"id": 0, "email": clean_email, "name": display_name}
