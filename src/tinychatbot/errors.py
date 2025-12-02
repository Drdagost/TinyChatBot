class MissingConfigError(RuntimeError):
    """Raised when required configuration (environment variables) is missing.

    This allows callers to catch configuration-related errors explicitly instead
    of the process exiting abruptly.
    """

    pass
