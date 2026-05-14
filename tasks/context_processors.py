def staff_nav(request):
    user = getattr(request, "user", None)
    show_admin_dashboard = bool(
        user and user.is_authenticated and (user.is_staff or user.is_superuser)
    )
    return {"show_admin_dashboard": show_admin_dashboard}
