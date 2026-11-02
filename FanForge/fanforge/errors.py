class FanForgeError(Exception):
    """Base error for deterministic generation failures."""


class ConfigError(FanForgeError):
    """Project configuration is incomplete or invalid."""


class ResourceConflictError(FanForgeError):
    """Two feature requirements cannot share the selected hardware resource."""
