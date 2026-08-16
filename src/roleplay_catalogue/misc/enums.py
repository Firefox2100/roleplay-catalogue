from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = 'admin'
    USER = 'user'


class UserStatus(StrEnum):
    ACTIVE = 'active'
    PENDING_ACTIVATION = 'pendingActivation'
