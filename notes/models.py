from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import os
import random
from PyPDF2 import PdfReader
from docx import Document
from django.contrib.auth.models import User
from django.db.models import Avg

from users import forms

# ==========================================================
# 1. AKADEMİK İÇERİK MODELLERİ
# ==========================================================

class Note(models.Model):
    is_nadir = models.BooleanField(default=False)
    baslik = models.CharField(max_length=200)
    aciklama = models.TextField()
    dosya = models.FileField(upload_to='notes/')  # Ana dosya
    kapak_resmi = models.ImageField(upload_to='covers/', null=True, blank=True)
    ders_kategorisi = models.CharField(max_length=100)
    yuklenme_tarihi = models.DateTimeField(auto_now_add=True)
    yukleyen = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notlar')
    onizleme_sayfalari = models.CharField(max_length=100, blank=True, null=True) # Örn: "1, 3, 5"
    onizleme_dosyasi = models.FileField(upload_to='previews/', null=True, blank=True)
    sayfa_sayisi = models.PositiveIntegerField(default=1, editable=False)
    
    sayfa_sayisi = models.PositiveIntegerField(default=1, editable=False) 
    fiyat = models.PositiveIntegerField(default=10)
    kira_fiyati = models.PositiveIntegerField(editable=False, null=True)
    is_pinned = models.BooleanField(default=False) # Sabitleme anahtarı
    begenenler = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='begendigi_notlar', blank=True)

    def save(self, *args, **kwargs):
        if self.dosya:
            try:
                ext = os.path.splitext(self.dosya.name)[1].lower()
                if ext == '.pdf':
                    self.dosya.seek(0)
                    reader = PdfReader(self.dosya)
                    self.sayfa_sayisi = len(reader.pages)
                elif ext == '.docx':
                    self.dosya.seek(0)
                    doc = Document(self.dosya)
                    self.sayfa_sayisi = len(doc.sections)
                else:
                    self.sayfa_sayisi = 1
            except Exception as e:
                print(f"Dosya okuma hatası: {e}")
                self.sayfa_sayisi = 1
        else:
            self.sayfa_sayisi = 1
        
        if not self.kira_fiyati:
            self.kira_fiyati = max(1, int(self.fiyat * 0.2))
            
        super().save(*args, **kwargs)

    # ⭐ ORTALAMA PUAN HESAPLAMA
    @property
    def average_rating(self):
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0
    
    
class NoteFile(models.Model):
    """ Çoklu dosya yükleme desteği için ek dosyalar """
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='ek_dosyalar')
    dosya = models.FileField(upload_to='notes/multiple/')

    def __str__(self):
        return f"{self.note.baslik} - Ek Dosya"

# ==========================================================
# 2. TİCARET VE KİRALAMA MODELLERİ
# ==========================================================

class Rental(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Tekil not kiralarsa burası dolacak (Boş bırakılabilir yaptık)
    note = models.ForeignKey(Note, on_delete=models.CASCADE, null=True, blank=True)
    # 🔥 YENİ: Paket kiralarsa burası dolacak (Tırnak içinde yazdık ki hata vermesin)
    package = models.ForeignKey('NotePackage', on_delete=models.CASCADE, null=True, blank=True)
    
    kira_baslangic = models.DateTimeField(auto_now_add=True)
    kira_bitis = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.id:
            self.kira_bitis = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

class Transaction(models.Model):
    alici = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alimlar')
    satici = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='satislar') # satıcı -> satici yapıldı
    not_obj = models.ForeignKey(Note, on_delete=models.CASCADE, null=True, blank=True)
    miktar = models.IntegerField()
    tarih = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    baslik = models.CharField(max_length=100)
    mesaj = models.TextField()
    tarih = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    # 🔥 YENİ EKLENECEKLER
    url = models.CharField(max_length=500, null=True, blank=True)
    action_text = models.CharField(max_length=50, null=True, blank=True)

# ==========================================================
# 3. MAĞAZA VE KİŞİSELLEŞTİRME SİSTEMİ
# ==========================================================

class StoreItem(models.Model):
    CATEGORY_CHOICES = [
        ('theme', 'Arka Plan Teması'),
        ('font', 'Özel Yazı Tipi'),
        ('frame', 'Profil Çerçevesi'),
        ('avatar', 'Özel Profil Avatarı'),  # İŞTE BU SATIRI EKLE
        ('effect', 'Görsel Efekt (Buton vb.)'),
    ]
    isim = models.CharField(max_length=100)
    kategori = models.CharField(max_length=20, choices=CATEGORY_CHOICES) # Burası bu listeyi kullanıyor
    fiyat = models.PositiveIntegerField()
    preview_image = models.ImageField(upload_to='store/previews/')
    css_class = models.CharField(max_length=100, help_text="Uygulanacak CSS sınıfı adı", blank=True, null=True)

    def __str__(self):
        return f"{self.isim} - {self.get_kategori_display()}"

