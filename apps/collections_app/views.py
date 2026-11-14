from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from .models import Collection
from .serializers import CollectionSerializer


# Create your views here.
class CollectionViewSet(viewsets.ModelViewSet):
    queryset = Collection.objects.none()
    serializer_class = CollectionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Collection.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        serializer.save(owner=self.request.user)
