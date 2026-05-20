from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    # Çıkış işlemi artık POST ile yapılıyor, LogoutView otomatik halleder
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('settings/', views.user_settings, name='user_settings'),
    
    # Şifre Değiştirme
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change.html'), name='password_change'),
    path('password-change-done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
]