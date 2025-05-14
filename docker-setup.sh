#!/bin/bash

# Exit on error
set -e

# Show command being executed
set -x

# Check if .env file exists, if not create from example
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env file from .env.example. Please edit it with your specific settings."
  exit 1
fi

# Make script executable
chmod +x check_deadlines.sh

# Build and start Docker containers
docker-compose up -d --build

# Run migrations
docker-compose exec web python manage.py migrate

# Create static files
docker-compose exec web python manage.py collectstatic --noinput

# Run an initial deadline check
docker-compose exec web ./check_deadlines.sh --once

echo "Docker setup complete! You can now access the application at http://localhost:5000"
echo "To create a superuser, run: docker-compose exec web python manage.py createsuperuser"
echo "Deadline notifications are configured to run every 6 hours"