from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin Paneli (Doğru Kullanım)
    path('admin/', admin.site.urls),
    
    # Kullanıcı Kayıt/Giriş Sistemi
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Senin Not Uygulaman ve Ekonomi Motorun
    path('', include('notes.urls')),
    
    # Kullanıcı Uygulaman
    path('users/', include('users.urls')),
]

# Medya dosyalarını (Notlar, Kapaklar) tarayıcıda görmek için
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)