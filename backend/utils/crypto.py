"""AES-256-GCM encryption/decryption for sensitive fields (auth_config)."""

import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt(data: str, key: bytes) -> str:
    """Encrypt a string with AES-256-GCM. Returns base64-encoded nonce+ciphertext."""
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes for AES-256")
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt(ciphertext_b64: str, key: bytes) -> str:
    """Decrypt AES-256-GCM ciphertext. Returns original plaintext string."""
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes for AES-256")
    raw = base64.b64decode(ciphertext_b64)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def derive_key(secret: str) -> bytes:
    """Derive a 32-byte key from the SECRET_KEY setting using SHA-256."""
    import hashlib
    return hashlib.sha256(secret.encode("utf-8")).digest()
