from unittest import mock

from django.test import TestCase, override_settings

from ..documents_app.models import QuestionLog
from . import client, exceptions_handler, services
from .exceptions import (
    AIAuthError,
    AIBadRequestError,
    AIConnectionError,
    AIError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)


class SanitizeErrorTests(TestCase):
    def test_sanitize_error_masks_openai_key(self):
        message = "Error with sk-abcdefghijklmnopqrstuvwxyz key"
        result = client._sanitize_error(message, "sk-abcdefghijklmnopqrstuvwxyz")
        self.assertIn("***", result)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz", result)

    def test_sanitize_error_masks_grok_key(self):
        message = "Error with gsk_abc123 key"
        result = client._sanitize_error(message, "gsk_abc123")
        self.assertIn("***", result)
        self.assertNotIn("gsk_abc123", result)

    def test_sanitize_error_masks_bearer_token(self):
        message = "Authorization Bearer abcdef1234567890 failed"
        result = client._sanitize_error(message, None)
        self.assertIn("Bearer ***", result)

    def test_sanitize_error_truncates_long_messages(self):
        message = "x" * 1000
        result = client._sanitize_error(message, None)
        self.assertEqual(len(result), 500)

    def test_sanitize_error_empty_api_key(self):
        message = "simple error"
        result = client._sanitize_error(message, None)
        self.assertEqual(result, "simple error")


class CheckHttpStatusTests(TestCase):
    def test_check_http_status_success(self):
        resp = mock.Mock(spec=["status_code", "text"])
        resp.status_code = 200
        resp.text = "{}"
        client._check_http_status(resp, None)

    def test_check_http_status_401_raises_auth_error(self):
        resp = mock.Mock(spec=["status_code", "text"])
        resp.status_code = 401
        resp.text = "Unauthorized"
        with self.assertRaises(AIAuthError):
            client._check_http_status(resp, None)

    def test_check_http_status_403_raises_auth_error(self):
        resp = mock.Mock(spec=["status_code", "text"])
        resp.status_code = 403
        resp.text = "Forbidden"
        with self.assertRaises(AIAuthError):
            client._check_http_status(resp, None)

    def test_check_http_status_429_raises_rate_limit(self):
        resp = mock.Mock(spec=["status_code", "text"])
        resp.status_code = 429
        resp.text = "Too Many Requests"
        with self.assertRaises(AIRateLimitError):
            client._check_http_status(resp, None)

    def test_check_http_status_400_raises_bad_request(self):
        resp = mock.Mock(spec=["status_code", "text"])
        resp.status_code = 400
        resp.text = "Bad Request"
        with self.assertRaises(AIBadRequestError):
            client._check_http_status(resp, None)

    def test_check_http_status_500_raises_provider_error(self):
        resp = mock.Mock(spec=["status_code", "text"])
        resp.status_code = 500
        resp.text = "Internal Server Error"
        with self.assertRaises(AIProviderError):
            client._check_http_status(resp, None)


class PostJsonTests(TestCase):
    @mock.patch("requests.post")
    def test_post_json_success(self, mock_post):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        mock_resp.text = '{"answer": "hello"}'
        mock_resp.json.return_value = {"answer": "hello"}
        mock_post.return_value = mock_resp

        result = client._post_json(
            url="http://example.com",
            headers={"Content-Type": "application/json"},
            payload={"model": "llama3.1"},
            connect_timeout=5.0,
            read_timeout=30.0,
            provider_name="Ollama",
            api_key=None,
        )
        self.assertEqual(result, {"answer": "hello"})
        mock_post.assert_called_once()

    @mock.patch("requests.post")
    def test_post_json_timeout(self, mock_post):
        mock_post.side_effect = __import__("requests").Timeout("timed out")
        with self.assertRaises(AITimeoutError):
            client._post_json(
                url="http://example.com",
                headers={},
                payload={},
                connect_timeout=5.0,
                read_timeout=30.0,
                provider_name="Ollama",
            )

    @mock.patch("requests.post")
    def test_post_json_connection_error(self, mock_post):
        mock_post.side_effect = __import__("requests").ConnectionError("conn fail")
        with self.assertRaises(AIConnectionError):
            client._post_json(
                url="http://example.com",
                headers={},
                payload={},
                connect_timeout=5.0,
                read_timeout=30.0,
                provider_name="Ollama",
            )

    @mock.patch("requests.post")
    def test_post_json_invalid_json(self, mock_post):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        mock_resp.text = "not json"
        mock_resp.json.side_effect = ValueError("invalid")
        mock_post.return_value = mock_resp
        with self.assertRaises(AIProviderError):
            client._post_json(
                url="http://example.com",
                headers={},
                payload={},
                connect_timeout=5.0,
                read_timeout=30.0,
                provider_name="Ollama",
            )


