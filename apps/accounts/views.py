from django.contrib import messages
from django.contrib.admin.sites import site
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from .forms import (
    CustomAuthenticationForm,
    CustomPasswordChangeForm,
    CustomUserCreationForm,
    UserProfileForm,
)
from .models import User, UserProfile


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = "accounts/login.html"

    def form_valid(self, form):
        user = form.get_user()

        # Check if account is locked
        if user.is_account_locked():
            remaining_time = user.get_lockout_time_remaining()
            messages.error(
                self.request,
                f"Account locked due to multiple failed login attempts. Please try again in {remaining_time} minutes.",
            )
            return self.form_invalid(form)

        # Check if user is verified
        if not user.is_verified and not user.is_superuser:
            messages.error(
                self.request,
                "Your account has not been verified yet. Please contact an admin.",
            )
            return self.form_invalid(form)

        # Reset failed attempts on successful login
        user.reset_failed_attempts()
        messages.success(self.request, f"Welcome back, {user.username}!")
        return super().form_valid(form)

    def form_invalid(self, form):
        username = form.cleaned_data.get("username")
        if username:
            try:
                user = User.objects.get(username=username)
                if not user.is_account_locked():
                    user.increment_failed_attempts()

                    if user.is_account_locked():
                        messages.error(
                            self.request,
                            "Account locked due to multiple failed login attempts. Please try again in 30 minutes.",
                        )
                    else:
                        attempts_left = 3 - user.failed_login_attempts
                        messages.warning(
                            self.request,
                            f"Invalid credentials. {attempts_left} attempts remaining before account lockout.",
                        )
                else:
                    remaining_time = user.get_lockout_time_remaining()
                    messages.error(
                        self.request,
                        f"Account locked. Please try again in {remaining_time} minutes.",
                    )
            except User.DoesNotExist:
                messages.error(self.request, "Invalid username or password.")

        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Login"
        return context


class CustomLogoutView(View):
    """
    Custom logout view that supports both GET and POST methods
    """

    def get(self, request):
        if request.user.is_authenticated:
            logout(request)
            messages.success(request, "You have been logged out.")
        return redirect("accounts:login")

    def post(self, request):
        if request.user.is_authenticated:
            logout(request)
            messages.success(request, "You have been logged out.")
        return redirect("accounts:login")


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        # Set verification token and save user
        user = form.save(commit=False)
        user.is_verified = False
        user.verification_token = get_random_string(64)
        user.save()

        # Create user profile (handled in form.save)
        form.save_m2m()

        messages.success(
            self.request,
            "Account created successfully. An admin will verify your account before you can log in.",
        )
        return HttpResponseRedirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Register"
        return context


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:password_change_done")


class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "accounts/profile.html"
    context_object_name = "user_obj"

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "User Profile"
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self):
        return self.request.user.userprofile

    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Profile"
        return context


# Admin only views for user management
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin()


class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 10  # Added pagination

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get("search")

        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "User Management"
        return context


class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):
        messages.success(self.request, "User created successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create User"
        context["action"] = "Create"
        return context


class UserDetailView(AdminRequiredMixin, DetailView):
    model = User
    template_name = "accounts/user_detail.html"
    context_object_name = "user_obj"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "User Details"
        return context


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"instance": self.object})
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "User updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit User"
        context["action"] = "Update"
        return context


def verify_user(request, pk):
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, "You do not have permission to perform this action.")
        return redirect("accounts:login")

    user = get_object_or_404(User, pk=pk)
    user.is_verified = True
    user.save()

    # Create notification for the verified user
    from apps.notifications.models import Notification

    # Create notification for the verified user
    user_notification = Notification.objects.create(
        user=user,
        title="Account Verified",
        message=f"Your account has been verified by {request.user.username}.",
        notification_type="user_verified",
        link="/dashboard/",
    )

    # Also create notification for the admin who verified
    admin_notification = Notification.objects.create(
        user=request.user,
        title="User Verified",
        message=f"You have verified user {user.username}.",
        notification_type="user_verified",
        link=f"/accounts/users/",
    )

    # Send real-time notification via WebSocket
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()

    # Send to user's notification group
    async_to_sync(channel_layer.group_send)(
        f"notifications_{user.id}",
        {
            "type": "notification_message",
            "message": {
                "title": "Account Verified",
                "content": f"Your account has been verified by {request.user.username}.",
                "link": "/dashboard/",
            },
        },
    )

    # Send to admin's notification group
    async_to_sync(channel_layer.group_send)(
        f"notifications_{request.user.id}",
        {
            "type": "notification_message",
            "message": {
                "title": "User Verified",
                "content": f"You have verified user {user.username}.",
                "link": f"/accounts/users/",
            },
        },
    )

    messages.success(request, f"User {user.username} has been verified successfully.")
    return redirect("accounts:user_list")


class UserDeleteView(AdminRequiredMixin, DeleteView):
    model = User
    template_name = "accounts/user_confirm_delete.html"
    success_url = reverse_lazy("accounts:user_list")
    context_object_name = "user_obj"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "User deleted successfully.")
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Delete User"
        return context


class CustomAdminView(AdminRequiredMixin, TemplateView):
    """Custom Admin view that mimics Django admin but with our own styling"""

    template_name = "admin/admin_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "CollaboraSync Admin Portal"
        # Add additional context if needed
        return context
