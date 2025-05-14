#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'task_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

User = get_user_model()

# Define the users with their roles
test_users = [
    {
        'username': 'admin1',
        'email': 'admin1@example.com',
        'password': 'admin123',
        'first_name': 'Admin',
        'last_name': 'User',
        'role': 'admin',
        'is_staff': True,
        'is_superuser': False,
    },
    {
        'username': 'project_manager',
        'email': 'pm@example.com',
        'password': 'manager123',
        'first_name': 'Project',
        'last_name': 'Manager',
        'role': 'project_manager',
        'is_staff': False,
        'is_superuser': False,
    },
    {
        'username': 'team_member',
        'email': 'member@example.com',
        'password': 'member123',
        'first_name': 'Team',
        'last_name': 'Member',
        'role': 'team_member',
        'is_staff': False,
        'is_superuser': False,
    },
    {
        'username': 'leader1',
        'email': 'leader1@example.com',
        'password': 'leader123',
        'first_name': 'Team',
        'last_name': 'Leader',
        'role': 'leader',
        'is_staff': False,
        'is_superuser': False,
    },
    # Create a superuser as well
    {
        'username': 'super_admin',
        'email': 'superadmin@example.com',
        'password': 'super123',
        'first_name': 'Super',
        'last_name': 'Admin',
        'role': 'admin',
        'is_staff': True,
        'is_superuser': True,
    }
]


def create_test_users():
    """Create test users with different roles"""
    created_users = []
    
    for user_data in test_users:
        username = user_data['username']
        email = user_data['email']
        password = user_data['password']
        role = user_data['role']
        
        # Check if user already exists by username or email
        user_exists = User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists()
        
        if user_exists:
            print(f"User with username '{username}' or email '{email}' already exists. Updating if found by username...")
            try:
                user = User.objects.get(username=username)
                # Update only fields that won't cause conflicts
                user.first_name = user_data['first_name']
                user.last_name = user_data['last_name']
                user.is_staff = user_data['is_staff']
                user.is_superuser = user_data['is_superuser']
                # Don't update email as it might cause conflicts
                user.save()
                # Set password separately
                user.set_password(password)
                user.save()
            except User.DoesNotExist:
                print(f"User with email '{email}' exists but username '{username}' does not. Skipping...")
                continue
        else:
            print(f"Creating new user '{username}'...")
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                is_staff=user_data['is_staff'],
                is_superuser=user_data['is_superuser'],
            )
        
        # Mark user as verified
        user.is_verified = True
        user.save()
        
        # Update or create user profile
        try:
            profile = UserProfile.objects.get(user=user)
            profile.role = role
            profile.save()
            print(f"Updated profile for '{username}' with role '{role}'")
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(
                user=user,
                role=role
            )
            print(f"Created profile for '{username}' with role '{role}'")
        
        created_users.append({
            'username': username,
            'password': password,
            'role': role
        })
    
    return created_users


if __name__ == "__main__":
    print("Creating test users...")
    users = create_test_users()
    print("\nCreated the following test users:")
    print("=" * 50)
    print(f"{'Username':<20} {'Password':<20} {'Role':<15}")
    print("-" * 50)
    for user in users:
        print(f"{user['username']:<20} {user['password']:<20} {user['role']:<15}")
    print("=" * 50)
    print("\nAll users are verified and ready to use.")