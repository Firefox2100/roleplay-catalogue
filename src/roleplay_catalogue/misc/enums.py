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
    SILLY_TAVERN_PRESET = 'sillytavern/preset'
    IMAGE = 'core/image'
    WORLD_SIMULATION_WORLD = 'world-simulation-engine/world'


class ResourceVisibility(StrEnum):
    PUBLIC = 'public'
    AUTHENTICATED = 'authenticated'
    PRIVATE = 'private'


class ResourceLanguage(StrEnum):
    ENGLISH_UK = 'en-uk'
    CHINESE_SIMPLIFIED = 'zh-cn'
