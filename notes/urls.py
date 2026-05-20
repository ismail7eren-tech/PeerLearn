from django.urls import path
from . import views

urlpatterns = [
    # --- TEMEL ÖZELLİKLER ---
    path('', views.ana_sayfa, name='ana_sayfa'),
    path('not-paylas/', views.not_ekle, name='not_ekle'),
    path('not/<int:pk>/', views.not_detay, name='not_detay'),
    path('not-satin-al/<int:pk>/', views.not_satin_al, name='not_satin_al'),
    path('not-kirala/<int:pk>/', views.not_kirala, name='not_kirala'),
    path('not-goruntule/<int:pk>/', views.view_pdf, name='view_pdf'),
    path('not-sil/<int:pk>/', views.not_sil, name='not_sil'),
    path('not-duzenle/<int:pk>/', views.not_duzenle, name='not_duzenle'),
    path('bildirimler/okundu-yap/', views.notifications_mark_all_read, name='notifications_mark_all_read'),
    path('bildirimler/tumunu-sil/', views.notifications_delete_all, name='notifications_delete_all'), 
    path('bildirim-sil/<int:notif_id>/', views.notification_delete, name='notification_delete'),
    path('bildirim-oku/<int:notif_id>/', views.notification_mark_read, name='notification_mark_read'),
    
    # --- KULLANICI İŞLEMLERİ ---
    path('profil/', views.profil, name='profil_self'),
    path('profil/<int:pk>/', views.profil, name='profil'),
    path('liderlik/', views.liderlik, name='liderlik'),
    path('bildirimler/', views.notifications, name='notifications'),
    path('kredi-gonder/<int:alici_id>/', views.kredi_gonder, name='kredi_gonder'),
    path('ara/', views.search, name='search'), 
    
    # --- MAĞAZA (SHOP) SİSTEMİ ---
    path('magaza/', views.magaza_view, name='magaza'), 
    path('shop-redirect/', views.magaza_view, name='shop'),
    path('magaza/kategori/<str:kategori_slug>/', views.magaza_kategori_view, name='shop_category'),
    path('magaza/kredi-yukle/', views.kredi_yukle_view, name='kredi_yukle'),
    path('buy/<int:item_id>/', views.buy_item_view, name='buy_item'), 
    
    # --- PAKETLEME SİSTEMİ ---
    path('paket/<int:pk>/', views.paket_detay, name='paket_detay'),
    path('paket-olustur/', views.paket_olustur, name='paket_olustur'),
    path('paket/<int:pk>/sil/', views.paket_sil, name='paket_sil'),
    path('paket/<int:pk>/duzenle/', views.paket_duzenle, name='paket_duzenle'),
    path('paket-kirala/<int:pk>/', views.paket_kirala, name='paket_kirala'),
    path('paket-satin-al/<int:pk>/', views.paket_satin_al, name='paket_satin_al'),
    
    # --- ENVANTER VE AKTİVASYON ---
    path('envanterim/', views.envanter_goruntule, name='envanter_goruntule'),
    path('envanter/aktif-et/<int:inventory_id>/', views.envanter_aktif_et, name='envanter_aktif_et'),
    path('envanter/sifirla/<str:kategori>/', views.envanter_sifirla, name='envanter_sifirla'),
    # --- TAKİP SİSTEMİ ---
    path('follow/<int:pk>/', views.follow_user, name='follow_toggle'),
    path('takip-et-ajax/', views.takip_et_ajax, name='takip_et_ajax'),
    # --- SORU VE DEĞERLENDİRME ---
    path('not/<int:pk>/soru-sor/', views.add_question, name='add_question'),
    path('not/<int:pk>/degerlendir/', views.add_review, name='add_review'),
    path('not/<int:pk>/cevapla/', views.reply_to_interaction, name='reply_to_interaction'),
    #--- BAŞARI SİSTEMİ ---
    path('achievement/add/', views.add_achievement, name='add_achievement'),
    path('achievement/delete/<int:pk>/', views.delete_achievement, name='delete_achievement'),
    path('achievement/edit/<int:pk>/', views.edit_achievement, name='edit_achievement'),
    #---- AJAX İstekleri ---
    path('not/begen-ajax/', views.not_begen_ajax, name='not_begen_ajax'),
    # --- PEERMESAJ (DM SİSTEMİ) ---
    path('mesajlar/', views.mesaj_kutusu, name='mesaj_kutusu'),
    path('mesajlar/t/<str:username>/', views.sohbet_odasi, name='sohbet_odasi'),
    path('not/paylas-ajax/', views.not_paylas_ajax, name='not_paylas_ajax'),
    # --- POMODORO ÖDÜL SİSTEMİ ---
    path('pomodoro-odul-ajax/', views.pomodoro_odul_ajax, name='pomodoro_odul_ajax'),
]