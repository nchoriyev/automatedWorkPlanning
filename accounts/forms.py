from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from .models import User
from .utils import allocate_username_from_full_name


class LoginForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": _("Please enter a correct full name and password."),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fname, field in self.fields.items():
            css = "mtms-input"
            if fname == "password":
                field.widget.attrs.setdefault("autocomplete", "current-password")
            if fname == User.USERNAME_FIELD:
                field.widget.attrs.setdefault("autocomplete", "name")
                field.label = _("Full name")
            field.widget.attrs.setdefault("class", css)

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                try:
                    u = User.objects.get(full_name__iexact=username.strip())
                    self.user_cache = authenticate(self.request, username=u.username, password=password)
                except User.DoesNotExist:
                    pass
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"class": "mtms-input"}),
    )
    password2 = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(attrs={"class": "mtms-input"}),
    )

    class Meta:
        model = User
        fields = ("full_name", "role", "phone")
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "mtms-input", "autocomplete": "name"}),
            "role": forms.Select(attrs={"class": "mtms-input"}),
            "phone": forms.TextInput(attrs={"class": "mtms-input", "autocomplete": "tel", "inputmode": "tel"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].required = False

    def clean_full_name(self):
        name = (self.cleaned_data.get("full_name") or "").strip()
        if not name:
            raise forms.ValidationError(_("This field is required."))
        if User.objects.filter(full_name__iexact=name).exists():
            raise forms.ValidationError(_("An account with this full name already exists."))
        return name

    def clean_phone(self):
        value = (self.cleaned_data.get("phone") or "").strip()
        return value or ""

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("Passwords do not match."))
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = allocate_username_from_full_name(user.full_name)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("full_name", "phone", "role", "avatar")
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "mtms-input"}),
            "phone": forms.TextInput(attrs={"class": "mtms-input", "autocomplete": "tel", "inputmode": "tel"}),
            "role": forms.Select(attrs={"class": "mtms-input"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "mtms-input-file"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].required = False

    def clean_full_name(self):
        name = (self.cleaned_data.get("full_name") or "").strip()
        if not name:
            raise forms.ValidationError(_("This field is required."))
        qs = User.objects.filter(full_name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("An account with this full name already exists."))
        return name

    def clean_phone(self):
        value = (self.cleaned_data.get("phone") or "").strip()
        return value or ""

    def save(self, commit=True):
        user = super().save(commit=False)
        prior_name = (self.initial.get("full_name") or "").strip()
        if prior_name != (user.full_name or "").strip():
            user.username = allocate_username_from_full_name(user.full_name, exclude_pk=user.pk)
        if commit:
            user.save()
        return user
