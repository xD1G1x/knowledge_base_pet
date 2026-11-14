from django_filters.rest_framework import FilterSet, NumberFilter
from rest_framework.exceptions import ValidationError

from apps.collections_app.models import Collection

from .models import Document


class DocumentFilterSet(FilterSet):
    collection = NumberFilter(method="filter_collection")

    class Meta:
        model = Document
        fields = []

    def filter_collection(self, queryset, name, value):
        if value is None:
            return queryset

        request = getattr(self, "request", None)
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            raise ValidationError("Authentication required.")

        collection = Collection.objects.filter(pk=value, owner=user).first()
        if not collection:
            raise ValidationError("Collection not found.")

        return queryset.filter(collection_id=value)
