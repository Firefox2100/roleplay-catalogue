from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = 'admin'
    USER = 'user'


class UserStatus(StrEnum):
    ACTIVE = 'active'
    PENDING_ACTIVATION = 'pendingActivation'


class ResourceType(StrEnum):
    SILLY_TAVERN_CHARACTER = 'sillytavern/character'
    SILLY_TAVERN_LOREBOOK = 'sillytavern/lorebook'
    IMAGE = 'core/image'


class ResourceVisibility(StrEnum):
    PUBLIC = 'public'
    AUTHENTICATED = 'authenticated'
    PRIVATE = 'private'
