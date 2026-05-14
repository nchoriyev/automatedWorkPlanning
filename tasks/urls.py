from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.BoardView.as_view(), name="board"),
    path("tasks/calendar/month/", views.TaskDueCalendarMonthView.as_view(), name="calendar_month"),
    path("tasks/calendar/day/", views.TaskDueCalendarDayView.as_view(), name="calendar_day"),
    path("tasks/create/", views.TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/update/", views.TaskUpdateView.as_view(), name="task_update"),
    path("tasks/move/", views.TaskMoveView.as_view(), name="task_move"),
    path("admin-dashboard/", views.AdminDashboardView.as_view(), name="admin_dashboard"),
    path("admin-dashboard/columns/add/", views.AdminColumnCreateView.as_view(), name="column_create"),
]
