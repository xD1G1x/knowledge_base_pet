import logging
import time

from django.conf import settings

from ..documents_app.models import QuestionLog
from . import client
from .exceptions import AIError, AITimeoutError
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


def _safe_create_log(**kwargs) -> QuestionLog | None:
    """Создать QuestionLog, не падая при ошибке БД."""
    try:
        return QuestionLog.objects.create(**kwargs)
    except Exception:
        logger.exception(
            "Failed to create QuestionLog for document_id=%s",
            kwargs.get("document").pk if kwargs.get("document") else None,
        )
        return None


def _build_messages(document, question: str) -> list[dict]:
    """Собрать messages с обрезкой контекста документа."""
    content = document.content or ""
    context_limit = getattr(settings, "CONTEXT_CHAR_LIMIT", 10_000)
    context = content[:context_limit]
    if len(content) > context_limit:
        context += "…"

    user_prompt = USER_PROMPT_TEMPLATE.format(
        context=context,
        question=question,
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def _log_ok(
    document, question: str, response: dict, latency_ms: int, error_message: str = ""
) -> QuestionLog | None:
    return _safe_create_log(
        document=document,
        question=question,
        answer=response["answer"],
        status=QuestionLog.Status.OK,
        latency_ms=latency_ms,
        tokens_used=response.get("tokens_used"),
        error_message=error_message,
    )


def _log_error(
    document, question: str, status: str, latency_ms: int, error_message: str
) -> QuestionLog | None:
    return _safe_create_log(
        document=document,
        question=question,
        answer="",
        status=status,
        latency_ms=latency_ms,
        error_message=error_message[:500],
    )


def ask_document(document, question: str) -> tuple[str, QuestionLog | None]:
    messages = _build_messages(document, question)
    start_time = time.perf_counter()

    try:
        response = client.chat(messages)
    except AITimeoutError as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning("AI timeout for document_id=%s: %s", document.pk, exc)
        _log_error(document, question, QuestionLog.Status.TIMEOUT, latency_ms, str(exc))
        raise
    except AIError as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning("AI error for document_id=%s: %s", document.pk, exc)
        _log_error(document, question, QuestionLog.Status.ERROR, latency_ms, str(exc))
        raise

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    log = _log_ok(document, question, response, latency_ms)
    return response["answer"], log
