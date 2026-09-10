from cryptography.fernet import Fernet

from core.config import settings


def _fernet() -> Fernet:
    if not settings.FERNET_SECRET_KEY:
        raise RuntimeError("FERNET_SECRET_KEY is not set — cannot encrypt/decrypt stored tokens.")
    return Fernet(settings.FERNET_SECRET_KEY.encode("utf-8"))


def encrypt_token(raw_token: str) -> str:
    return _fernet().encrypt(raw_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    return _fernet().decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
