from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class BoardColumn(models.Model):
    """Kanban column — toggled by admins (`is_active`)."""

    slug = models.SlugField(
        _("slug"),
        max_length=64,
        unique=True,
        help_text=_("Stable key for translations (e.g. planned, in_progress)."),
    )
    name = models.CharField(_("display name override"), max_length=120, blank=True)
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    is_active = models.BooleanField(_("visible on board"), default=True)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = _("board column")
        verbose_name_plural = _("board columns")

    def __str__(self):
        return self.name or self.slug


class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_tasks",
        verbose_name=_("creator"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        verbose_name=_("assigned employee"),
    )
    priority = models.CharField(
        _("priority"),
        max_length=16,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    column = models.ForeignKey(
        BoardColumn,
        on_delete=models.PROTECT,
        related_name="tasks",
        verbose_name=_("column"),
    )
    due_date = models.DateField(_("due date"), null=True, blank=True)
    position = models.PositiveIntegerField(_("order in column"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ["column", "position", "-created_at"]
        verbose_name = _("task")
        verbose_name_plural = _("tasks")
        indexes = [
            models.Index(fields=["column", "position"]),
            models.Index(fields=["assigned_to", "column"]),
            models.Index(fields=["creator"]),
        ]

    def __str__(self):
        return self.title


class TaskAttachment(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("task"),
    )
    file = models.FileField(_("file"), upload_to="task_attachments/%Y/%m/")
    uploaded_at = models.DateTimeField(_("uploaded at"), auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = _("task attachment")
        verbose_name_plural = _("task attachments")
