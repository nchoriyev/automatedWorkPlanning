from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import BoardColumn, BoardSettings, Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "description", "priority", "due_date", "assigned_to", "column")
        widgets = {
            "title": forms.TextInput(attrs={"class": "mtms-input"}),
            "description": forms.Textarea(attrs={"class": "mtms-input", "rows": 4}),
            "priority": forms.Select(attrs={"class": "mtms-input"}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "mtms-input"}),
            "assigned_to": forms.Select(attrs={"class": "mtms-input"}),
            "column": forms.Select(attrs={"class": "mtms-input"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        UserModel = get_user_model()
        self.fields["assigned_to"].queryset = UserModel.objects.filter(is_active=True).order_by(
            "full_name", "username"
        )
        self.fields["assigned_to"].required = False
        self.fields["column"].required = True

        col_qs = BoardColumn.objects.filter(is_active=True).order_by("order", "pk")
        if self.instance.pk and self.instance.column_id:
            col_qs = BoardColumn.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.column_id)
            ).order_by("order", "pk")
        self.fields["column"].queryset = col_qs


class AdminColumnForm(forms.ModelForm):
    """Dashboard form — slug is generated from name on save."""

    class Meta:
        model = BoardColumn
        fields = ("name", "order", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "mtms-input"}),
            "order": forms.NumberInput(attrs={"class": "mtms-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "mtms-checkbox"}),
        }


class BoardSettingsForm(forms.ModelForm):
    class Meta:
        model = BoardSettings
        fields = ("completed_column", "completed_retention_hours")
        widgets = {
            "completed_column": forms.Select(attrs={"class": "mtms-input"}),
            "completed_retention_hours": forms.NumberInput(
                attrs={"class": "mtms-input", "min": 1, "max": 8760}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["completed_column"].queryset = BoardColumn.objects.all().order_by("order", "pk")
        self.fields["completed_column"].required = False
        self.fields["completed_column"].label = _("Completed column")
        self.fields["completed_retention_hours"].label = _("Completed task retention (hours)")
