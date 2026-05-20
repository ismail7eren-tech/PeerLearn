from django.contrib.auth.models import AbstractUser
from django.db import models


# Bu alanlar, kullanıcıların dijital portföylerini zenginleştirmek için eklendi. İleride bu alanlara özel ikonlar veya görseller ekleyebiliriz.
class CustomUser(AbstractUser):
    profil_resmi = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, null=True, verbose_name="Biyografi")
    yetenekler = models.CharField(max_length=500, blank=True)
    kredi = models.PositiveIntegerField(default=100)
    is_premium = models.BooleanField(default=False)
    
    # Mağazadan satın alınan eşyaların aktif olarak kullanılması için bir alan ekliyoruz. Bu, kullanıcının hangi eşyayı aktif olarak kullandığını takip etmemizi sağlar.
    aktif_cerceve = models.ForeignKey(
    'notes.StoreItem',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='kullananlar',
    verbose_name="Aktif Profil Çerçevesi"
)

    # Referans Sistemi
    getiren_kisi = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='referanslar'
    )
    referans_odulu_alindi = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'Kullanıcı'
        verbose_name_plural = 'Kullanıcılar'