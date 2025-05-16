from django.urls import path
from . import views 

urlpatterns = [

    path('dashboard/', views.dashboard_admin, name='dashboard-admin'), 
    path('manage-users/', views.manage_users, name='manage-users'), 
    path("change-user-role/", views.change_user_role, name="change_user_role"),
    path('log-activity/', views.log_activity, name='log-activity'),  
    path('profile/', views.profile_admin, name='profile-admin'), 
    path("update-profile/<int:user_id>/", views.update_profile_adm, name="update_profile_adm"),
    path('change-password/', views.change_password, name='change-password'),
    path('logout/', views.logout_view, name='logout'),

]