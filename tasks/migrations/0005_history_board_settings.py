# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_board_settings(apps, schema_editor):
    BoardColumn = apps.get_model("tasks", "BoardColumn")
    BoardSettings = apps.get_model("tasks", "BoardSettings")
    BoardSettings.objects.get_or_create(pk=1, defaults={"completed_retention_hours": 24})
    row = BoardSettings.objects.get(pk=1)
    col = BoardColumn.objects.filter(slug="completed").first()
    if col and row.completed_column_id != col.pk:
        row.completed_column_id = col.pk
        row.save(update_fields=["completed_column_id"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0003_board_column_slug_blank"),
    ]

    operations = [
        migrations.CreateModel(
            name="BoardSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "completed_retention_hours",
                    models.PositiveIntegerField(
                        default=24,
                        help_text="Tasks stay on the board in the completed column for this long, then are deleted (history is kept).",
                        verbose_name="Completed task retention (hours)",
                    ),
                ),
                (
                    "completed_column",
                    models.ForeignKey(
                        blank=True,
                        help_text="Tasks moved here are archived to user history and removed after the retention period.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="tasks.boardcolumn",
                        verbose_name="Completed column",
                    ),
                ),
            ],
            options={
                "verbose_name": "Board settings",
                "verbose_name_plural": "Board settings",
            },
        ),
        migrations.CreateModel(
            name="TaskHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="title")),
                ("description", models.TextField(blank=True, verbose_name="description")),
                ("priority", models.CharField(max_length=16, verbose_name="priority")),
                ("column_slug", models.CharField(max_length=64, verbose_name="column slug")),
                ("creator_display", models.CharField(max_length=255, verbose_name="creator")),
                ("assignee_display", models.CharField(blank=True, max_length=255, verbose_name="Assignee snapshot")),
                ("completed_at", models.DateTimeField(verbose_name="completed at")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_history_entries",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={
                "verbose_name": "task history entry",
                "verbose_name_plural": "task history",
                "ordering": ["-completed_at", "-pk"],
            },
        ),
        migrations.AddField(
            model_name="task",
            name="entered_completed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Set when the task first enters the configured completed column.",
                null=True,
                verbose_name="entered completed column at",
            ),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["column", "entered_completed_at"], name="tasks_task_col_ent_idx"),
        ),
        migrations.RunPython(seed_board_settings, noop_reverse),
    ]
