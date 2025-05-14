from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Project URLs
    path('', views.ProjectListView.as_view(), name='list'),
    path('create/', views.ProjectCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='delete'),
    
    # Project Members URLs
    path('<int:project_id>/members/', views.ProjectMemberListView.as_view(), name='members'),
    path('<int:project_id>/members/add/', views.ProjectMemberCreateView.as_view(), name='add_member'),
    path('<int:project_id>/members/<int:pk>/edit/', views.ProjectMemberUpdateView.as_view(), name='edit_member'),
    path('<int:project_id>/members/<int:pk>/remove/', views.ProjectMemberDeleteView.as_view(), name='remove_member'),
    path('<int:project_id>/members/invite/', views.ProjectMemberInviteView.as_view(), name='invite_members'),
    
    # Project Statistics URLs
    path('<int:pk>/statistics/', views.ProjectStatisticsView.as_view(), name='statistics'),
    
    # API Endpoints
    path('api/<int:project_id>/members/', views.ProjectMemberApiView.as_view(), name='api_members'),
]
