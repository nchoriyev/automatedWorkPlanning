import json
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import AdminColumnForm, BoardSettingsForm, TaskForm
from .models import BoardColumn, BoardSettings, Task, TaskAttachment, TaskHistory
from .permissions import (
    permission_denied_message,
    tasks_visible_for_user,
    user_can_edit_task,
    user_can_view_task,
)
from .services import handle_completed_column_transition, purge_completed_tasks


def _board_redirect(request):
    url = reverse("tasks:board")
    if request.user.is_staff or request.user.is_superuser:
        bu = request.POST.get("board_user") or request.GET.get("board_user")
        if bu:
            url += f"?board_user={bu}"
    return redirect(url)


class BoardView(LoginRequiredMixin, TemplateView):
    template_name = "tasks/board.html"

    def dispatch(self, request, *args, **kwargs):
        purge_completed_tasks()
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            request.session["board_query_user"] = request.GET.get("board_user", "")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        columns = BoardColumn.objects.filter(is_active=True).order_by("order", "pk")
        tasks_qs = (
            Task.objects.filter(column__in=columns)
            .select_related("creator", "assigned_to", "column")
            .prefetch_related("attachments")
            .order_by("position", "-created_at")
        )
        staff_filter = None
        board_filter_user_id = None
        if self.request.user.is_staff or self.request.user.is_superuser:
            raw = self.request.GET.get("board_user")
            if raw:
                try:
                    board_filter_user_id = int(raw)
                    staff_filter = raw
                except ValueError:
                    board_filter_user_id = None

        tasks_qs = tasks_visible_for_user(tasks_qs, self.request.user, staff_filter)

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
        ctx["assignees"] = UserModel.objects.filter(is_active=True).order_by("full_name", "username")
        ctx["board_filter_users"] = UserModel.objects.filter(is_active=True).order_by("full_name", "username")
        ctx["board_filter_user_id"] = board_filter_user_id
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
        column = form.cleaned_data["column"]
        agg = Task.objects.filter(column=column).aggregate(m=Max("position"))
        max_pos = agg["m"]
        form.instance.position = (max_pos + 1) if max_pos is not None else 0
        old_column_id = None
        resp = super().form_valid(form)
        attach_key = form.add_prefix("attachments")
        for f in self.request.FILES.getlist(attach_key):
            TaskAttachment.objects.create(task=self.object, file=f)
        self.object.refresh_from_db()
        handle_completed_column_transition(self.object, old_column_id)
        messages.success(self.request, _("Task created."))
        return resp

    def form_invalid(self, form):
        for err in form.non_field_errors():
            messages.error(self.request, err)
        for field, errs in form.errors.items():
            for e in errs:
                messages.error(self.request, f"{field}: {e}")
        return _board_redirect(self.request)

    def get_success_url(self):
        url = reverse("tasks:board")
        if self.request.user.is_staff or self.request.user.is_superuser:
            bu = self.request.POST.get("board_user")
            if bu:
                url += f"?board_user={bu}"
        return url


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not user_can_view_task(request.user, self.object):
            raise Http404()
        if not user_can_edit_task(request.user, self.object):
            messages.error(request, permission_denied_message())
            return _board_redirect(request)
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        old_column_id = self.object.column_id
        resp = super().form_valid(form)
        for f in self.request.FILES.getlist("attachments"):
            TaskAttachment.objects.create(task=self.object, file=f)
        self.object.refresh_from_db()
        handle_completed_column_transition(self.object, old_column_id)
        messages.success(self.request, _("Task updated."))
        return resp

    def form_invalid(self, form):
        for err in form.non_field_errors():
            messages.error(self.request, err)
        for field, errs in form.errors.items():
            for e in errs:
                messages.error(self.request, f"{field}: {e}")
        return _board_redirect(self.request)

    def get_success_url(self):
        url = reverse("tasks:board")
        if self.request.user.is_staff or self.request.user.is_superuser:
            bu = self.request.POST.get("board_user")
            if bu:
                url += f"?board_user={bu}"
        return url


