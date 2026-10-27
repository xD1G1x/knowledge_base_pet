from rest_framework import serializers

from .models import Collection
from .models import Document, QuestionLog


class DocumentSerializer(serializers.ModelSerializer):
    CONTENT_CHAR_LIMIT = 50_000

    class Meta:
        model = Document
        fields = (
            "id",
            "title",
            "content",
            "collection",
            "owner",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "owner")

    def validate_title(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("Title is empty.")
        return value

    def validate_content(self, value: str) -> str:
        if len(value) > self.CONTENT_CHAR_LIMIT:
            raise serializers.ValidationError(
                f"Exceeded content char limit "
                f"(max: {self.CONTENT_CHAR_LIMIT}, current: {len(value)})."
            )
        if not value.strip():
            raise serializers.ValidationError("Content is empty.")
        return value

    def validate_collection(self, value: Collection | None) -> Collection | None:
        if value is None:
            return value

        request = self.context.get("request")
        if request is None:
            raise serializers.ValidationError(
                "Request context is required to validate collection ownership."
            )

        if value.owner_id != request.user.id:
            raise serializers.ValidationError(
                "You are not the owner of this collection."
            )
        return value


class QuestionLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = QuestionLog
        fields = (
            "id",
            "document",
            "question",
            "answer",
            "status",
            "error_message",
            "created_at",
            "tokens_used",
            "latency_ms",
        )
        read_only_fields = fields


class AskSerializer(serializers.Serializer):

    QUESTION_CHAR_LIMIT = 50_000

    question = serializers.CharField(
        max_length=QUESTION_CHAR_LIMIT,
        trim_whitespace=True,
        allow_blank=False,
    )