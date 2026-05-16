from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError(_("The username must be set"))
        username = self.model.normalize_username(username)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self._create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SPECIALIST = "specialist", _("Specialist")
        SENIOR_SPECIALIST = "senior_specialist", _("Senior specialist")
        LEADING_SPECIALIST = "leading_specialist", _("Leading specialist")
        EXPERT = "expert", _("Expert")
        GROUP_LEAD = "group_lead", _("Group lead")

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_("Required to sign in. Letters, digits and @/./+/-/_ only."),
        validators=[UnicodeUsernameValidator()],
    )
    phone = models.CharField(_("Phone number"), max_length=32, blank=True, default="")
    full_name = models.CharField(_("full name"), max_length=255)
    role = models.CharField(
        _("position / role"),
        max_length=32,
        choices=Role.choices,
        default=Role.SPECIALIST,
    )
    avatar = models.ImageField(
        _("profile picture"),
        upload_to="avatars/",
        blank=True,
        null=True,
        help_text=_("Optional; default avatar is shown when empty."),
    )

    is_staff = models.BooleanField(_("staff status"), default=False)
    is_active = models.BooleanField(_("active"), default=True)

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.full_name or self.username