class TaskDetailView(LoginRequiredMixin, View):
    template_name = "tasks/task_detail.html"

    def _task(self, pk):
        return get_object_or_404(
            Task.objects.select_related("creator", "assigned_to", "column").prefetch_related("attachments"),
            pk=pk,
        )

    def _board_back_url(self, request):
        url = reverse("tasks:board")
        if request.user.is_staff or request.user.is_superuser:
            bq = request.session.get("board_query_user", "")
            if bq:
                url += f"?board_user={bq}"
        return url

    def get(self, request, pk):
        task = self._task(pk)
        if not user_can_view_task(request.user, task):
            raise Http404()
        can_edit = user_can_edit_task(request.user, task)
        form = TaskForm(instance=task, user=request.user) if can_edit else None
        return render(
            request,
            self.template_name,
            {
                "task": task,
                "can_edit": can_edit,
                "form": form,
                "board_back_url": self._board_back_url(request),
            },
        )

    def post(self, request, pk):
        task = self._task(pk)
        if not user_can_view_task(request.user, task):
            raise Http404()
        if not user_can_edit_task(request.user, task):
            messages.error(request, permission_denied_message())
            return redirect("tasks:task_detail", pk=pk)
        old_column_id = task.column_id
        form = TaskForm(request.POST, request.FILES, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            for f in request.FILES.getlist("attachments"):
                TaskAttachment.objects.create(task=task, file=f)
            task.refresh_from_db()
            handle_completed_column_transition(task, old_column_id)
            messages.success(request, _("Task updated."))
            return redirect("tasks:task_detail", pk=pk)
        return render(
            request,
            self.template_name,
            {
                "task": task,
                "can_edit": True,
                "form": form,
                "board_back_url": self._board_back_url(request),
            },
        )


class TaskAttachmentDeleteView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, task_pk, pk):
        att = get_object_or_404(TaskAttachment, pk=pk, task_id=task_pk)
        if not user_can_view_task(request.user, att.task):
            raise Http404()
        if not user_can_edit_task(request.user, att.task):
            messages.error(request, permission_denied_message())
            return redirect("tasks:task_detail", pk=task_pk)
        att.delete()
        messages.success(request, _("Attachment removed."))
        return redirect("tasks:task_detail", pk=task_pk)


class TaskDeleteView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        if not user_can_view_task(request.user, task):
            raise Http404()
        if not user_can_edit_task(request.user, task):
            messages.error(request, permission_denied_message())
            return redirect("tasks:task_detail", pk=pk)
        task.delete()
        messages.success(request, _("Task deleted."))
        return _board_redirect(request)


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

        if not user_can_view_task(request.user, task):
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

        old_col_id = task.column_id
        with transaction.atomic():
            task.column = column
            task.save(update_fields=["column", "updated_at"])
            for position, tid in enumerate(ids_int):
                Task.objects.filter(pk=tid, column=column).update(position=position)

        task.refresh_from_db()
        handle_completed_column_transition(task, old_col_id)

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
        qs = Task.objects.filter(column__in=active, due_date__year=year, due_date__month=month)
        qs = tasks_visible_for_user(qs, request.user)
        rows = qs.values("due_date").annotate(c=Count("id"))
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
        qs = Task.objects.filter(column__in=active, due_date=d)
        qs = tasks_visible_for_user(qs, request.user)
        tasks = qs.select_related("column").order_by("title").values("id", "title", "column__slug")
        return JsonResponse({"date": raw, "tasks": list(tasks)})


