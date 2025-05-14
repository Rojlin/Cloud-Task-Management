from django import forms
from .models import Project, ProjectMember
from apps.accounts.models import User
from django.contrib.auth import get_user_model

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'status', 'start_date', 'end_date', 'priority']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['start_date', 'end_date']:
                field.widget.attrs.update({'class': 'form-control'})

class ProjectMemberForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=get_user_model().objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    
    class Meta:
        model = ProjectMember
        fields = ['user', 'role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
        }

class ProjectFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'All')] + list(Project.STATUS_CHOICES)
    PRIORITY_CHOICES = [('', 'All')] + list(Project.PRIORITY_CHOICES)
    
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name'}))

class ProjectMemberInviteForm(forms.Form):
    emails = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text='Enter email addresses separated by comma'
    )
    role = forms.ChoiceField(choices=ProjectMember.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    
    def clean_emails(self):
        emails = self.cleaned_data['emails']
        email_list = [email.strip() for email in emails.split(',') if email.strip()]
        
        # Validate email format
        invalid_emails = []
        for email in email_list:
            try:
                forms.EmailField().clean(email)
            except forms.ValidationError:
                invalid_emails.append(email)
        
        if invalid_emails:
            raise forms.ValidationError(f"Invalid email addresses: {', '.join(invalid_emails)}")
        
        return email_list
