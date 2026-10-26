from django.contrib import admin

from .models import Document, QuestionLog

# Register your models here.

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "content_preview","collection", "owner", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "content", "owner__username", "collection__name")
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("collection", "owner")
    
    @admin.display(description="Content preview")
    def content_preview(self, obj: Document) -> str:
        content = obj.content or ""
        return content[:80] + ("…" if len(content) > 80 else "")
    
@admin.register(QuestionLog)
class QuestionLogAdmin(admin.ModelAdmin):
    llist_display = ("id", "document", "status", "created_at", "tokens_used", "latency_ms")
    list_filter = ("status", "created_at")
    search_fields = ("question", "answer", "document__title")
    list_select_related = ("document",)
    date_hierarchy = "created_at"
    list_per_page = 50
    
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True   # удалять иногда полезно (чистка мусора)

    def get_readonly_fields(self, request, obj=None):
        # все поля read-only, включая document
        return [f.name for f in self.model._meta.fields]