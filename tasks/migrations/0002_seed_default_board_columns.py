from django.db import migrations


DEFAULT_COLUMNS = [
    {"slug": "planned", "name": "", "order": 0, "is_active": True},
    {"slug": "in_progress", "name": "", "order": 1, "is_active": True},
    {"slug": "review", "name": "", "order": 2, "is_active": True},
    {"slug": "completed", "name": "", "order": 3, "is_active": True},
]


def seed_columns(apps, schema_editor):
    BoardColumn = apps.get_model("tasks", "BoardColumn")
    for row in DEFAULT_COLUMNS:
        BoardColumn.objects.get_or_create(slug=row["slug"], defaults=row)


def unseed_columns(apps, schema_editor):
    BoardColumn = apps.get_model("tasks", "BoardColumn")
    BoardColumn.objects.filter(slug__in=[r["slug"] for r in DEFAULT_COLUMNS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_columns, unseed_columns),
    ]
