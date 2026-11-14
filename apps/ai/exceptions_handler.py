from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .exceptions import (
    AIAuthError,
    AIBadRequestError,
    AIConnectionError,
    AIError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)

_STATUS_MAP = {
    AITimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
    AIConnectionError: status.HTTP_502_BAD_GATEWAY,
    AIRateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
    AIAuthError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    AIBadRequestError: status.HTTP_502_BAD_GATEWAY,
    AIProviderError: status.HTTP_502_BAD_GATEWAY,
}


def ai_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, AIError):
        for exc_type, http_status in _STATUS_MAP.items():
            if isinstance(exc, exc_type):
                return Response(
                    {"detail": str(exc)},
                    status=http_status,
                )
        return Response(
            {"detail": "AI service error."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return None
