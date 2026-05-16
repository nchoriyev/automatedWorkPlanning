from datetime import timedelta

from django.utils import timezone


def purge_completed_tasks():
    """Remove tasks that stayed long enough in the configured completed column."""
    from .models import BoardSettings, Task

    settings = BoardSettings.load()
    cc = settings.completed_column_id
    if not cc or settings.completed_retention_hours < 1:
        return 0
    cutoff = timezone.now() - timedelta(hours=settings.completed_retention_hours)
    qs = Task.objects.filter(
        column_id=cc,
        entered_completed_at__isnull=False,
        entered_completed_at__lte=cutoff,
    )
    n = qs.count()
    qs.delete()
    return n


def log_task_completion_history(task):
    from .models import TaskHistory

    prio_label = task.get_priority_display()
    creator_name = task.creator.full_name if task.creator_id else ""
    assignee_name = task.assigned_to.full_name if task.assigned_to_id else ""

    user_ids = {task.creator_id}
    if task.assigned_to_id:
        user_ids.add(task.assigned_to_id)

    now = timezone.now()
    col_slug = task.column.slug

    for uid in user_ids:
        if not uid:
            continue
        TaskHistory.objects.create(
            user_id=uid,
            title=task.title,
            description=task.description or "",
            priority=str(prio_label),
            column_slug=col_slug,
            creator_display=creator_name,
            assignee_display=assignee_name,
            completed_at=now,
        )


def handle_completed_column_transition(task, previous_column_id):
    """After task.column reflects the new column (already saved)."""
    from .models import BoardSettings, Task

    settings = BoardSettings.load()
    cc_id = settings.completed_column_id
    if not cc_id:
        Task.objects.filter(pk=task.pk, entered_completed_at__isnull=False).update(entered_completed_at=None)
        task.refresh_from_db(fields=["entered_completed_at"])
        return

    was_done = previous_column_id == cc_id
    is_done = task.column_id == cc_id

    if is_done and not was_done:
        Task.objects.filter(pk=task.pk).update(entered_completed_at=timezone.now())
        task.refresh_from_db(fields=["entered_completed_at", "column_id"])
        log_task_completion_history(task)
    elif not is_done and was_done:
        Task.objects.filter(pk=task.pk).update(entered_completed_at=None)
        task.refresh_from_db(fields=["entered_completed_at"])