class Inventory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='envanter_genel')
    item = models.ForeignKey(StoreItem, on_delete=models.CASCADE)
    alinma_tarihi = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Envanterler"

# ==========================================================
# 4. HİBRİT PAKETLEME SİSTEMİ
# ==========================================================

class NotePackage(models.Model):
    olusturan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    baslik = models.CharField(max_length=200)
    aciklama = models.TextField()
    notlar = models.ManyToManyField('Note', related_name='paketler', blank=True)
    yeni_dosya = models.FileField(upload_to='packages/', null=True, blank=True)
    fiyat = models.PositiveIntegerField()
    kapak_resmi = models.ImageField(upload_to='package_covers/', null=True, blank=True)
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)
    is_nadir = models.BooleanField(default=False)
    kira_fiyati = models.PositiveIntegerField(null=True, blank=True)
    begenenler = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='begendigi_paketler', blank=True)

    # 🔥 Otomatik kira fiyatı hesaplama
    def save(self, *args, **kwargs):
        if not self.kira_fiyati and self.fiyat:
            self.kira_fiyati = max(1, int(self.fiyat * 0.2))  # %20 kira fiyatı
        super().save(*args, **kwargs)

    def __str__(self):
        return self.baslik
    
# ==========================================================
# 5. YENİ MAĞAZA EKLEMELERİ (BOZMADAN EKLENDİ)
# ==========================================================

class ShopItem(models.Model):
    CATEGORY_CHOICES = [
        ('tema', 'Arka Plan Teması'),
        ('cerceve', 'Profil Çerçevesi'),
        ('yazi', 'Yazı Tipi & Efekt'),
        ('buton', 'Özel Buton Efekti'),
        ('paket', 'Not Paketi'),
    ]
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price = models.IntegerField(default=0)
    css_class = models.CharField(max_length=100, help_text="Uygulanacak CSS sınıfı (örn: neon-glow)")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='shop_items/', null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

class UserInventory(models.Model):
    # HATA FİX: settings.AUTH_USER_MODEL kullanıldı ve related_name değiştirildi
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='envanter_items')
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    purchased_at = models.DateTimeField(auto_now_add=True)

