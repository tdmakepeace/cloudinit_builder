"""Password hashing compatible with mkpasswd --method=SHA-512 (libcrypt $6$)."""

from __future__ import annotations

from passlib.hash import sha512_crypt


def hash_plain_password_sha512(plain: str) -> str:
    """Return a SHA-512 crypt hash string suitable for cloud-init/subiquity identity.password."""
    return sha512_crypt.hash(plain)
