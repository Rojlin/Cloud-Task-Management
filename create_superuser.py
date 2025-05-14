import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'task_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

User = get_user_model()

def update_or_create_superuser():
    try:
        # Check if user exists
        if User.objects.filter(username='itsroj13').exists():
            user = User.objects.get(username='itsroj13')
            user.set_password('admin')
            user.email = 'itstoj13@gmail.com'
            user.is_staff = True
            user.is_superuser = True
            user.is_verified = True
            user.save()
            
            # Check if profile exists
            try:
                profile = UserProfile.objects.get(user=user)
                profile.role = 'admin'
                profile.save()
            except UserProfile.DoesNotExist:
                UserProfile.objects.create(
                    user=user,
                    role='admin'
                )
            
            print("Existing superuser updated successfully!")
        else:
            # Create new superuser
            superuser = User.objects.create_superuser(
                username='itsroj13',
                email='itstoj13@gmail.com',
                password='admin',
                is_verified=True
            )
            
            # Create user profile
            UserProfile.objects.create(
                user=superuser,
                role='admin'
            )
            
            print("New superuser created successfully!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    update_or_create_superuser()