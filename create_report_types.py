import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'task_management.settings')
django.setup()

from apps.analytics.models import ReportType

def create_report_types():
    """Create default report types for analytics"""
    
    # Define the default report types
    report_types = [
        {
            'name': 'Task Progress',
            'description': 'Report on task completion rates and progress over time'
        },
        {
            'name': 'Project Overview',
            'description': 'High-level overview of project status, tasks, and milestones'
        },
        {
            'name': 'User Productivity',
            'description': 'Analysis of user productivity, task completion rates, and activity'
        },
        {
            'name': 'Task Status Distribution',
            'description': 'Distribution of tasks by status (To Do, In Progress, Done, etc.)'
        },
        {
            'name': 'Project Timeline',
            'description': 'Project timeline with scheduled tasks, deadlines, and actual completion dates'
        },
    ]
    
    # Create report types if they don't exist
    for report_type_data in report_types:
        report_type, created = ReportType.objects.get_or_create(
            name=report_type_data['name'],
            defaults={'description': report_type_data['description']}
        )
        
        if created:
            print(f"Created report type: {report_type.name}")
        else:
            print(f"Report type already exists: {report_type.name}")

if __name__ == "__main__":
    create_report_types()
    print("Report types creation completed!")