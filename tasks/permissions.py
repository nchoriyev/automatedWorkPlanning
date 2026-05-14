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


def permission_denied_message():
    return _("You cannot modify this task.")
