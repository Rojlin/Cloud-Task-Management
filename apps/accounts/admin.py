from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'get_role')
    list_filter = ('is_active', 'is_staff', 'userprofile__role')
    
    def get_role(self, obj):
        return obj.userprofile.get_role_display()
    get_role.short_description = 'Role'

admin.site.register(User, UserAdmin)