class ChatTests(TestCase):
    @override_settings(
        OLLAMA_URL="http://localhost:11434/api/chat",
        OLLAMA_MODEL="llama3.1",
        OLLAMA_CONNECT_TIMEOUT=5.0,
        OLLAMA_READ_TIMEOUT=30.0,
        OLLAMA_MAX_TOKENS=500,
        OLLAMA_TEMPERATURE=0.7,
    )
    @mock.patch("apps.ai.client._post_json")
    def test_chat_success(self, mock_post_json):
        mock_post_json.return_value = {
            "message": {"content": "The answer"},
            "prompt_eval_count": 10,
            "eval_count": 20,
        }
        messages = [{"role": "user", "content": "Hello"}]
        result = client.chat(messages, model="llama3.1")

        self.assertEqual(result["answer"], "The answer")
        self.assertEqual(result["tokens_used"], 30)
        self.assertEqual(result["raw"]["prompt_eval_count"], 10)

        call_args = mock_post_json.call_args
        self.assertEqual(call_args.kwargs["url"], "http://localhost:11434/api/chat")
        self.assertEqual(call_args.kwargs["provider_name"], "Ollama")
        self.assertIsNone(call_args.kwargs["api_key"])
        self.assertEqual(call_args.kwargs["connect_timeout"], 5.0)
        self.assertEqual(call_args.kwargs["read_timeout"], 30.0)
        payload = call_args.kwargs["payload"]
        self.assertEqual(payload["model"], "llama3.1")
        self.assertEqual(payload["messages"], messages)
        self.assertEqual(payload["stream"], False)
        self.assertEqual(payload["options"]["num_predict"], 500)
        self.assertEqual(payload["options"]["temperature"], 0.7)

    @override_settings(
        OLLAMA_URL="http://localhost:11434/api/chat",
        OLLAMA_MODEL="llama3.1",
        OLLAMA_CONNECT_TIMEOUT=5.0,
        OLLAMA_READ_TIMEOUT=30.0,
    )
    @mock.patch("apps.ai.client._post_json")
    def test_chat_no_api_key_not_required(self, mock_post_json):
        mock_post_json.return_value = {
            "message": {"content": "ok"},
            "prompt_eval_count": 1,
            "eval_count": 2,
        }
        result = client.chat([{"role": "user", "content": "Hello"}])

        self.assertEqual(result["answer"], "ok")
        self.assertIsNone(mock_post_json.call_args.kwargs["api_key"])

    @override_settings(
        OLLAMA_URL="http://localhost:11434/api/chat",
        OLLAMA_MODEL="llama3.1",
        OLLAMA_CONNECT_TIMEOUT=5.0,
        OLLAMA_READ_TIMEOUT=30.0,
    )
    @mock.patch("apps.ai.client._post_json")
    def test_chat_unexpected_format_raises(self, mock_post_json):
        mock_post_json.return_value = {"unexpected": "format"}
        with self.assertRaises(AIProviderError):
            client.chat([{"role": "user", "content": "Hello"}])

    @override_settings(
        OLLAMA_URL="http://localhost:11434/api/chat",
        OLLAMA_MODEL="llama3.1",
        OLLAMA_CONNECT_TIMEOUT=5.0,
        OLLAMA_READ_TIMEOUT=30.0,
    )
    @mock.patch("apps.ai.client._post_json")
    def test_chat_non_string_content_raises(self, mock_post_json):
        mock_post_json.return_value = {"message": {"content": 123}}
        with self.assertRaises(AIProviderError):
            client.chat([{"role": "user", "content": "Hello"}])


class SafeCreateLogTests(TestCase):
    @mock.patch("apps.ai.services.QuestionLog.objects.create")
    def test_safe_create_log_success(self, mock_create):
        mock_log = mock.Mock()
        mock_create.return_value = mock_log
        result = services._safe_create_log(document=mock.Mock(), question="Q")
        self.assertEqual(result, mock_log)
        mock_create.assert_called_once()

    @mock.patch("apps.ai.services.QuestionLog.objects.create")
    def test_safe_create_log_db_error_returns_none(self, mock_create):
        mock_create.side_effect = Exception("DB error")
        result = services._safe_create_log(document=mock.Mock(), question="Q")
        self.assertIsNone(result)


