from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class BoardColumn(models.Model):
    """Kanban column — toggled by admins (`is_active`)."""

    slug = models.SlugField(
        _("slug"),
        max_length=64,
        unique=True,
        help_text=_("Stable key for translations (e.g. planned, in_progress). Left blank to derive from name."),
        blank=True,
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

    def save(self, *args, **kwargs):
        name = (self.name or "").strip()
        slug_in = (self.slug or "").strip()
        if name and not slug_in:
            self.slug = slugify(name)[:64] or "column"
        elif not slug_in:
            self.slug = "column"
        self.slug = (self.slug or "column")[:64]

        cls = type(self)
        qs = cls.objects.exclude(pk=self.pk) if self.pk else cls.objects.all()
        base = self.slug
        candidate = base
        n = 0
        while qs.filter(slug=candidate).exists():
            n += 1
            suffix = f"-{n}"
            max_base = max(1, 64 - len(suffix))
            candidate = base[:max_base] + suffix
        self.slug = candidate
        super().save(*args, **kwargs)


class BoardSettings(models.Model):
    """Singleton — completed column + auto-purge delay (single row, pk=1)."""

    completed_column = models.ForeignKey(
        BoardColumn,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Completed column"),
        help_text=_("Tasks moved here are archived to user history and removed after the retention period."),
    )
    completed_retention_hours = models.PositiveIntegerField(
        _("Completed task retention (hours)"),
        default=24,
        help_text=_("Tasks stay on the board in the completed column for this long, then are deleted (history is kept)."),
    )

    class Meta:
        verbose_name = _("Board settings")
        verbose_name_plural = _("Board settings")

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={"completed_retention_hours": 24},
        )
        return obj

    def __str__(self):
        return str(_("Board settings"))


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
    entered_completed_at = models.DateTimeField(
        _("entered completed column at"),
        null=True,
        blank=True,
        help_text=_("Set when the task first enters the configured completed column."),
    )
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
            models.Index(fields=["column", "entered_completed_at"]),
        ]

    def __str__(self):
        return self.title


class TaskHistory(models.Model):
    """Snapshot when a task enters the completed column (per user feed)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_history_entries",
        verbose_name=_("user"),
    )
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    priority = models.CharField(_("priority"), max_length=16)
    column_slug = models.CharField(_("column slug"), max_length=64)
    creator_display = models.CharField(_("creator"), max_length=255)
    assignee_display = models.CharField(_("Assignee snapshot"), max_length=255, blank=True)
    completed_at = models.DateTimeField(_("completed at"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at", "-pk"]
        verbose_name = _("task history entry")
        verbose_name_plural = _("task history")

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
