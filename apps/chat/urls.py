from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.ChatRoomListView.as_view(), name='list'),
    path('<int:pk>/', views.ChatRoomDetailView.as_view(), name='detail'),
    path('create/', views.ChatRoomCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.ChatRoomUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ChatRoomDeleteView.as_view(), name='delete'),
    path('<int:pk>/add-members/', views.ChatRoomAddMembersView.as_view(), name='add_members'),
    path('api/messages/<int:room_id>/', views.get_messages, name='get_messages'),
    path('api/send-message/<int:room_id>/', views.send_message, name='send_message'),
]
