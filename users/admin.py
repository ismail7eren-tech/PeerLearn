from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    
    # Liste ekranında (Admin ana sayfası) görünecek sütunlar
    list_display = ['username', 'email', 'kredi', 'is_premium', 'is_staff']
    
    # Detay düzenleme ekranındaki alan grupları
    # DİKKAT: 'profile_image' ismini 'profil_resmi' olarak güncelledik!
    fieldsets = UserAdmin.fieldsets + (
        ('PeerLearn Ekonomi', {
            'fields': (
                'kredi', 
                'is_premium', 
                'profil_resmi',  # Burayı düzelttik
                'getiren_kisi', 
                'referans_odulu_alindi'
            )
        }),
    )
    
    # Yeni kullanıcı ekleme ekranı
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('PeerLearn Ekonomi', {
            'fields': (
                'email', 
                'first_name', 
                'last_name', 
                'kredi', 
                'is_premium'
            )
        }),
    )