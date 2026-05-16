from django.utils.text import slugify


def allocate_username_from_full_name(full_name: str, *, exclude_pk=None) -> str:
    """Build a unique USERNAME_FIELD value from display name (users never type this)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    base = slugify((full_name or "").strip(), allow_unicode=True).replace("-", "_")
    if not base:
        base = "user"
    base = User.normalize_username(base)[:150]
    candidate = base
    n = 0
    qs = User.objects.all()
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(username=candidate).exists():
        n += 1
        suffix = f"_{n}"
        candidate = (base[: max(1, 150 - len(suffix))] + suffix)
    return candidate
