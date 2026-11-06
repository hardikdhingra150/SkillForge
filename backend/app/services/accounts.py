"""Accounts for AUTH_MODE=accounts: scrypt password hashes and opaque session tokens (only their hash is stored)."""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.config import settings
from app.database.account_models import User, UserSession
from app.database.models import Workspace

SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return f"scrypt${SCRYPT['n']}${salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        scheme, n, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=8, p=1, dklen=32)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual.hex(), digest)


# Compared against when the email is unknown, so a wrong email takes as long as a wrong password.
DUMMY_HASH = hash_password(secrets.token_hex(8))


def normalize_email(email: str) -> str:
    value = email.strip().lower()
    if len(value) > 254 or not EMAIL.match(value):
        raise ValueError("Enter a valid email address.")
    return value


def check_new_password(password: str, email: str):
    if len(password) < 10:
        raise ValueError("Use at least 10 characters for the password.")
    if len(password) > 200:
        raise ValueError("Use at most 200 characters for the password.")
    if password.lower() in {email, email.split("@")[0]} or len(set(password)) < 4:
        raise ValueError("Choose a password that is harder to guess.")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_user(db, email: str, password: str, name: str = "") -> User:
    email = normalize_email(email)
    check_new_password(password, email)
    if db.scalars(select(User).where(User.email == email)).first() is not None:
        raise ValueError("An account with this email already exists. Sign in instead.")
    workspace = Workspace(name=(name.strip() or email.split("@")[0])[:120] + "'s workspace")
    db.add(workspace)
    db.flush()
    user = User(email=email, name=name.strip()[:120], password_hash=hash_password(password), workspace_id=workspace.id)
    db.add(user)
    db.flush()
    return user


def authenticate(db, email: str, password: str) -> User | None:
    try:
        email = normalize_email(email)
    except ValueError:
        check_password(password, DUMMY_HASH)
        return None
    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None:
        check_password(password, DUMMY_HASH)
        return None
    return user if check_password(password, user.password_hash) else None


def start_session(db, user: User) -> str:
    token = "sfs_" + secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < now))
    db.add(UserSession(token_hash=token_hash(token), user_id=user.id,
                       expires_at=now + timedelta(days=settings.session_days)))
    db.flush()
    return token


def session_user(db, token: str) -> User | None:
    session = db.get(UserSession, token_hash(token))
    if session is None or session.expires_at <= datetime.now(UTC):
        return None
    return db.get(User, session.user_id)


def end_session(db, token: str):
    db.execute(delete(UserSession).where(UserSession.token_hash == token_hash(token)))
