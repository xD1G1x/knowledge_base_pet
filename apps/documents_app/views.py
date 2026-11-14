import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..ai.services import ask_document
from .filters import DocumentFilterSet
from .models import Document, QuestionLog
from .serializers import (
    AskSerializer,
    DocumentSerializer,
    QuestionLogSerializer,
)

logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.none()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter, SearchFilter, DjangoFilterBackend]
    filterset_class = DocumentFilterSet
    search_fields = ["title", "content"]
    ordering_fields = ["title", "created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Document.objects.select_related("collection").filter(
            owner=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(
        request=AskSerializer,
        responses={
            200: inline_serializer(
                name="AskResponse",
                fields={
                    "answer": serializers.CharField(),
                    "log": QuestionLogSerializer(allow_null=True),
                },
            ),
        },
    )
    @action(detail=True, methods=["post"], url_path="ask")
    def ask(self, request, pk=None):
        document = self.get_object()

        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data["question"]

        answer, log = ask_document(document, question)

        return Response(
            {
                "answer": answer,
                "log": QuestionLogSerializer(log).data if log else None,
            },
            status=status.HTTP_200_OK,
        )


class QuestionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QuestionLog.objects.none()
    serializer_class = QuestionLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter, SearchFilter, DjangoFilterBackend]
    filterset_fields = ["status", "document"]
    search_fields = ["question", "answer"]
    ordering_fields = ["status", "created_at", "tokens_used"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return QuestionLog.objects.select_related("document").filter(
            document__owner=self.request.user
        )