class TaskHistoryView(LoginRequiredMixin, ListView):
    template_name = "tasks/task_history.html"
    context_object_name = "entries"
    paginate_by = 25

    def get_queryset(self):
        qs = TaskHistory.objects.select_related("user").order_by("-completed_at", "-pk")
        if self.request.user.is_staff or self.request.user.is_superuser:
            raw = self.request.GET.get("user")
            if raw:
                try:
                    qs = qs.filter(user_id=int(raw))
                except ValueError:
                    pass
            return qs
        return qs.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        User = get_user_model()
        ctx["history_filter_users"] = User.objects.filter(is_active=True).order_by("full_name", "username")
        ctx["history_filter_user_id"] = None
        raw = self.request.GET.get("user")
        if raw and (self.request.user.is_staff or self.request.user.is_superuser):
            try:
                ctx["history_filter_user_id"] = int(raw)
            except ValueError:
                pass
        return ctx


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "tasks/admin_dashboard.html"
    raise_exception = False

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_staff or u.is_superuser)

    def handle_no_permission(self):
        messages.error(self.request, _("You do not have access to the admin dashboard."))
        return redirect("tasks:board")

    def post(self, request, *args, **kwargs):
        form = BoardSettingsForm(request.POST, instance=BoardSettings.load())
        if form.is_valid():
            form.save()
            messages.success(request, _("Board settings saved."))
        else:
            for field, errs in form.errors.items():
                for e in errs:
                    messages.error(request, f"{field}: {e}")
        return redirect("tasks:admin_dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        User = get_user_model()
        ctx["columns"] = BoardColumn.objects.all().order_by("order", "pk")
        ctx["stats"] = {
            "users": User.objects.count(),
            "tasks": Task.objects.count(),
            "attachments": TaskAttachment.objects.count(),
            "active_columns": BoardColumn.objects.filter(is_active=True).count(),
            "history_entries": TaskHistory.objects.count(),
        }
        labels = dict(Task.Priority.choices)
        ctx["by_priority"] = [
            {"priority": labels[row["priority"]], "count": row["c"]}
            for row in Task.objects.values("priority").annotate(c=Count("id")).order_by("priority")
        ]
        ctx["column_form"] = AdminColumnForm()
        ctx["board_settings_form"] = BoardSettingsForm(instance=BoardSettings.load())

        today = timezone.now().date()
        try:
            period_year = int(self.request.GET.get("year", today.year))
            period_month = int(self.request.GET.get("month", today.month))
        except (TypeError, ValueError):
            period_year, period_month = today.year, today.month
        if period_month < 1 or period_month > 12 or period_year < 1970 or period_year > 2100:
            period_year, period_month = today.year, today.month

        tz = timezone.get_current_timezone()
        range_start = timezone.make_aware(datetime(period_year, period_month, 1, 0, 0, 0), tz)
        last_day = monthrange(period_year, period_month)[1]
        range_end = timezone.make_aware(
            datetime(period_year, period_month, last_day, 23, 59, 59, 999999),
            tz,
        )

        hist_month = TaskHistory.objects.filter(
            completed_at__gte=range_start,
            completed_at__lte=range_end,
        )

        tasks_completed_month = (
            hist_month.values("title", "completed_at").distinct().count()
        )

        per_day_unique = defaultdict(set)
        for title, completed_at in hist_month.values_list("title", "completed_at"):
            per_day_unique[completed_at.date()].add((title, completed_at))

        chart_labels = [str(d) for d in range(1, last_day + 1)]
        chart_values = [
            len(per_day_unique[date(period_year, period_month, d)])
            for d in range(1, last_day + 1)
        ]

        sort_workers = self.request.GET.get("sort_workers", "count")
        worker_order = self.request.GET.get("order", "desc")
        if sort_workers not in ("count", "name"):
            sort_workers = "count"
        if worker_order not in ("asc", "desc"):
            worker_order = "desc"

        workers_qs = User.objects.annotate(
            completed_entries=Count(
                "task_history_entries",
                filter=Q(
                    task_history_entries__completed_at__gte=range_start,
                    task_history_entries__completed_at__lte=range_end,
                ),
            )
        ).filter(completed_entries__gt=0)

        if sort_workers == "name":
            workers_qs = workers_qs.order_by(
                "full_name" if worker_order == "asc" else "-full_name",
                "username" if worker_order == "asc" else "-username",
            )
        else:
            workers_qs = workers_qs.order_by(
                "completed_entries" if worker_order == "asc" else "-completed_entries",
                "full_name",
            )

        top_workers = list(workers_qs[:25])

        def shift_month(y, m, delta):
            if delta < 0:
                return (y - 1, 12) if m <= 1 else (y, m - 1)
            return (y + 1, 1) if m >= 12 else (y, m + 1)

        py, pm = shift_month(period_year, period_month, -1)
        ny, nm = shift_month(period_year, period_month, 1)

        def period_query(**overrides):
            q = {
                "year": str(period_year),
                "month": str(period_month),
                "sort_workers": sort_workers,
                "order": worker_order,
            }
            q.update({k: str(v) for k, v in overrides.items()})
            return urlencode(q)

        dash_url = reverse("tasks:admin_dashboard")
        ctx["period_year"] = period_year
        ctx["period_month"] = period_month
        ctx["period_day_one"] = date(period_year, period_month, 1)
        ctx["tasks_completed_month"] = tasks_completed_month
        ctx["chart_labels_json"] = json.dumps(chart_labels)
        ctx["chart_values_json"] = json.dumps(chart_values)
        ctx["top_workers"] = top_workers
        ctx["sort_workers"] = sort_workers
        ctx["worker_order"] = worker_order
        ctx["stats_prev_month_url"] = f"{dash_url}?{period_query(year=py, month=pm)}"
        ctx["stats_next_month_url"] = f"{dash_url}?{period_query(year=ny, month=nm)}"
        ctx["sort_count_desc_url"] = f"{dash_url}?{period_query(sort_workers='count', order='desc')}"
        ctx["sort_count_asc_url"] = f"{dash_url}?{period_query(sort_workers='count', order='asc')}"
        ctx["sort_name_asc_url"] = f"{dash_url}?{period_query(sort_workers='name', order='asc')}"
        ctx["sort_name_desc_url"] = f"{dash_url}?{period_query(sort_workers='name', order='desc')}"

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
