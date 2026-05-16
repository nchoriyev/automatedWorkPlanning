# Generated manually for optional email + username login + role choices.

import django.contrib.auth.validators
from django.db import migrations, models
from django.db.models import Q


def populate_username_and_role(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    valid_roles = frozenset(
        {"specialist", "senior_specialist", "leading_specialist", "expert", "group_lead"}
    )
    for u in User.objects.all():
        if not u.username:
            email = u.email or ""
            base = email.split("@")[0] if "@" in email else email or "user"
            base = "".join(c if c.isalnum() or c in "._+-" else "_" for c in base).strip("._") or "user"
            base = base[:80]
            candidate = base
            suffix = 0
            while User.objects.filter(username=candidate).exclude(pk=u.pk).exists():
                suffix += 1
                candidate = f"{base}_{suffix}"
            u.username = candidate

        raw = (u.role or "").strip().lower().replace(" ", "_").replace("-", "_")
        if raw not in valid_roles:
            raw = "specialist"
        u.role = raw
        u.save(update_fields=["username", "role"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, max_length=254, verbose_name="email address"),
        ),
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(
                blank=True,
                help_text="Required to sign in. Letters, digits and @/./+/-/_ only.",
                max_length=150,
                null=True,
                validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                verbose_name="username",
            ),
        ),
        migrations.RunPython(populate_username_and_role, noop_reverse),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(
                help_text="Required to sign in. Letters, digits and @/./+/-/_ only.",
                max_length=150,
                unique=True,
                validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                verbose_name="username",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name="email address"),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                condition=Q(email__isnull=False),
                fields=("email",),
                name="accounts_user_email_unique_when_set",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("specialist", "Specialist"),
                    ("senior_specialist", "Senior specialist"),
                    ("leading_specialist", "Leading specialist"),
                    ("expert", "Expert"),
                    ("group_lead", "Group lead"),
                ],
                default="specialist",
                max_length=32,
                verbose_name="position / role",
            ),
        ),
    ]
