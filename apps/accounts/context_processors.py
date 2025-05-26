def user_permissions(request):
    """
    Provide role-based permission flags for templates to use
    """
    context = {
        "can_create_project": False,
        "can_create_task": False,
        "can_assign_tasks": False,
        "can_manage_users": False,
        "can_access_admin": False,
        "can_view_analytics": False,
        "can_manage_projects": False,
        "is_project_manager": False,
        "is_leader": False,
        "is_admin": False,
        "is_team_member": False,
    }

    # Check if user is authenticated
    if not request.user.is_authenticated:
        return context

    user = request.user

    # Set role flags
    context["is_admin"] = user.is_admin()
    context["is_project_manager"] = user.is_project_manager()
    context["is_leader"] = user.is_leader()
    context["is_team_member"] = user.is_team_member()

    # Set permission flags based on roles (with strict security checks)
    if user.is_admin():
        # Admin can do everything
        context["can_create_project"] = True
        context["can_create_task"] = True
        context["can_assign_tasks"] = True
        context["can_manage_users"] = True
        context["can_access_admin"] = True
        context["can_view_analytics"] = True
        context["can_manage_projects"] = True
    elif user.is_project_manager():
        # Project managers can create projects/tasks, assign tasks, view analytics
        context["can_create_project"] = True
        context["can_create_task"] = True
        context["can_assign_tasks"] = True
        context["can_view_analytics"] = True
        context["can_manage_projects"] = True
    elif user.is_leader():
        # Leaders can create projects, create tasks, and assign tasks within their projects
        context["can_create_project"] = True
        context["can_create_task"] = True
        context["can_assign_tasks"] = True
        context["can_manage_projects"] = True
    elif user.is_team_member():
        # Team members can only view and update assigned tasks
        # SECURITY: Explicitly ensure team members get NO admin permissions
        context["can_manage_users"] = False
        context["can_access_admin"] = False
        context["can_view_analytics"] = True

    return context
