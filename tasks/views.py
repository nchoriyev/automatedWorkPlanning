import json
from calendar import monthrange
from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import AdminColumnForm, TaskForm
from .models import BoardColumn, Task, TaskAttachment
from .permissions import permission_denied_message, user_can_edit_task


class BoardView(LoginRequiredMixin, TemplateView):
    template_name = "tasks/board.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        columns = BoardColumn.objects.filter(is_active=True).order_by("order", "pk")
        tasks_qs = (
            Task.objects.filter(column__in=columns)
            .select_related("creator", "assigned_to", "column")
            .prefetch_related("attachments")
            .order_by("position", "-created_at")
        )
        by_col = {c.id: [] for c in columns}
        for t in tasks_qs:
            if t.column_id in by_col:
                by_col[t.column_id].append(t)
        board_columns = []
        for c in columns:
            board_columns.append({"column": c, "tasks": by_col[c.id]})
        ctx["board_columns"] = board_columns
        ctx["columns"] = columns
        ctx["task_form"] = TaskForm(prefix="c", user=self.request.user)
        ctx["priority_choices"] = Task.Priority.choices
        UserModel = get_user_model()
        ctx["assignees"] = UserModel.objects.filter(is_active=True).order_by("full_name", "email")
        return ctx


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    http_method_names = ["post"]

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["prefix"] = "c"
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        form.instance.creator = self.request.user
        resp = super().form_valid(form)
        attach_key = form.add_prefix("attachments")
        for f in self.request.FILES.getlist(attach_key):
            TaskAttachment.objects.create(task=self.object, file=f)
        messages.success(self.request, _("Task created."))
        return resp

    def form_invalid(self, form):
        for err in form.non_field_errors():
            messages.error(self.request, err)
        for field, errs in form.errors.items():
            for e in errs:
                messages.error(self.request, f"{field}: {e}")
        return redirect("tasks:board")

    def get_success_url(self):
        return reverse("tasks:board")


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not user_can_edit_task(request.user, self.object):
            messages.error(request, permission_denied_message())
            return redirect("tasks:board")
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        resp = super().form_valid(form)
        for f in self.request.FILES.getlist("attachments"):
            TaskAttachment.objects.create(task=self.object, file=f)
        messages.success(self.request, _("Task updated."))
        return resp

    def form_invalid(self, form):
        for err in form.non_field_errors():
            messages.error(self.request, err)
        for field, errs in form.errors.items():
            for e in errs:
                messages.error(self.request, f"{field}: {e}")
        return redirect("tasks:board")

    def get_success_url(self):
        return reverse("tasks:board")


class TaskMoveView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode())
        except json.JSONDecodeError:
            return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

        task_id = payload.get("task_id")
        column_id = payload.get("column_id")
        ordered_ids = payload.get("ordered_ids")

        if task_id is None or column_id is None or not isinstance(ordered_ids, list):
            return JsonResponse({"ok": False, "error": "bad payload"}, status=400)

        task = Task.objects.filter(pk=task_id).select_related("column").first()
        if not task:
            return JsonResponse({"ok": False, "error": "not found"}, status=404)

        if not user_can_edit_task(request.user, task):
            return JsonResponse({"ok": False, "error": str(permission_denied_message())}, status=403)

        column = BoardColumn.objects.filter(pk=column_id, is_active=True).first()
        if not column:
            return JsonResponse({"ok": False, "error": "bad column"}, status=400)

        try:
            ids_int = [int(x) for x in ordered_ids]
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "bad ids"}, status=400)

        with transaction.atomic():
            task.column = column
            task.save(update_fields=["column", "updated_at"])
            for position, tid in enumerate(ids_int):
                Task.objects.filter(pk=tid, column=column).update(position=position)

        return JsonResponse({"ok": True})


class TaskDueCalendarMonthView(LoginRequiredMixin, View):
    """JSON: task counts per day of month (by due_date) on active board columns."""

    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        try:
            year = int(request.GET.get("year", date.today().year))
            month = int(request.GET.get("month", date.today().month))
        except (TypeError, ValueError):
            return JsonResponse({"error": "invalid"}, status=400)
        if month < 1 or month > 12 or year < 1970 or year > 2100:
            return JsonResponse({"error": "range"}, status=400)

        active = BoardColumn.objects.filter(is_active=True)
        rows = (
            Task.objects.filter(column__in=active, due_date__year=year, due_date__month=month)
            .values("due_date")
            .annotate(c=Count("id"))
        )
        counts = {str(row["due_date"].day): row["c"] for row in rows}
        first_weekday, days_in_month = monthrange(year, month)
        return JsonResponse(
            {
                "year": year,
                "month": month,
                "counts": counts,
                "days_in_month": days_in_month,
                "first_weekday_mon0": first_weekday,
            }
        )


class TaskDueCalendarDayView(LoginRequiredMixin, View):
    """JSON: tasks due on a single date."""

    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        raw = request.GET.get("date")
        if not raw:
            return JsonResponse({"error": "missing date"}, status=400)
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            return JsonResponse({"error": "invalid date"}, status=400)

        active = BoardColumn.objects.filter(is_active=True)
        tasks = (
            Task.objects.filter(column__in=active, due_date=d)
            .select_related("column")
            .order_by("title")
            .values("id", "title", "column__slug")
        )
        return JsonResponse({"date": raw, "tasks": list(tasks)})


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "tasks/admin_dashboard.html"
    raise_exception = False

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_staff or u.is_superuser)

    def handle_no_permission(self):
        messages.error(self.request, _("You do not have access to the admin dashboard."))
        return redirect("tasks:board")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        User = get_user_model()
        ctx["columns"] = BoardColumn.objects.all().order_by("order", "pk")
        ctx["stats"] = {
            "users": User.objects.count(),
            "tasks": Task.objects.count(),
            "attachments": TaskAttachment.objects.count(),
            "active_columns": BoardColumn.objects.filter(is_active=True).count(),
        }
        labels = dict(Task.Priority.choices)
        ctx["by_priority"] = [
            {"priority": labels[row["priority"]], "count": row["c"]}
            for row in Task.objects.values("priority").annotate(c=Count("id")).order_by("priority")
        ]
        ctx["column_form"] = AdminColumnForm()
        return ctx


class AdminColumnCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = BoardColumn
    form_class = AdminColumnForm
    http_method_names = ["post"]
    raise_exception = False

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_staff or u.is_superuser)

    def handle_no_permission(self):
        messages.error(self.request, _("You do not have access to this action."))
        return redirect("tasks:board")

    def form_valid(self, form):
        messages.success(self.request, _("Column saved."))
        return super().form_valid(form)

    def form_invalid(self, form):
        for field, errs in form.errors.items():
            for e in errs:
                messages.error(self.request, f"{field}: {e}")
        return redirect("tasks:admin_dashboard")

    def get_success_url(self):
        return reverse("tasks:admin_dashboard")
