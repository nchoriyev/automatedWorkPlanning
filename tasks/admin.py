from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import BoardColumn, Task, TaskAttachment


class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0


@admin.register(BoardColumn)
class BoardColumnAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("slug", "name")
    ordering = ("order",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "column", "priority", "creator", "assigned_to", "due_date", "created_at")
    list_filter = ("column", "priority", "created_at")
    search_fields = ("title", "description")
    autocomplete_fields = ("creator", "assigned_to", "column")
    readonly_fields = ("created_at", "updated_at")
    inlines = [TaskAttachmentInline]


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ("task", "file", "uploaded_at")
    search_fields = ("task__title",)
