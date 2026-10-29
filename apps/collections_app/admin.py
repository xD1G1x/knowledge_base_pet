from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from .models import Collection

# Register your models here.


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "docs_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "owner__username")
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("owner",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Collection]:
        return super().get_queryset(request).annotate(_docs_count=Count("documents"))

    @admin.display(description="Documents", ordering="_docs_count")
    def docs_count(self, obj):
        return getattr(obj, "_docs_count", 0)
