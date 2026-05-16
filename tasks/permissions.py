from django.db.models import Q
from django.utils.translation import gettext_lazy as _


def user_can_edit_task(user, task) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    if task.creator_id == user.id:
        return True
    if task.assigned_to_id == user.id:
        return True
    return False


def user_can_view_task(user, task) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return task.creator_id == user.id or (task.assigned_to_id is not None and task.assigned_to_id == user.id)


def permission_denied_message():
    return _("You cannot modify this task.")


def tasks_visible_for_user(queryset, user, staff_board_user_id=None):
    """Staff see all tasks (optional filter by creator/assignee). Others see only tasks they created or are assigned to."""
    if user.is_staff or user.is_superuser:
        if staff_board_user_id:
            try:
                uid = int(staff_board_user_id)
            except (TypeError, ValueError):
                uid = None
            if uid:
                return queryset.filter(Q(creator_id=uid) | Q(assigned_to_id=uid))
        return queryset
    return queryset.filter(Q(creator=user) | Q(assigned_to=user))