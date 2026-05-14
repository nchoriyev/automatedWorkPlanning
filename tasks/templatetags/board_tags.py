import html as html_module
import json

from django import template
from django.utils.safestring import mark_safe

from ..permissions import user_can_edit_task

register = template.Library()


def _label_for_slug(slug: str):
    from django.utils.translation import gettext as _

    mapping = {
        "planned": _("Planned"),
        "in_progress": _("In progress"),
        "review": _("In review"),
        "completed": _("Completed"),
    }
    return mapping.get(slug)


@register.simple_tag
def column_title(column):
    from tasks.models import BoardColumn

    if not isinstance(column, BoardColumn):
        return ""
    label = _label_for_slug(column.slug)
    if label:
        return str(label)
    return column.name or column.slug


@register.simple_tag
def column_sticker(column):
    """Emoji sticker per built-in column slug; generic columns get a pin."""
    from tasks.models import BoardColumn

    if not isinstance(column, BoardColumn):
        return ""
    stickers = {
        "planned": "📋",
        "in_progress": "⚙️",
        "review": "🔎",
        "completed": "🏁",
    }
    emoji = stickers.get(column.slug, "📌")
    return mark_safe(f'<span class="column-sticker-emoji" aria-hidden="true">{emoji}</span>')


@register.simple_tag
def user_can_edit(user, task):
    return user_can_edit_task(user, task)


@register.simple_tag(takes_context=True)
def task_payload(context, task):
    request = context["request"]
    user = request.user
    data = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else "",
        "assigned_to": task.assigned_to_id or "",
        "column": task.column_id,
        "can_edit": user_can_edit_task(user, task),
    }
    return html_module.escape(json.dumps(data))
