from django import forms
from .models import Task, TaskComment, TaskAttachment
from apps.projects.models import Project, ProjectMember
from django.contrib.auth import get_user_model
from django.db.models import Q


User = get_user_model()

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'status', 'priority', 'due_date', 'assigned_to', 'project']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if field_name not in ['due_date', 'description']:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Filter projects
        if user:
            if user.is_admin:
                self.fields['project'].queryset = Project.objects.all()
            else:
                self.fields['project'].queryset = Project.objects.filter(
                    Q(created_by=user) | Q(members=user)
                ).distinct()
                
        # If project_id is provided, pre-select and disable the project field
        if project_id:
            self.fields['project'].initial = project_id
            self.fields['project'].disabled = True
            
            # Filter assigned_to field to only show members of the project
            project = Project.objects.get(id=project_id)
            self.fields['assigned_to'].queryset = project.members.all()
        else:
            # Initially, don't show any assignees until a project is selected
            self.fields['assigned_to'].queryset = (
            User.objects.filter(is_active=True).order_by('username')
            )

class TaskCommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Add a comment...'}),
        }

class TaskAttachmentForm(forms.ModelForm):
    class Meta:
        model = TaskAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }

class TaskFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'All')] + list(Task.STATUS_CHOICES)
    PRIORITY_CHOICES = [('', 'All')] + list(Task.PRIORITY_CHOICES)
    
    title = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by title'}))
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    assigned_to = forms.ModelChoiceField(queryset=User.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    due_date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    due_date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)
        
        # If project_id is provided, filter assigned_to to members of that project
        if project_id:
            project = Project.objects.get(id=project_id)
            self.fields['assigned_to'].queryset = project.members.all()
        elif user:
            # If user is provided but no project, filter to users in any of the user's projects
            if user.is_admin:
                self.fields['assigned_to'].queryset = User.objects.all()
            else:
                user_projects = Project.objects.filter(
                    Q(created_by=user) | Q(members=user)
                ).distinct()
                self.fields['assigned_to'].queryset = User.objects.filter(
                    Q(created_projects__in=user_projects) | Q(projects__in=user_projects)
                ).distinct()
                self.fields['assigned_to'].queryset = (
                User.objects.filter(is_active=True).order_by('username')
        )
