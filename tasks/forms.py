from django import forms
from django.db.models import Q
from .models import BoardColumn, Task


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
        from django.contrib.auth import get_user_model

        UserModel = get_user_model()
        self.fields["assigned_to"].queryset = UserModel.objects.filter(is_active=True).order_by(
            "full_name", "email"
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
    class Meta:
        model = BoardColumn
        fields = ("slug", "name", "order", "is_active")
        widgets = {
            "slug": forms.TextInput(attrs={"class": "mtms-input"}),
            "name": forms.TextInput(attrs={"class": "mtms-input"}),
            "order": forms.NumberInput(attrs={"class": "mtms-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "mtms-checkbox"}),
        }
