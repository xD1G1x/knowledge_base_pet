from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Document, QuestionLog
from .serializers import DocumentSerializer, QuestionLogSerializer
from .filters import DocumentFilterSet



# Create your views here.
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter, SearchFilter, DjangoFilterBackend]
    filterset_class = DocumentFilterSet
    search_fields = ["title", "content"]
    ordering_fields = ["title", "created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Document.objects
            .select_related("collection")
            .filter(owner=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        
    def perform_update(self, serializer):
        serializer.save(owner=self.request.user)


class QuestionLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuestionLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter, SearchFilter, DjangoFilterBackend]
    filterset_fields = ["status", "document"]
    search_fields = ["question", "answer"]
    ordering_fields = ["status", "created_at", "tokens_used"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            QuestionLog.objects
            .select_related("document")
            .filter(document__owner=self.request.user)
        )