# ==========================================================
# PROFİL VE AKADEMİK KİMLİK SİSTEMİ
# ==========================================================

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    
    # Resim yükleme alanı
    profil_resmi = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    # Telefon numarası alanı 
    telefon = models.CharField(max_length=15, blank=True, null=True)
    
    # Biyografi/Slogan (Hero section'da yazacak olan)
    slogan = models.CharField(max_length=255, default="PeerLearn Akademik Üyesi")
    
    # Okul Birincisi vb. ünvanlar için
    title = models.CharField(max_length=100, default="Öğrenci")
    
    # Takipçi gizliliği (True ise takipçi listesi sadece kullanıcı tarafından görülebilir)
    takip_listesi_gizli = models.BooleanField(default=False)
    
    # Biyografi alanı (Kullanıcı kendini tanıtabilir, başarılarını yazabilir vb.)
    bio = models.TextField(max_length=300, blank=True, verbose_name="Biyografi")
    
    # Rozetler için virgülle ayrılmış yetenek listesi
    yetenekler = models.CharField(
        max_length=500, 
        blank=True, 
        null=True, 
        help_text="Virgülle ayırarak yaz: Python, Django, Figma"
    )
    
    # Dinamik olarak hesaplanacak veya manuel verilecek akademik puan
    peerscore = models.IntegerField(default=0)

    # --- YENİ EKLENEN ---
    # editable=False: Kimse elle değiştiremez. unique=True: Herkeste farklı olur.
    peer_id = models.CharField(max_length=7, unique=True, editable=False, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Eğer henüz bir peer_id yoksa (yeni profil oluşturulurken)
        if not self.peer_id:
            while True:
                # 1.000.000 ile 9.999.999 arasında 7 haneli rastgele bir numara üret
                new_id = str(random.randint(1000000, 9999999))
                # Eğer bu numara başkasında yoksa (unique kontrolü)
                if not Profile.objects.filter(peer_id=new_id).exists():
                    self.peer_id = new_id
                    break  # Bulduysak döngüyü bitir

        super().save(*args, **kwargs)
    # ---------------------

    def __str__(self):
        return f"{self.user.username} Profili"

# ==========================================================
# SİNYALLER (KULLANICI OLUŞTUĞUNDA OTOMATİK PROFİL)
# ==========================================================
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Kullanıcı ilk kez oluşturulduğunda profilini de oluşturur."""
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """Kullanıcı her kaydedildiğinde profilini de günceller."""
    if hasattr(instance, 'profile'):
        instance.profile.save()

# =====================FOLLOW(TAKİPÇİ SİSTEMİ)===================================
class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='following', 
        on_delete=models.CASCADE
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='followers', 
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"
    
#-------------------------------YORUM VE SORU-CEVAP SİSTEMİ-----------------------------------   
class Comment(models.Model):
    note = models.ForeignKey('Note', on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    # HATALI SATIRI ŞUNUNLA DEĞİŞTİR:
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    def __str__(self):
        return f"{self.author.username} - {self.content[:20]}"
    
# 1. SORU-CEVAP SİSTEMİ (Herkes sorabilir)
class Question(models.Model):
    note = models.ForeignKey('Note', on_delete=models.CASCADE, related_name='questions')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_answered = models.BooleanField(default=False)
    answer = models.TextField(null=True, blank=True)# 1. SORU-CEVAP SİSTEMİ (Herkes sorabilir)
    answered_at = models.DateTimeField(null=True, blank=True)# 1. SORU-CEVAP SİSTEMİ (Herkes sorabilir)

    def __str__(self):
        return f"Soru: {self.author.username} - {self.content[:20]}"

# 2. YORUM VE YILDIZ SİSTEMİ (Sadece satın alan/kiralayan)
class Review(models.Model):
    note = models.ForeignKey('Note', on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)]) # 1-5 yıldız
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    reply = models.TextField(null=True, blank=True)# 2. YORUM VE YILDIZ SİSTEMİ (Sadece satın alan/kiralayan)
    replied_at = models.DateTimeField(null=True, blank=True)# 2. YORUM VE YILDIZ SİSTEMİ (Sadece satın alan/kiralayan)

    class Meta:
        unique_together = ('note', 'author') # Bir kişi bir nota bir kez puan verebilir

    def __str__(self):
        return f"{self.rating} Yıldız - {self.author.username}"
    
    
#-------------------------------BAŞARI SİSTEMİ-----------------------------------
class UserAchievement(models.Model):
    ACHIEVEMENT_TYPES = (
        ('academic', 'Akademik Başarı (Notlar/Dereceler)'),
        ('certificate', 'Sertifika (Udemy, BTK Akademi vb.)'),
        ('project', 'Proje & Yarışma (Teknofest, Hackathon vb.)'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=200, verbose_name="Başarı Adı")
    category = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES)
    institution = models.CharField(max_length=200, verbose_name="Kurum", blank=True, null=True)
    description = models.TextField(max_length=500, verbose_name="Kısa Açıklama", blank=True, null=True) # Opsiyonel ekleme
    evidence_file = models.FileField(upload_to='achievements/%Y/%m/', verbose_name="Kanıt Belgesi (SS/PDF)")
    achievement_date = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False, verbose_name="Onaylandı mı?") # Profesyonel dokunuş
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
class NotePackageReview(models.Model):
    package = models.ForeignKey(NotePackage, on_delete=models.CASCADE, related_name='package_reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    point = models.PositiveIntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.package.baslik} - {self.user.username}"

class NotePackageQuestion(models.Model):
    package = models.ForeignKey(NotePackage, on_delete=models.CASCADE, related_name='package_questions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    answer = models.TextField(blank=True, null=True)
    is_answered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Soru: {self.package.baslik} - {self.user.username}"
    
# ==========================================================
# 6. PEERMESAJ (DM / MESAJLAŞMA) SİSTEMİ
# ==========================================================

class Conversation(models.Model):
    """İki kullanıcı arasındaki sohbet odası"""
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Sohbet Odası: {self.id}"

class Message(models.Model):
    """Sohbet odasındaki tekil mesajlar ve paylaşılan notlar"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True, null=True)
    
    # 🔥 İŞTE INSTAGRAM ÖZELLİĞİ: DM'den Not/Paket fırlatmak için
    shared_note = models.ForeignKey('Note', on_delete=models.SET_NULL, blank=True, null=True, related_name='shared_in_messages')
    shared_package = models.ForeignKey('NotePackage', on_delete=models.SET_NULL, blank=True, null=True, related_name='shared_in_messages')
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # Mesajlar eskiden yeniye sıralansın

    def __str__(self):
        return f"{self.sender.username}: {self.content[:20] if self.content else 'Paylaşım'}"