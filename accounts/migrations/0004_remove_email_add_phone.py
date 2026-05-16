# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_remove_user_department"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="user",
            name="accounts_user_email_unique_when_set",
        ),
        migrations.RemoveField(
            model_name="user",
            name="email",
        ),
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=32, verbose_name="phone number"),
        ),
    ]
