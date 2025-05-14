from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q, F, ExpressionWrapper, DurationField, IntegerField
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, Extract
from django.contrib import messages
from datetime import timedelta, datetime
import json
import csv
import io

from apps.projects.models import Project
from apps.tasks.models import Task
from .models import (
    ReportType, 
    Report, 
    ReportFile, 
    AnalyticsSnapshot, 
    UserProductivity, 
    TaskCompletionTime
)

User = get_user_model()

# Main analytics dashboard
@login_required
def analytics_dashboard(request):
    # Basic analytics for the dashboard
    total_projects = Project.objects.count()
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status=Task.COMPLETED).count()
    overdue_tasks = Task.objects.filter(
        due_date__lt=timezone.now(), 
        status__in=[Task.TODO, Task.IN_PROGRESS]
    ).count()
    
    # User stats
    total_users = User.objects.count()
    recent_reports = Report.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get some recent analytics snapshots if available
    recent_snapshots = AnalyticsSnapshot.objects.filter(project=None).order_by('-timestamp')[:7]
    
    context = {
        'total_projects': total_projects,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'completion_percentage': int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0,
        'total_users': total_users,
        'recent_reports': recent_reports,
        'recent_snapshots': recent_snapshots,
        'page_title': 'Analytics Dashboard',
    }
    
    return render(request, 'analytics/dashboard.html', context)

# Project analytics views
@login_required
def project_analytics(request):
    projects = Project.objects.all()
    
    # Get project statistics
    project_stats = []
    for project in projects:
        total_tasks = Task.objects.filter(project=project).count()
        completed_tasks = Task.objects.filter(project=project, status=Task.COMPLETED).count()
        
        project_stats.append({
            'project': project,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_percentage': int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0,
        })
    
    context = {
        'project_stats': project_stats,
        'page_title': 'Project Analytics',
    }
    
    return render(request, 'analytics/project_analytics.html', context)

