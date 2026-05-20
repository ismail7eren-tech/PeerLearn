from django.contrib import admin
from .models import Note, Rental, Transaction, Notification, StoreItem, NotePackage, Inventory

# 1. NOTLAR
@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'yukleyen', 'fiyat', 'sayfa_sayisi')

# 2. BİLDİRİMLER
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'baslik', 'tarih', 'is_read')

# 3. İŞLEMLER
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('alici', 'satici', 'not_obj', 'miktar', 'tarih')

# 4. KİRALAMALAR
@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ('user', 'note', 'kira_baslangic', 'kira_bitis')

# 5. MAĞAZA ÜRÜNLERİ
@admin.register(StoreItem)
class StoreItemAdmin(admin.ModelAdmin):
    list_display = ('isim', 'kategori', 'fiyat')
    list_filter = ('kategori',)

# 6. ÖZEL PAKETLER
@admin.register(NotePackage)
class NotePackageAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'olusturan', 'fiyat', 'olusturulma_tarihi')

# 7. ENVANTER
@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'item', 'alinma_tarihi', 'is_active')