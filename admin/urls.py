# admin/urls.py
from django.urls import path
from . import views

app_name = 'admin'

urlpatterns = [
    # Dashboard
    path('', views.admin_dashboard, name='dashboard'),
    
    # User management
    path('add-user/', views.add_user, name='add_user'),
    path('delete-user/<str:email>/', views.delete_user, name='delete_user'),
    path('update-user-role/', views.update_user_role, name='update_user_role'),  # ✅ Added

    # Room management
    path('delete-room/<int:room_id>/', views.delete_room, name='delete_room'),
    path('toggle-room-verification/<int:room_id>/', views.toggle_room_verification, name='toggle_room_verification'),
    
    # House management
    path('delete-house/<int:house_id>/', views.delete_house, name='delete_house'),
    path('toggle-house-verification/<int:house_id>/', views.toggle_house_verification, name='toggle_house_verification'),
    
    # Contact management
    path('view-contact/<int:contact_id>/', views.view_contact, name='view_contact'),
    path('delete-contact/<int:contact_id>/', views.delete_contact, name='delete_contact'),

    # AJAX endpoint for verification toggle
    path('update-verification/', views.update_verification, name='update_verification'),  # ✅ Added
    
    # API endpoints (optional)
    path('api/stats/', views.get_stats_api, name='stats_api'),
    path('api/search-users/', views.search_users_api, name='search_users_api'),
]