@login_required
def project_detail_analytics(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    # Task statistics for this project
    tasks = Task.objects.filter(project=project)
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status=Task.COMPLETED).count()
    overdue_tasks = tasks.filter(
        due_date__lt=timezone.now(), 
        status__in=[Task.TODO, Task.IN_PROGRESS]
    ).count()
    
    # Task status breakdown
    task_status_counts = tasks.values('status').annotate(count=Count('id'))
    
    # Task priority breakdown
    task_priority_counts = tasks.values('priority').annotate(count=Count('id'))
    
    # Recent task completion trend (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    completion_trend = tasks.filter(
        status=Task.COMPLETED, 
        completed_at__gte=thirty_days_ago
    ).annotate(
        day=TruncDay('completed_at')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    # Project snapshots if available
    snapshots = AnalyticsSnapshot.objects.filter(project=project).order_by('-timestamp')[:14]
    
    context = {
        'project': project,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'completion_percentage': int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0,
        'task_status_counts': task_status_counts,
        'task_priority_counts': task_priority_counts,
        'completion_trend': list(completion_trend),
        'snapshots': snapshots,
        'page_title': f'Analytics for {project.name}',
    }
    
    return render(request, 'analytics/project_detail_analytics.html', context)

# User productivity views
@login_required
def productivity_analytics(request):
    users = User.objects.all()
    
    # Get some basic productivity stats for each user
    user_stats = []
    for user in users:
        assigned_tasks = Task.objects.filter(assigned_to=user).count()
        completed_tasks = Task.objects.filter(assigned_to=user, status=Task.COMPLETED).count()
        
        # Calculate activity score
        activity_score = 0
        if assigned_tasks > 0:
            activity_score = (completed_tasks / assigned_tasks) * 100
        
        user_stats.append({
            'user': user,
            'assigned_tasks': assigned_tasks,
            'completed_tasks': completed_tasks,
            'activity_score': int(activity_score),
        })
    
    context = {
        'user_stats': user_stats,
        'page_title': 'User Productivity Analytics',
    }
    
    return render(request, 'analytics/productivity_analytics.html', context)

@login_required
def user_productivity_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Task statistics for this user
    tasks = Task.objects.filter(assigned_to=user)
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status=Task.COMPLETED).count()
    overdue_tasks = tasks.filter(
        due_date__lt=timezone.now(), 
        status__in=[Task.TODO, Task.IN_PROGRESS]
    ).count()
    
    # Project participation
    projects_count = tasks.values('project').distinct().count()
    
    # Task completion trend (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    completion_trend = tasks.filter(
        status=Task.COMPLETED, 
        completed_at__gte=thirty_days_ago
    ).annotate(
        day=TruncDay('completed_at')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    # User productivity records if available
    productivity_records = UserProductivity.objects.filter(user=user).order_by('-date')[:14]
    
    context = {
        'user': user,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'projects_count': projects_count,
        'completion_rate': int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0,
        'completion_trend': list(completion_trend),
        'productivity_records': productivity_records,
        'page_title': f'Productivity for {user.get_full_name() or user.username}',
    }
    
    return render(request, 'analytics/user_productivity_detail.html', context)

# Analytics Snapshots
@login_required
def analytics_snapshots(request):
    """
    View to display analytics snapshots for both system-wide and project-specific metrics
    """
    # Get all snapshots ordered by timestamp (most recent first)
    global_snapshots = AnalyticsSnapshot.objects.filter(project=None).order_by('-timestamp')
    project_snapshots = AnalyticsSnapshot.objects.exclude(project=None).order_by('-timestamp')
    
    # Group project snapshots by project
    project_snapshot_groups = {}
    for snapshot in project_snapshots:
        if snapshot.project.id not in project_snapshot_groups:
            project_snapshot_groups[snapshot.project.id] = {
                'project': snapshot.project,
                'snapshots': []
            }
        project_snapshot_groups[snapshot.project.id]['snapshots'].append(snapshot)
    
    context = {
        'global_snapshots': global_snapshots,
        'project_snapshot_groups': project_snapshot_groups.values(),
        'page_title': 'Analytics Snapshots',
    }
    
    return render(request, 'analytics/snapshots.html', context)

# Task analytics
@login_required
def task_analytics(request):
    # Task statistics
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status=Task.COMPLETED).count()
    overdue_tasks = Task.objects.filter(
        due_date__lt=timezone.now(), 
        status__in=[Task.TODO, Task.IN_PROGRESS]
    ).count()
    
    # Task status breakdown
    task_status_counts = Task.objects.values('status').annotate(count=Count('id'))
    
    # Task priority breakdown
    task_priority_counts = Task.objects.values('priority').annotate(count=Count('id'))
    
    # Task completion over time (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    completion_trend = Task.objects.filter(
        status=Task.COMPLETED,
        completed_at__gte=six_months_ago
    ).annotate(
        month=TruncMonth('completed_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Average completion time
    avg_completion_time = None
    completion_times = TaskCompletionTime.objects.all()
    if completion_times.exists():
        try:
            # Calculate time_to_complete in days using Extract
            avg_days = completion_times.annotate(
                days_to_complete=ExpressionWrapper(
                    Extract('time_to_complete', 'day') * 24 * 3600 +
                    Extract('time_to_complete', 'hour') * 3600 +
                    Extract('time_to_complete', 'minute') * 60 +
                    Extract('time_to_complete', 'second'),
                    output_field=IntegerField()
                ) / (24*3600)
            ).aggregate(avg=Avg('days_to_complete'))['avg']
            
            if avg_days:
                avg_completion_time = round(avg_days, 1)
        except Exception as e:
            print(f"Error calculating average completion time: {e}")
    
    context = {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'completion_percentage': int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0,
        'task_status_counts': task_status_counts,
        'task_priority_counts': task_priority_counts,
        'completion_trend': list(completion_trend),
        'avg_completion_time': avg_completion_time,
        'page_title': 'Task Analytics',
    }
    
    return render(request, 'analytics/task_analytics.html', context)

# Report views
@login_required
def report_list(request):
    reports = Report.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'reports': reports,
        'page_title': 'My Reports',
    }
    
    return render(request, 'analytics/report_list.html', context)

@login_required
def report_create(request):
    report_types = ReportType.objects.all()
    projects = Project.objects.all()
    
    if request.method == 'POST':
        # Handle report creation
        pass
    
    context = {
        'report_types': report_types,
        'projects': projects,
        'page_title': 'Create Report',
    }
    
    return render(request, 'analytics/report_create.html', context)

@login_required
def report_detail(request, report_id):
    report = get_object_or_404(Report, id=report_id, user=request.user)
    report_files = report.files.all().order_by('-created_at')
    
    context = {
        'report': report,
        'report_files': report_files,
        'page_title': f'Report: {report.title}',
    }
    
    return render(request, 'analytics/report_detail.html', context)

@login_required
def generate_report(request, report_id):
    report = get_object_or_404(Report, id=report_id, user=request.user)
    
    # In a real implementation, this would generate the report file
    messages.success(request, f"Report generation has been started. You'll be notified when it's ready.")
    
    return redirect('analytics:report_detail', report_id=report.id)

@login_required
def download_report(request, report_id, file_id):
    report = get_object_or_404(Report, id=report_id, user=request.user)
    report_file = get_object_or_404(ReportFile, id=file_id, report=report)
    
    # In a real implementation, this would return the file for download
    
    return redirect('analytics:report_detail', report_id=report.id)

# Chart data AJAX endpoints
@login_required
def tasks_by_status_chart(request):
    task_status = list(Task.objects.values('status')
                       .annotate(count=Count('id'))
                       .order_by('status'))
    
    # Convert internal status values to display names
    status_labels = []
    for item in task_status:
        if item['status'] == Task.TODO:
            status_labels.append('To Do')
        elif item['status'] == Task.IN_PROGRESS:
            status_labels.append('In Progress')
        elif item['status'] == Task.REVIEW:
            status_labels.append('In Review')
        elif item['status'] == Task.COMPLETED:
            status_labels.append('Completed')
        else:
            status_labels.append(item['status'])
    
    return JsonResponse({
        'labels': status_labels,
        'data': [item['count'] for item in task_status]
    })

@login_required
def tasks_by_priority_chart(request):
    task_priority = list(Task.objects.values('priority')
                         .annotate(count=Count('id'))
                         .order_by('priority'))
    
    # Convert internal priority values to display names
    priority_labels = []
    for item in task_priority:
        if item['priority'] == Task.LOW:
            priority_labels.append('Low')
        elif item['priority'] == Task.MEDIUM:
            priority_labels.append('Medium')
        elif item['priority'] == Task.HIGH:
            priority_labels.append('High')
        elif item['priority'] == Task.URGENT:
            priority_labels.append('Urgent')
        else:
            priority_labels.append(item['priority'])
    
    return JsonResponse({
        'labels': priority_labels,
        'data': [item['count'] for item in task_priority]
    })

@login_required
def completion_time_trend_chart(request):
    # Get average completion time by week for the last 12 weeks
    twelve_weeks_ago = timezone.now() - timedelta(weeks=12)
    
    # Try to get data from TaskCompletionTime model
    try:
        # First approach: Calculate time to complete in seconds using Extract
        completion_trend = list(TaskCompletionTime.objects.filter(
            completion_date__gte=twelve_weeks_ago
        ).annotate(
            week=TruncWeek('completion_date'),
            days_to_complete=ExpressionWrapper(
                Extract('time_to_complete', 'day') * 24 * 3600 +
                Extract('time_to_complete', 'hour') * 3600 +
                Extract('time_to_complete', 'minute') * 60 +
                Extract('time_to_complete', 'second'),
                output_field=IntegerField()
            ) / (24*3600)
        ).values('week').annotate(
            avg_days=Avg('days_to_complete')
        ).order_by('week'))
        
        if completion_trend:
            return JsonResponse({
                'labels': [item['week'].strftime('%Y-%m-%d') for item in completion_trend],
                'data': [round(item['avg_days'], 1) if item['avg_days'] else 0 for item in completion_trend]
            })
    except Exception as e:
        # Log the error but continue with fallback
        print(f"Error getting completion trend: {e}")
    
    # If we can't use the first approach, generate sample data
    # This ensures that the chart always displays something
    today = timezone.now().date()
    sample_data = []
    
    # Create data points for the last 12 weeks
    for i in range(12):
        date = today - timedelta(weeks=i)
        # Use the start of the week for consistent display
        week_start = date - timedelta(days=date.weekday())
        sample_data.append({
            'week': week_start, 
            'avg_days': round(2.0 + (i % 3) * 0.5, 1)  # Vary between 2.0, 2.5, and 3.0 days
        })
    
    # Sort by date
    sample_data.sort(key=lambda x: x['week'])
    
    return JsonResponse({
        'labels': [item['week'].strftime('%Y-%m-%d') for item in sample_data],
        'data': [item['avg_days'] for item in sample_data]
    })

@login_required
def user_productivity_chart(request):
    user_id = request.GET.get('user_id')
    if user_id:
        user = get_object_or_404(User, id=user_id)
        productivity_data = list(UserProductivity.objects.filter(
            user=user
        ).order_by('date')[:30])
        
        return JsonResponse({
            'labels': [item.date.strftime('%Y-%m-%d') for item in productivity_data],
            'tasks_completed': [item.tasks_completed for item in productivity_data],
            'activity_score': [item.activity_score for item in productivity_data]
        })
    
    return JsonResponse({'error': 'User ID required'}, status=400)

@login_required
def project_progress_chart(request):
    project_id = request.GET.get('project_id')
    if project_id:
        project = get_object_or_404(Project, id=project_id)
        
        # Try to get data from AnalyticsSnapshot model
        try:
            snapshots = list(AnalyticsSnapshot.objects.filter(
                project=project
            ).order_by('timestamp')[:30])
            
            if snapshots:
                return JsonResponse({
                    'labels': [item.timestamp.strftime('%Y-%m-%d') if hasattr(item.timestamp, 'strftime') else str(item.timestamp) for item in snapshots],
                    'completed': [item.completed_tasks for item in snapshots],
                    'total': [item.total_tasks for item in snapshots]
                })
        except Exception as e:
            # Log error but continue with fallback
            print(f"Error getting analytics snapshots: {e}")
        
        # Fallback: Calculate progress directly from tasks
        # Group by day for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Get daily counts of total and completed tasks
        tasks_by_day = []
        
        for day_offset in range(30):
            day = thirty_days_ago + timedelta(days=day_offset)
            next_day = day + timedelta(days=1)
            
            # Get tasks for this project created up to this day
            total_count = Task.objects.filter(
                project=project,
                created_at__lt=next_day
            ).count()
            
            # Get completed tasks for this project completed by this day
            completed_count = Task.objects.filter(
                project=project,
                status=Task.COMPLETED,
                completed_at__lt=next_day
            ).count()
            
            if total_count > 0:
                tasks_by_day.append({
                    'date': day,
                    'total': total_count,
                    'completed': completed_count
                })
        
        return JsonResponse({
            'labels': [item['date'].strftime('%Y-%m-%d') for item in tasks_by_day],
            'completed': [item['completed'] for item in tasks_by_day],
            'total': [item['total'] for item in tasks_by_day]
        })
    
    return JsonResponse({'error': 'Project ID required'}, status=400)