import re


PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

_LOWERCASE = re.compile(r'[a-z]')
_UPPERCASE = re.compile(r'[A-Z]')
_DIGIT = re.compile(r'[0-9]')
_SPECIAL = re.compile(r'[^A-Za-z0-9]')


def password_strength_error(password: str) -> str | None:
    """Return a description of the first unmet password complexity rule, or None if it passes.

    Length is intentionally not checked here; callers already enforce
    PASSWORD_MIN_LENGTH/PASSWORD_MAX_LENGTH via Pydantic Field constraints.
    """
    if not _LOWERCASE.search(password):
        return 'Password must contain at least one lowercase letter'
    if not _UPPERCASE.search(password):
        return 'Password must contain at least one uppercase letter'
    if not _DIGIT.search(password):
        return 'Password must contain at least one number'
    if not _SPECIAL.search(password):
        return 'Password must contain at least one special character'
    return None
