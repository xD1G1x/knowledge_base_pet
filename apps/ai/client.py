import logging
import re
import time

import requests
from django.conf import settings

from .exceptions import (
    AIAuthError,
    AIBadRequestError,
    AIConnectionError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)

logger = logging.getLogger(__name__)


def _sanitize_error(message: str, api_key: str) -> str:
    if api_key:
        message = message.replace(api_key, "***")
    message = re.sub(r"sk-[A-Za-z0-9_-]{16,}", "***", message)  # OpenAI / Anthropic
    message = re.sub(r"gsk_[A-Za-z0-9]+", "***", message)  # Grok (xAI)
    message = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer ***", message)
    return message[:500]


def _check_http_status(resp: requests.Response, api_key: str | None = None) -> None:
    if 200 <= resp.status_code < 300:
        return

    logger.warning(
        "AI provider returned HTTP %s (body length=%d)",
        resp.status_code,
        len(resp.text or ""),
    )
    error_body = _sanitize_error(resp.text or "", api_key)[:200]
    message = f"AI provider returned HTTP {resp.status_code}: {error_body}"

    if resp.status_code in (401, 403):
        raise AIAuthError(message)
    if resp.status_code == 429:
        raise AIRateLimitError(message)
    if resp.status_code == 400:
        raise AIBadRequestError(message)
    raise AIProviderError(message)


def _post_json(
    url: str,
    headers: dict,
    payload: dict,
    connect_timeout: float,
    read_timeout: float,
    provider_name: str,
    api_key: str | None = None,
) -> dict:
    start = time.perf_counter()

    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=(connect_timeout, read_timeout),
        )
    except requests.Timeout as exc:
        raise AITimeoutError(f"{provider_name} request timed out") from exc
    except requests.ConnectionError as exc:
        raise AIConnectionError(f"Failed to connect to {provider_name}") from exc
    except requests.RequestException as exc:
        safe_message = _sanitize_error(str(exc), api_key)
        raise AIProviderError(
            f"{provider_name} HTTP request failed: {safe_message}"
        ) from exc

    latency = time.perf_counter() - start
    logger.debug("%s request completed in %.3f seconds", provider_name, latency)

    _check_http_status(resp, api_key)

    try:
        return resp.json()
    except ValueError as exc:
        raise AIProviderError(f"{provider_name} returned invalid JSON") from exc


def chat(messages: list, model: str | None = None) -> dict:

    url = settings.OLLAMA_URL
    model_name = model or settings.OLLAMA_MODEL

    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": getattr(settings, "OLLAMA_MAX_TOKENS", 1000),
            "temperature": getattr(settings, "OLLAMA_TEMPERATURE", 0.3),
        },
    }

    data = _post_json(
        url=url,
        headers=headers,
        payload=payload,
        connect_timeout=settings.OLLAMA_CONNECT_TIMEOUT,
        read_timeout=getattr(settings, "OLLAMA_READ_TIMEOUT", 120),
        provider_name="Ollama",
        api_key=None,
    )

    try:
        content = data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise AIProviderError("Ollama returned an unexpected response format") from exc

    if not isinstance(content, str):
        raise AIProviderError("Ollama returned a non-string message content")

    tokens_used = None
    if isinstance(data.get("prompt_eval_count"), int) or isinstance(
        data.get("eval_count"), int
    ):
        tokens_used = (data.get("prompt_eval_count") or 0) + (
            data.get("eval_count") or 0
        )

    return {"answer": content, "tokens_used": tokens_used, "raw": data}
