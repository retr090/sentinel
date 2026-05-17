import os
from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.getenv("FORUM_ENCRYPTION_KEY", "")
    if not key:
        raise ValueError("FORUM_ENCRYPTION_KEY not set in environment")
    return Fernet(key.encode())


def encrypt_password(password: str) -> str:
    return _get_fernet().encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


def is_encrypted(value: str) -> bool:
    try:
        return value.startswith("gAAAAA")
    except Exception:
        return False
