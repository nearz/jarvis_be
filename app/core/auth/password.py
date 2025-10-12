from pwdlib import PasswordHash

# Use recommended settings (Argon2id by default)
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plain text password using Argon2id.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password string (includes salt and parameters)
    """
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password from the database

    Returns:
        True if password matches, False otherwise
    """
    return password_hash.verify(plain_password, hashed_password)


