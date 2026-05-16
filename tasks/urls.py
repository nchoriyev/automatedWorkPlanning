from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.BoardView.as_view(), name="board"),
    path("tasks/history/", views.TaskHistoryView.as_view(), name="task_history"),
    path("tasks/calendar/month/", views.TaskDueCalendarMonthView.as_view(), name="calendar_month"),
    path("tasks/calendar/day/", views.TaskDueCalendarDayView.as_view(), name="calendar_day"),
    path("tasks/create/", views.TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/", views.TaskDetailView.as_view(), name="task_detail"),
    path(
        "tasks/<int:task_pk>/attachments/<int:pk>/delete/",
        views.TaskAttachmentDeleteView.as_view(),
        name="task_attachment_delete",
    ),
    path("tasks/<int:pk>/delete/", views.TaskDeleteView.as_view(), name="task_delete"),
    path("tasks/<int:pk>/update/", views.TaskUpdateView.as_view(), name="task_update"),
    path("tasks/move/", views.TaskMoveView.as_view(), name="task_move"),
    path("admin-dashboard/", views.AdminDashboardView.as_view(), name="admin_dashboard"),
    path("admin-dashboard/columns/add/", views.AdminColumnCreateView.as_view(), name="column_create"),
]
