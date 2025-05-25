from django.urls import path
from . import views  # Import the views module from the current package

urlpatterns = [
    path('login/', views.custom_login_user, name='custom_login_user'),
    path('dashboard/', views.dashboard_user, name='dashboard-user'), 
    path('brstoexcel/', views.brstoexcel, name='brs-to-excel'), 
    path('rekapitulasi/', views.rekapitulasi, name='rekapitulasi'), 
    path('rekapitulasi_keseluruhan/', views.rekapitulasi_keseluruhan, name='rekapitulasi-keseluruhan'),
    path('rekapitulasi_pribadi/', views.rekapitulasi_pribadi, name='rekapitulasi-pribadi'), 
    path('profile/', views.profile_user, name='profile-user'), 
    path("update-profile/<int:user_id>/", views.update_profile_usr, name="update_profile_usr"),
    path('change-password/', views.change_password_usr, name='change-password_usr'),
    path('delete-brs/<int:id_brsexcel>/', views.delete_brs, name='delete-brs'),
]