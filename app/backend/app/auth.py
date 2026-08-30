from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from .config import Settings
from .subjects import normalize_subject

PASSWORD_ITERATIONS = 310_000
ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"
VALID_ROLES = {ROLE_ADMIN, ROLE_STUDENT}


@dataclass(frozen=True)
class AuthSession:
    username: str
    role: str
    subject: str
    expires_at: int


def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return "$".join(
        [
            "pbkdf2_sha256",
            str(PASSWORD_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_text, digest_text = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
    except (TypeError, ValueError, UnicodeError):
        return False

    return hmac.compare_digest(actual, expected)


def _ensure_users_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
        )
        """
    )
    existing_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    if "role" not in existing_columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'"
        )
    conn.execute(
        "UPDATE users SET role = ? WHERE role IS NULL OR role NOT IN (?, ?)",
        (ROLE_STUDENT, ROLE_ADMIN, ROLE_STUDENT),
    )


def ensure_bootstrap_user(
    db_path: Path,
    username: str,
    password: str,
) -> None:
    normalized_username = normalize_username(username)
    with sqlite3.connect(str(db_path)) as conn:
        _ensure_users_table(conn)
        exists = conn.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (normalized_username,),
        ).fetchone()
        if exists is None:
            conn.execute(
                """
                INSERT INTO users (username, password_hash, created_at, role)
                VALUES (?, ?, ?, ?)
                """,
                (
                    normalized_username,
                    hash_password(password),
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    ROLE_ADMIN,
                ),
            )
        else:
            conn.execute(
                "UPDATE users SET role = ? WHERE username = ?",
                (ROLE_ADMIN, normalized_username),
            )


def register_user(
    db_path: Path,
    username: str,
    password: str,
) -> str:
    normalized_username = normalize_username(username)
    try:
        with sqlite3.connect(str(db_path)) as conn:
            _ensure_users_table(conn)
            conn.execute(
                """
                INSERT INTO users (username, password_hash, created_at, role)
                VALUES (?, ?, ?, ?)
                """,
                (
                    normalized_username,
                    hash_password(password),
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    ROLE_STUDENT,
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("该账号已存在，请直接登录。") from exc

    return normalized_username


def get_user_role(db_path: Path, username: str) -> str | None:
    normalized_username = normalize_username(username)
    with sqlite3.connect(str(db_path)) as conn:
        _ensure_users_table(conn)
        row = conn.execute(
            "SELECT role FROM users WHERE username = ?",
            (normalized_username,),
        ).fetchone()

    if row is None:
        return None
    role = str(row[0]).strip().lower()
    return role if role in VALID_ROLES else ROLE_STUDENT


def authenticate(
    db_path: Path,
    username: str,
    password: str,
) -> bool:
    normalized_username = normalize_username(username)
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (normalized_username,),
        ).fetchone()

    if row is None:
        return False
    return verify_password(password, row[0])


def _encode_payload(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_payload(value: str) -> dict:
    padding = "=" * (-len(value) % 4)
    raw = base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("令牌内容无效。")
    return payload


def _signature(settings: Settings, payload_part: str) -> str:
    digest = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        payload_part.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def create_access_token(
    settings: Settings,
    username: str,
    subject: str,
    role: str = ROLE_STUDENT,
) -> tuple[str, int]:
    expires_at = int(time.time()) + settings.session_ttl_hours * 60 * 60
    payload_part = _encode_payload(
        {
            "username": username,
            "role": role if role in VALID_ROLES else ROLE_STUDENT,
            "subject": normalize_subject(subject),
            "expires_at": expires_at,
        }
    )
    token = f"{payload_part}.{_signature(settings, payload_part)}"
    return token, expires_at


def verify_access_token(settings: Settings, token: str) -> AuthSession | None:
    try:
        payload_part, provided_signature = token.split(".", 1)
        expected_signature = _signature(settings, payload_part)
        if not hmac.compare_digest(provided_signature, expected_signature):
            return None

        payload = _decode_payload(payload_part)
        username = str(payload["username"]).strip()
        role = str(payload.get("role") or "").strip().lower()
        subject = normalize_subject(str(payload["subject"]))
        expires_at = int(payload["expires_at"])
    except (KeyError, TypeError, ValueError, UnicodeError):
        return None

    if not username or expires_at <= int(time.time()):
        return None

    if role not in VALID_ROLES:
        role = get_user_role(settings.conversation_db_path, username) or ROLE_STUDENT

    return AuthSession(
        username=username,
        role=role,
        subject=subject,
        expires_at=expires_at,
    )