class AskDocumentTests(TestCase):
    def setUp(self):
        self.document = mock.Mock()
        self.document.content = "The capital of France is Paris."
        self.document.pk = 1
        self.question = "What is the capital of France?"

    @mock.patch("apps.ai.services.client.chat")
    @mock.patch("apps.ai.services._safe_create_log")
    def test_ask_document_success(self, mock_safe_log, mock_chat):
        mock_chat.return_value = {
            "answer": "Paris",
            "tokens_used": 10,
            "raw": {},
        }
        mock_log = mock.Mock()
        mock_log.pk = 1
        mock_safe_log.return_value = mock_log

        answer, log = services.ask_document(self.document, self.question)

        self.assertEqual(answer, "Paris")
        self.assertEqual(log, mock_log)
        mock_chat.assert_called_once()
        call_args = mock_chat.call_args[0][0]
        self.assertEqual(call_args[0]["role"], "system")
        self.assertEqual(call_args[1]["role"], "user")
        self.assertIn(self.question, call_args[1]["content"])
        mock_safe_log.assert_called_once()
        log_kwargs = mock_safe_log.call_args.kwargs
        self.assertEqual(log_kwargs["status"], QuestionLog.Status.OK)
        self.assertEqual(log_kwargs["tokens_used"], 10)

    @mock.patch("apps.ai.services.client.chat")
    @mock.patch("apps.ai.services._safe_create_log")
    def test_ask_document_context_truncation(self, mock_safe_log, mock_chat):
        mock_chat.return_value = {
            "answer": "Paris",
            "tokens_used": 5,
            "raw": {},
        }
        mock_log = mock.Mock()
        mock_log.pk = 1
        mock_safe_log.return_value = mock_log

        long_content = "x" * 20000
        self.document.content = long_content
        with override_settings(CONTEXT_CHAR_LIMIT=10000):
            services.ask_document(self.document, self.question)

        call_args = mock_chat.call_args[0][0]
        user_content = call_args[1]["content"]
        self.assertLessEqual(len(user_content), 10000 + len(self.question) + 50)
        self.assertIn("…", user_content)

    @mock.patch("apps.ai.services.client.chat")
    @mock.patch("apps.ai.services._safe_create_log")
    def test_ask_document_timeout(self, mock_safe_log, mock_chat):
        mock_chat.side_effect = AITimeoutError("timed out")
        mock_log = mock.Mock()
        mock_log.pk = 1
        mock_safe_log.return_value = mock_log

        with self.assertRaises(AITimeoutError):
            services.ask_document(self.document, self.question)

        mock_safe_log.assert_called_once()
        log_kwargs = mock_safe_log.call_args.kwargs
        self.assertEqual(log_kwargs["status"], QuestionLog.Status.TIMEOUT)
        self.assertEqual(log_kwargs["answer"], "")

    @mock.patch("apps.ai.services.client.chat")
    @mock.patch("apps.ai.services._safe_create_log")
    def test_ask_document_ai_error(self, mock_safe_log, mock_chat):
        mock_chat.side_effect = AIProviderError("provider error")
        mock_log = mock.Mock()
        mock_log.pk = 1
        mock_safe_log.return_value = mock_log

        with self.assertRaises(AIError):
            services.ask_document(self.document, self.question)

        mock_safe_log.assert_called_once()
        log_kwargs = mock_safe_log.call_args.kwargs
        self.assertEqual(log_kwargs["status"], QuestionLog.Status.ERROR)
        self.assertEqual(log_kwargs["answer"], "")


class ExceptionHandlerTests(TestCase):
    def test_ai_timeout_maps_to_504(self):
        exc = AITimeoutError("gateway timeout")
        response = exceptions_handler.ai_exception_handler(exc, {})
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.data["detail"], "gateway timeout")

    def test_ai_connection_error_maps_to_502(self):
        exc = AIConnectionError("connection failed")
        response = exceptions_handler.ai_exception_handler(exc, {})
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 502)

    def test_ai_rate_limit_maps_to_429(self):
        exc = AIRateLimitError("rate limited")
        response = exceptions_handler.ai_exception_handler(exc, {})
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 429)

    def test_ai_auth_error_maps_to_500(self):
        exc = AIAuthError("auth failed")
        response = exceptions_handler.ai_exception_handler(exc, {})
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 500)

    def test_ai_bad_request_maps_to_502(self):
        exc = AIBadRequestError("bad request")
        response = exceptions_handler.ai_exception_handler(exc, {})
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 502)

    def test_ai_provider_error_maps_to_502(self):
        exc = AIProviderError("provider error")
        response = exceptions_handler.ai_exception_handler(exc, {})
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 502)

    def test_unknown_exception_returns_none(self):
        exc = ValueError("not an AI error")
        response = exceptions_handler.ai_exception_handler(exc, {})
        self.assertIsNone(response)
