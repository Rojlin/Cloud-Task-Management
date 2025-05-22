from django.core.management.base import BaseCommand

from apps.tasks.utils import send_overdue_notifications


class Command(BaseCommand):
    help = "Check for overdue tasks and send notifications"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Checking for overdue tasks..."))

        try:
            send_overdue_notifications()
            self.stdout.write(
                self.style.SUCCESS(
                    "Successfully checked and sent overdue task notifications"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error checking overdue tasks: {str(e)}")
            )
