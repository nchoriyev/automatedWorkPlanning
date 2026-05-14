from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from .models import User


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fname, field in self.fields.items():
            css = "mtms-input"
            if fname == "password":
                field.widget.attrs.setdefault("autocomplete", "current-password")
            if fname == User.USERNAME_FIELD:
                field.widget.attrs.setdefault("autocomplete", "email")
                field.label = _("Email")
            field.widget.attrs.setdefault("class", css)


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
        fields = ("email", "full_name", "role", "department")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "mtms-input"}),
            "full_name": forms.TextInput(attrs={"class": "mtms-input"}),
            "role": forms.TextInput(attrs={"class": "mtms-input"}),
            "department": forms.TextInput(attrs={"class": "mtms-input"}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("Passwords do not match."))
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("full_name", "role", "department", "avatar")
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "mtms-input"}),
            "role": forms.TextInput(attrs={"class": "mtms-input"}),
            "department": forms.TextInput(attrs={"class": "mtms-input"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "mtms-input-file"}),
        }
