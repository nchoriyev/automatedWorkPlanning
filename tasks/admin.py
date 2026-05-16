from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import BoardColumn, BoardSettings, Task, TaskAttachment, TaskHistory


class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0


@admin.register(BoardColumn)
class BoardColumnAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("slug", "name")
    ordering = ("order",)


@admin.register(BoardSettings)
class BoardSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "completed_column", "completed_retention_hours")

    def has_add_permission(self, request):
        return not BoardSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "priority", "column_slug", "completed_at")
    list_filter = ("column_slug",)
    search_fields = ("title", "description", "creator_display", "assignee_display")
    readonly_fields = ("created_at",)
    ordering = ("-completed_at",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "column",
        "priority",
        "creator",
        "assigned_to",
        "due_date",
        "entered_completed_at",
        "created_at",
    )
    list_filter = ("column", "priority", "created_at")
    search_fields = ("title", "description")
    autocomplete_fields = ("creator", "assigned_to", "column")
    readonly_fields = ("created_at", "updated_at")
    inlines = [TaskAttachmentInline]


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ("task", "file", "uploaded_at")
    search_fields = ("task__title",)
