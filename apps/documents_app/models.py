from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from apps.collections_app.models import Collection


class Document(models.Model):
    title = models.CharField(
        max_length=255,
    )
    content = models.TextField()
    collection = models.ForeignKey(
        Collection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["owner", "collection"]),
            models.Index(fields=["title"]),
        ]

    def clean(self):
        super().clean()
        if (
            self.collection_id
            and self.owner_id
            and self.collection.owner_id != self.owner_id
        ):
            raise ValidationError(
                {"collection": "Коллекция принадлежит другому пользователю."}
            )

    def __str__(self) -> str:
        return self.title or f"Document #{self.pk}"


class QuestionLog(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="question_logs"
    )
    question = models.TextField()
    answer = models.TextField()

    class Status(models.TextChoices):
        OK = "ok", "OK"
        ERROR = "error", "Error"
        TIMEOUT = "timeout", "Timeout"

    status = models.CharField(choices=Status.choices, default=Status.OK, max_length=10)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    latency_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["document", "-created_at"])]

    def __str__(self) -> str:
        return f"Q#{self.pk} → doc#{self.document_id}"
