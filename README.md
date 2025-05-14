# Task Management System

A comprehensive task management application with role-based permissions, Kanban boards, interactive calendars, and project tracking functionality built with Django and vanilla JavaScript.

## Features

- User authentication with admin verification
- Role-based permissions (Admin, Project Manager, Team Member, Leader)
- Project management with task assignments
- Kanban board for task visualization
- Real-time notifications and chat
- File attachments and comments on tasks
- Task status tracking and deadline management

## System Requirements

- Python 3.11 or higher
- PostgreSQL 13 or higher
- Docker and Docker Compose (optional, for containerized setup)

## Installation

### Option 1: Local Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd task-management
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r project_requirements.txt
   ```

4. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file with your specific settings.

5. Configure the database:
   ```
   python manage.py migrate
   ```

6. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```
   python manage.py runserver
   ```

### Option 2: Docker Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd task-management
   ```

2. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file with your specific settings.

3. Build and start the Docker containers:
   ```
   docker-compose up -d
   ```

4. Create a superuser:
   ```
   docker-compose exec web python manage.py createsuperuser
   ```

5. Access the application at http://localhost:8000

## User Roles

1. **Admin**: Full access to all functionalities, user management, and system configuration.
2. **Project Manager**: Can create projects, assign tasks, and manage project resources.
3. **Team Member**: Can update task status, add comments, and upload files.
4. **Leader**: Can manage team members and track project progress.

## Usage

1. Login as an admin to verify new user accounts
2. Create projects and add team members
3. Create tasks and assign them to team members
4. Use the Kanban board to visualize and manage task progress
5. Receive real-time notifications when tasks are assigned or updated
6. Use the chat feature for team communication

## Development

### Backend Structure

- `apps/accounts`: User authentication and profile management
- `apps/projects`: Project management functionality
- `apps/tasks`: Task management with Kanban boards
- `apps/notifications`: Real-time notifications
- `apps/chat`: Real-time chat functionality

### Frontend Features

- Bootstrap CSS for responsive design
- Vanilla JavaScript for interactivity
- WebSocket for real-time updates

## License

This project is licensed under the MIT License - see the LICENSE file for details.