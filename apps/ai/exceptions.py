class AIError(Exception):
    """Base exception for all AI provider errors."""


class AITimeoutError(AIError):
    """Raised when the AI provider request times out."""


class AIConnectionError(AIError):
    """Raised when a connection to the AI provider fails."""


class AIAuthError(AIError):
    """Raised when authentication with the AI provider fails."""


class AIRateLimitError(AIError):
    """Raised when the AI provider rate limit is exceeded."""


class AIProviderError(AIError):
    """Raised when the AI provider returns an unexpected error."""


class AIBadRequestError(AIError):
    """Raised when the request sent to the AI provider is invalid."""
