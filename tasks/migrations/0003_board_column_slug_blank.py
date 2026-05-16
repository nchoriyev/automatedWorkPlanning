# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0002_seed_default_board_columns"),
    ]

    operations = [
        migrations.AlterField(
            model_name="boardcolumn",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="Stable key for translations (e.g. planned, in_progress). Left blank to derive from name.",
                max_length=64,
                unique=True,
                verbose_name="slug",
            ),
        ),
    ]
