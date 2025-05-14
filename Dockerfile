FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=task_management.settings

# Working directory in the container
WORKDIR /app

# Install dependencies
COPY project_requirements.txt .
RUN pip install --no-cache-dir -r project_requirements.txt
RUN pip install --no-cache-dir daphne channels

# Copy project
COPY . .

# Make scripts executable
RUN chmod +x check_deadlines.sh

# Create staticfiles directory
RUN mkdir -p staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 5000

# Run application
CMD ["daphne", "-b", "0.0.0.0", "-p", "5000", "task_management.asgi:application"]