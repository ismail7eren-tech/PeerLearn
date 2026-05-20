import os
import io
from django.contrib.auth.decorators import login_required
import re
import base64
from datetime import timedelta
from django.contrib.auth import get_user_model
User = get_user_model()

import cv2
import numpy as np
from PyPDF2 import PdfReader, PdfWriter

from django.db.models import Q


from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.urls import reverse
from django.core.files.base import ContentFile

from users.forms import UserProfileUpdateForm
from .forms import NotePackageForm, NoteUploadForm

from .models import (
    Follow, Note, NoteFile, Transaction, Rental, Notification,
    StoreItem, NotePackage, Inventory, Profile,
    ShopItem, UserInventory,
    Question, Review, UserAchievement,
    NotePackageReview, NotePackageQuestion,
    Conversation, Message
)

User = get_user_model()

# --- ANA SAYFA ---
def ana_sayfa(request):
    filtre = request.GET.get('filtre', 'all')
    
    
    notlar = Note.objects.exclude(ders_kategorisi="Paket İçeriği").order_by('-yuklenme_tarihi') if filtre in ['all', 'tekil'] else []
    
    paketler = NotePackage.objects.all().order_by('-olusturulma_tarihi') if filtre in ['all', 'paket'] else []

    # Notları ve paketleri tarihe göre karıştırıp listeliyoruz
    karisik_liste = sorted(
        list(notlar) + list(paketler), 
        key=lambda x: x.yuklenme_tarihi if hasattr(x, 'yuklenme_tarihi') else x.olusturulma_tarihi, 
        reverse=True
    )
    
    return render(request, 'notes/ana_sayfa.html', {'icerikler': karisik_liste, 'current_filter': filtre})

def not_detay(request, pk):
    """
    Not detay sayfası: Kullanıcının notu görüp göremeyeceğini,
    satın alıp almadığını veya kiralayıp kiralamadığını denetler.
    Soru-Cevap ve Değerlendirme verilerini sayfaya gönderir.
    """
    not_obj = get_object_or_404(Note, pk=pk)

    # --- SORU & DEĞERLENDİRME VERİLERİ ---
    questions = not_obj.questions.select_related("author").all().order_by('-created_at')
    reviews = not_obj.reviews.select_related("author").all().order_by('-created_at')

    # Başlangıçta her şeyi False kabul ediyoruz
    has_access = False
    is_owner = False
    is_purchased = False
    is_rented = False

    if request.user.is_authenticated:
        # 1. Notun sahibi mi?
        if not_obj.yukleyen == request.user:
            is_owner = True

        # 2. Daha önce satın almış mı?
        if Transaction.objects.filter(alici=request.user, not_obj=not_obj).exists():
            is_purchased = True

        # 3. Şu an aktif bir kiralaması var mı?
        if Rental.objects.filter(user=request.user, note=not_obj, kira_bitis__gt=timezone.now()).exists():
            is_rented = True

    # Herhangi biri True ise PDF'i görme yetkisi veriyoruz
    has_access = is_owner or is_purchased or is_rented

    return render(request, 'notes/note_detail.html', {
        'not': not_obj,
        'questions': questions,
        'reviews': reviews,
        'has_access': has_access,
        'is_purchased': is_purchased or is_owner,
        'is_rented': is_rented,
        'is_owner': is_owner,  # istersen template tarafında kullanırsın
    })

@login_required
def not_ekle(request):
    if request.method == 'POST':
        form = NoteUploadForm(request.POST, request.FILES)
        files = request.FILES.getlist('dosya') 
        
        if form.is_valid():
            yeni_not = form.save(commit=False)
            yeni_not.yukleyen = request.user
            
            if files:
                yeni_not.dosya = files[0] 
                yeni_not.save() # Önce kaydediyoruz ki sayfa sayısı hesaplansın
                
                # --- ÖNİZLEME (PDF KESME) MOTORU ---
                if yeni_not.dosya.name.lower().endswith('.pdf') and yeni_not.onizleme_sayfalari:
                    try:
                        # Adamın yazdığı "1, 3, 5" metnini sayılara çevir
                        sayfalar_str = yeni_not.onizleme_sayfalari.replace(' ', '').split(',')
                        secilen_sayfalar = [int(s) for s in sayfalar_str if s.isdigit()]
                        
                        toplam_sayfa = yeni_not.sayfa_sayisi
                        #  MATEMATİĞİ: %15 min, %25 max (En az 1 sayfa)
                        min_sayfa = max(1, int(toplam_sayfa * 0.15))
                        max_sayfa = max(1, int(toplam_sayfa * 0.25))
                        
                        if len(secilen_sayfalar) < min_sayfa or len(secilen_sayfalar) > max_sayfa:
                            messages.warning(request, f"ÖNİZLEME OLUŞTURULMADI: {toplam_sayfa} sayfalık bu not için en az {min_sayfa}, en fazla {max_sayfa} sayfa seçmelisiniz.")
                        else:
                            # Dosyayı aç, sadece seçilenleri kopyala
                            reader = PdfReader(yeni_not.dosya)
                            writer = PdfWriter()
                            
                            for sayfa_no in secilen_sayfalar:
                                # Kullanıcı 0 veya pdf'ten büyük sayfa yazarsa hata vermesin diye kontrol:
                                if 1 <= sayfa_no <= toplam_sayfa:
                                    writer.add_page(reader.pages[sayfa_no - 1]) # Index 0'dan başlar
                            
                            # Kesilen sayfaları yeni bir PDF olarak kaydet
                            preview_io = io.BytesIO()
                            writer.write(preview_io)
                            yeni_not.onizleme_dosyasi.save(f"onizleme_{yeni_not.id}.pdf", ContentFile(preview_io.getvalue()), save=True)
                            messages.info(request, "Önizleme dosyası başarıyla makaslandı ve kilitlendi! ✂️")
                            
                    except Exception as e:
                        print(f"Önizleme hatası: {e}")
                
                # Diğer dosyaları ek dosya olarak kaydet
                for f in files:
                    NoteFile.objects.create(note=yeni_not, dosya=f)
                
                #  NOT BAŞARIYLA YÜKLENDİĞİNDE 10 PUANI VERİTABANINA YAZIYORUZ 🔥
                profil = request.user.profile
                profil.peerscore += 10
                profil.save(update_fields=['peerscore'])
                
                messages.success(request, f'Başarılı! {len(files)} adet dosya not setine eklendi. 🔥')
                return redirect('ana_sayfa')
            else:
                messages.error(request, "Hata: En az bir not dosyası seçmelisiniz!")
        else:
            messages.error(request, "Form bilgilerini kontrol edin.")
    else:
        form = NoteUploadForm()
        
    return render(request, 'notes/upload_notes.html', {'form': form})

# --- SATIN ALMA (KOMİSYONLU) ---
@login_required
def not_satin_al(request, pk):
    not_obj = get_object_or_404(Note, pk=pk)
    alici = request.user
    satici = not_obj.yukleyen

    # 1. Ön Kontroller
    if Transaction.objects.filter(alici=alici, not_obj=not_obj).exists():
        messages.info(request, "Bu not zaten kütüphanenizde mevcut.")
        return redirect('not_detay', pk=pk)

    if satici == alici:
        messages.warning(request, "Kendi notunuzu satın alamazsınız.")
        return redirect('not_detay', pk=pk)

    if alici.kredi < not_obj.fiyat:
        messages.error(request, "Yetersiz bakiye! Lütfen kredi yükleyin.")
        return redirect('not_detay', pk=pk)

    try:
        # ATOMIC BLOCK: Buradaki işlemlerden biri bile fail olursa hiçbirini kaydetmez!
        with transaction.atomic():
            
            # 2. Komisyon Hesabı
            if alici.is_premium:
                sistem_payi = 2
            else:
                sistem_payi = int(not_obj.fiyat * 0.4)

            kazanc = not_obj.fiyat - sistem_payi

            # 3. Kredi Transferi
            alici.kredi -= not_obj.fiyat
            satici.kredi += int(kazanc)
            
            # 4. Referans Ödülü
            if alici.getiren_kisi and not alici.referans_odulu_alindi:
                ust_kullanici = alici.getiren_kisi
                ust_kullanici.kredi += 4
                ust_kullanici.save()
                alici.referans_odulu_alindi = True
                
                Notification.objects.create(
                    user=ust_kullanici,
                    baslik="Referans Kazancı! 🤝",
                    mesaj=f"Davet ettiğin {alici.username} ilk alışverişini yaptı! +4 kredi eklendi."
                )

            # Kaydetme işlemleri
            alici.save()
            satici.save()

            # 5. Kütüphane Kaydı (Transaction nesnesi erişimi sağlar)
            Transaction.objects.create(
                alici=alici,
                satici=satici,
                not_obj=not_obj,
                miktar=not_obj.fiyat
            )

            # 6. Satıcıya Bildirim
            Notification.objects.create(
                user=satici,
                baslik="Not Satıldı! 💰",
                mesaj=f"'{not_obj.baslik}' adlı notun satın alındı. Hesabına {kazanc} kredi eklendi."
            )

        messages.success(request, f"Tebrikler! {not_obj.baslik} artık kütüphanende. 🔥")
        
    except Exception as e:
        # Beklenmedik bir hata olursa paralar iade edilmiş gibi kalır (rollback)
        messages.error(request, "İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin.")
        
    return redirect('not_detay', pk=pk)
# --- KİRALAMA (24 SAAT) ---
@login_required
def not_kirala(request, pk):
    """
    24 Saatlik Kiralama: Kullanıcıdan kira bedelini düşer 
    ve erişim süresini başlatır.
    """
    not_obj = get_object_or_404(Note, pk=pk)
    
    # 1. GÜVENLİK: Kullanıcı zaten satın almış mı veya sahibi mi?
    is_purchased = Transaction.objects.filter(alici=request.user, not_obj=not_obj).exists()
    if is_purchased or not_obj.yukleyen == request.user:
        messages.info(request, "Bu not zaten kütüphanenizde kalıcı olarak mevcut.")
        return redirect('profil_self')

    # 2. GÜVENLİK: Halihazırda devam eden bir kiralaması var mı?
    aktif_kira = Rental.objects.filter(
        user=request.user, 
        note=not_obj, 
        kira_bitis__gt=timezone.now()
    ).exists()
    
    if aktif_kira:
        messages.warning(request, "Bu not için zaten aktif bir kiralamanız bulunuyor.")
        return redirect('not_detay', pk=pk)

    # 3. KREDİ KONTROLÜ
    # Note modelinde 'kira_fiyatı' alanı (property veya field) olduğunu varsayıyoruz
    if request.user.kredi >= not_obj.kira_fiyati:
        # Krediyi düş ve kaydet
        request.user.kredi -= not_obj.kira_fiyati
        request.user.save()
        
        # Rental kaydını oluştur (Modeldeki save() metodu otomatik +24 saat ekler)
        Rental.objects.create(user=request.user, note=not_obj)
        
        messages.success(request, f'"{not_obj.baslik}" notu 24 saatliğine kiralandı. Keyifli çalışmalar! 📖')
        return redirect('profil_self')
    else:
        messages.error(request, 'Yetersiz kredi bakiyesi. Lütfen kredi yükleyin.')
        return redirect('not_detay', pk=pk)
# --- PROFİL VE KÜTÜPHANE ---
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages



@login_required
def profil(request, pk=None):

    # 1) Kullanıcıyı belirle
    user_obj = get_object_or_404(User, pk=pk) if pk else request.user

    # 2) Profile objesini garantiye al
    from notes.models import Profile
    profile_obj, created = Profile.objects.get_or_create(user=user_obj)

    u_form = None

    # 3) Sadece kendi profilini güncelleyebilsin
    if user_obj == request.user:

        if request.method == 'POST':

            print("POST received", list(request.POST.keys()))

            # =========================================
            # 🔥 YENİ: MAĞAZA AVATARINI KUŞANMA MOTORU
            # =========================================
            if 'set_inventory_avatar' in request.POST:
                inv_id = request.POST.get('set_inventory_avatar')
                try:
                    from notes.models import Inventory
                    from django.core.files.base import ContentFile
                    # Kullanıcının envanterindeki o ürünü bul
                    inv_item = Inventory.objects.get(id=inv_id, user=request.user)
                    
                    if inv_item.item.preview_image:
                        # Mağazadaki resmi okuyup, profil resmine kopyalıyoruz
                        img_content = inv_item.item.preview_image.read()
                        file_name = inv_item.item.preview_image.name.split('/')[-1]
                        
                        profile_obj.profil_resmi.save(f"avatar_{user_obj.id}_{file_name}", ContentFile(img_content), save=True)
                        messages.success(request, "Efsanevi avatarın başarıyla kuşanıldı! 👑")
                except Exception as e:
                    messages.error(request, f"Avatar kuşanılırken hata oluştu: {e}")
                
                return redirect('profil_self')

            # =========================================
            # PROFİL RESMİ SİLME
            # =========================================
            if 'delete_profile_image' in request.POST:

                if profile_obj.profil_resmi:
                    profile_obj.profil_resmi.delete(save=False)
                    profile_obj.profil_resmi = None
                    profile_obj.save()

                    messages.info(request, "Profil resmin kaldırıldı. 👋")
                else:
                    messages.warning(request, "Zaten profil resmin yok. 😅")

                return redirect('profil_self')

            # =========================================
            # FORM (User model update)
            # =========================================
            u_form = UserProfileUpdateForm(
                request.POST,
                request.FILES,
                instance=user_obj
            )

            if u_form.is_valid():

                # =========================================
                # KULLANICI ADI GÜNCELLEME
                # =========================================
                new_username = request.POST.get('username')

                if new_username:
                    new_username = new_username.strip().lower()

                    if new_username != request.user.username:

                        if not User.objects.filter(username=new_username).exists():
                            user_obj.username = new_username
                            user_obj.save()
                        else:
                            messages.error(request, "Bu kullanıcı adı zaten alınmış! ❌")
                            return redirect('profil_self')

                # =========================================
                # FORM SAVE
                # =========================================
                user_obj = u_form.save()

                profil_resmi_degisti = False

                # Profile objesini tekrar garantiye al
                profile_obj, created = Profile.objects.get_or_create(user=user_obj)

                # =========================================
                # TELEFON
                # =========================================
                telefon_verisi = request.POST.get('phone')

                if telefon_verisi:
                    telefon_verisi = telefon_verisi.strip()

                    import re
                    telefon_verisi = re.sub(r'\D', '', telefon_verisi)

                    if telefon_verisi.startswith("90") and len(telefon_verisi) == 12:
                        telefon_verisi = telefon_verisi[2:]

                    if telefon_verisi.startswith("0") and len(telefon_verisi) == 11:
                        telefon_verisi = telefon_verisi[1:]

                    if len(telefon_verisi) != 10 or not telefon_verisi.startswith("5"):
                        telefon_verisi = None

                if telefon_verisi and profile_obj.telefon != telefon_verisi:
                    profile_obj.telefon = telefon_verisi
                    profile_obj.save()

                # =========================================
                # BIO / YETENEK / PORTFOLYO
                # =========================================
                bio_verisi = request.POST.get('bio')
                yetenek_verisi = request.POST.get('yetenekler')
                kurum_verisi = request.POST.get('kurum')
                unvan_verisi = request.POST.get('unvan')
                linkedin_verisi = request.POST.get('linkedin')
                portfolio_verisi = request.POST.get('portfolio')

                if bio_verisi is not None:
                    user_obj.bio = bio_verisi.strip()

                if yetenek_verisi is not None:
                    user_obj.yetenekler = yetenek_verisi.strip()

                if kurum_verisi is not None:
                    user_obj.kurum = kurum_verisi.strip()

                if unvan_verisi is not None:
                    user_obj.unvan = unvan_verisi.strip()

                if linkedin_verisi is not None:
                    user_obj.linkedin = linkedin_verisi.strip()

                if portfolio_verisi is not None:
                    user_obj.portfolio = portfolio_verisi.strip()

                user_obj.save()

                # =========================================
                # KAMERA / CROPPER
                # =========================================
                camera_data = request.POST.get('camera_image')

                if camera_data:
                    try:
                        import base64
                        from django.core.files.base import ContentFile
                        from django.utils import timezone as tz_kamera

                        su_an_ts = int(tz_kamera.now().timestamp())

                        format, imgstr = camera_data.split(';base64,')
                        ext = format.split('/')[-1]

                        image_data = base64.b64decode(imgstr)
                        file_name = f'cam_{user_obj.id}_{su_an_ts}.{ext}'

                        profile_obj.profil_resmi.save(
                            file_name,
                            ContentFile(image_data),
                            save=True
                        )

                        profil_resmi_degisti = True

                    except Exception as e:
                        print(f"Kamera Kayıt Hatası: {e}")

                # =========================================
                # GALERİ FOTOĞRAFI
                # =========================================
                if 'profil_resmi' in request.FILES and not camera_data:
                    profile_obj.profil_resmi = request.FILES['profil_resmi']
                    profile_obj.save()
                    profil_resmi_degisti = True

                # =========================================
                # MESAJLAR
                # =========================================
                if profil_resmi_degisti:
                    messages.success(request, "Profil fotoğrafın güncellendi! 🔥")
                else:
                    messages.success(request, "Profil bilgilerin mermi gibi güncellendi! 🔥")

                return redirect('profil_self')

        else:
            u_form = UserProfileUpdateForm(instance=user_obj)

    # =========================================
    # İSTATİSTİKLER
    # =========================================
    from django.db.models import Sum
    from notes.models import Note, Transaction, Rental, Inventory, Follow
    from django.utils import timezone as tz_lib

    toplam_yuklenen = Note.objects.filter(yukleyen=user_obj).count()

    toplam_satis = Transaction.objects.filter(satici=user_obj).count()

    toplam_kazanc = Transaction.objects.filter(
        satici=user_obj
    ).aggregate(Sum('miktar'))['miktar__sum'] or 0

    hesaplanan_score = request.user.profile.peerscore

    # =========================================
    # YETENEKLER
    # =========================================
    raw_yetenekler = getattr(user_obj, 'yetenekler', "")
    yetenek_listesi = raw_yetenekler.split(',') if raw_yetenekler else []

    # =========================================
    # TAKİP DURUMU
    # =========================================
    is_following = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(
            follower=request.user,
            following=user_obj
        ).exists()

    # =========================================
    # KÜTÜPHANE
    # =========================================
    kutuphanem = Note.objects.filter(
        id__in=Transaction.objects.filter(
            alici=user_obj,
            not_obj__isnull=False
        ).values_list('not_obj_id', flat=True)
    ).order_by('-yuklenme_tarihi')

    toplam_kutuphanem = kutuphanem.count()

    # =========================================
    # CONTEXT
    # =========================================
    context = {
        'user': user_obj,
        'u_form': u_form,

        'yuklenen_notlar': Note.objects.filter(
            yukleyen=user_obj
        ).order_by('-yuklenme_tarihi'),

        'alinan_notlar': kutuphanem,
        'kutuphanem': kutuphanem,
        'toplam_kutuphanem': toplam_kutuphanem,

        'aktif_kiralamalar': Rental.objects.filter(
            user=user_obj,
            kira_bitis__gt=tz_lib.now()
        ).select_related('note'),

        'envanter': Inventory.objects.filter(
            user=user_obj
        ).select_related('item'),

        'avatarlar': Inventory.objects.filter(
            user=user_obj,
            item__kategori__iexact='avatar'
        ).select_related('item'),

        'toplam_yuklenen': toplam_yuklenen,
        'toplam_kazanc': toplam_kazanc,
        'hesaplanan_score': hesaplanan_score,

        'yetenek_listesi': yetenek_listesi,
        'is_following': is_following,
    }

    return render(request, 'notes/profile.html', context)


# --- LİDERLİK (PEERSCORE İLK 100) ---
@login_required
def liderlik(request):
    """
    Liderlik Tablosu: En yüksek PeerScore gücüne sahip ilk 100 kullanıcıyı çeker.
    Ayrıca her kullanıcının toplam yüklediği not sayısını da hesaplar.
    """
    from django.contrib.auth import get_user_model
    AktifUser = get_user_model()

    # annotate ile yüklenen not sayısını (note_count) hesaplıyoruz
    # Sonra Profile tablosundaki peerscore'a göre azalan (-) şekilde dizip, ilk 100'ü çekiyoruz
    liderler = AktifUser.objects.select_related('profile').filter(
        profile__isnull=False
    ).annotate(
        note_count=Count('notlar')
    ).order_by('-profile__peerscore')[:100]

    return render(request, 'notes/liderlik.html', {
        'liderler': liderler
    })

# --- BİLDİRİMLER ---
@login_required
def notifications(request):
    """
    Bildirimler sayfası:
    - Kullanıcının tüm bildirimlerini listeler
    - Otomatik okundu yapmaz
    - Okundu işlemi buton ile yapılır
    """
    bildirimler = request.user.notifications.all().order_by('-tarih')

    unread_count = request.user.notifications.filter(is_read=False).count()

    return render(request, 'notes/notifications.html', {
        'bildirimler': bildirimler,
        'unread_count': unread_count
    })
# --- KREDİ TRANSFERİ (ULTRA SİGORTALI v2.0) ---
@login_required
def kredi_gonder(request, alici_id): 
    if request.method == 'POST':
        from django.contrib import messages
        from django.shortcuts import get_object_or_404, redirect
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from notes.models import Transaction, Notification

        # 👑 CUSTOM USER SİGORTASI: auth_user hatasını ebediyen engeller!
        AktifUser = get_user_model()
        alici = get_object_or_404(AktifUser, id=alici_id)
        
        try:
            miktar = int(request.POST.get('miktar', 0))
        except ValueError:
            messages.error(request, "Geçersiz miktar girdiniz! ❌")
            return redirect('profil', pk=alici_id)
        
        # 1. Temel Kontroller
        if alici == request.user:
            messages.error(request, "Kendi hesabınıza kredi gönderemezsin aslanım! 😅")
            return redirect('profil', pk=alici_id)
        
        if miktar <= 0:
            messages.error(request, "Gönderilecek miktar en az 1 kredi olmalıdır! ❌")
            return redirect('profil', pk=alici_id)

        if miktar > request.user.kredi:
            messages.error(request, "Yetersiz bakiye! Hesabınızda yeterli kredi yok. ❌")
            return redirect('profil', pk=alici_id)

        # 2. GÜNLÜK 3 FARKLI KİŞİ LİMİTİ
        bugun = timezone.now().date()
        
        # Gönderen kişinin (request.user) o gün yaptığı transferleri sorgula
        transfer_edilen_kisiler = Transaction.objects.filter(
            alici=request.user, 
            not_obj__isnull=True, 
            tarih__date=bugun
        ).values_list('satici_id', flat=True).distinct()

        # Limit dolmuşsa ve alıcı yeni biriyse bodoslama engelle
        if len(transfer_edilen_kisiler) >= 3 and alici.id not in transfer_edilen_kisiler:
            messages.error(request, "Günlük maksimum 3 farklı kişiye transfer limitine ulaştınız! ❌")
            return redirect('profil', pk=alici_id)

        # 3. İşlemi Gerçekleştir (Atomik Değişim)
        request.user.kredi -= miktar
        alici.kredi += miktar
        request.user.save()
        alici.save()

        # Geçmiş Kaydı Oluştur (Mermi gibi Transaction Tanımı)
        Transaction.objects.create(
            alici=request.user,
            satici=alici, 
            miktar=miktar,
            tarih=timezone.now()
        )
        
        # Alıcıya Anlık Bildirim Gönder 
        Notification.objects.create(
            user=alici,
            baslik="🪙 Kredi Transferi Geldi!",
            mesaj=f"@{request.user.username} size {miktar} kredi gönderdi! Cüzdanınız güncellendi. 🥳"
        )

        messages.success(request, f"@{alici.username} kullanıcısına {miktar} kredi başarıyla gönderildi! 🔥")
        return redirect('profil', pk=alici_id)

    return redirect('ana_sayfa')

# --- PDF GÖRÜNTÜLEME ---
@login_required
def view_pdf(request, pk):
    """
    Güvenli PDF Görüntüleyici: 
    Sadece notun sahibinin, satın alanın veya kiralamış olanın içeriği görmesini sağlar.
    """
    not_obj = get_object_or_404(Note, pk=pk)
    
    # --- ERİŞİM KONTROLÜ (GÜVENLİK DUVARI) ---
    is_owner = not_obj.yukleyen == request.user
    is_purchased = Transaction.objects.filter(alici=request.user, not_obj=not_obj).exists()
    is_rented = Rental.objects.filter(
        user=request.user, 
        note=not_obj, 
        kira_bitis__gt=timezone.now()
    ).exists()

    # Eğer yetkisi yoksa içeri sızamaz, detay sayfasına şutla
    if not (is_owner or is_purchased or is_rented):
        messages.error(request, "Bu içeriği görüntülemek için önce satın almalı veya kiralamalısınız.")
        return redirect('not_detay', pk=pk)

    # Yetkisi varsa PDF'in olduğu sayfayı aç
    return render(request, 'notes/view_pdf.html', {
        'not': not_obj
    })

# ==========================================================
#                  MAĞAZA VE KATEGORİ SİSTEMİ
# ==========================================================

def magaza_view(request):
    """ Mağazanın ana giriş sayfası """
    return render(request, 'notes/magaza.html')

def shop(request):
    return redirect('magaza')

def magaza_kategori_view(request, kategori_slug):
    items = []
    paketler = []
    baslik = ""

    # Kategoriye göre veritabanı filtrelemesi (peerMarket Yönlendiricisi)
    if kategori_slug == 'tema':
        # Admin panelinde 'Arka Plan Teması' seçince DB'ye 'theme' gidiyor
        items = StoreItem.objects.filter(kategori='theme') 
        baslik = "Kişisel Temalar"
    elif kategori_slug == 'cerceve':
        items = StoreItem.objects.filter(kategori='frame')
        baslik = "Profil Çerçeveleri"
    elif kategori_slug == 'font':
        items = StoreItem.objects.filter(kategori='font')
        baslik = "Özel Yazı Stilleri"
    elif kategori_slug == 'avatar':
        # YENİ EKLENEN KISIM: Avatarlar buradan çekilecek
        items = StoreItem.objects.filter(kategori='avatar')
        baslik = "Özel Karakter Avatarları"
    elif kategori_slug == 'paket':
        paketler = NotePackage.objects.all().order_by('-olusturulma_tarihi')
        baslik = "Özel Not Paketleri"

    return render(request, 'notes/magaza_kategori.html', {
        'items': items,
        'paketler': paketler,
        'baslik': baslik,
        'slug': kategori_slug
    })

@login_required
def buy_item_view(request, item_id):
    if request.method == "POST":
        item = get_object_or_404(StoreItem, id=item_id)
        user = request.user
        
        # 1. Zaten sahip mi kontrol et
        if Inventory.objects.filter(user=user, item=item).exists():
            return JsonResponse({'status': 'error', 'message': 'Bu ürüne zaten sahipsin kral!'})
        
        # 2. Kredi kontrolü
        if user.kredi >= item.fiyat:
            user.kredi -= item.fiyat
            user.save()
            
            # Envantere ekle
            Inventory.objects.create(user=user, item=item, is_active=False)
            
            return JsonResponse({
                'status': 'success', 
                'message': f'{item.isim} başarıyla satın alındı! Envanterimden aktif edebilirsin.'
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Kredin yetersiz be kral!'})
            
    return JsonResponse({'status': 'error', 'message': 'Geçersiz istek!'})

# notes/views.py

@login_required
def kredi_yukle_view(request):
    if request.method == 'POST':
        paket_id = request.POST.get('paket')
        
        # 3/1 Oranına Göre Paket Tanımları
        paketler = {
            'bronz': {'kredi': 30, 'fiyat': 10},
            'gumus': {'kredi': 60, 'fiyat': 20},
            'altin': {'kredi': 90, 'fiyat': 30},
            'platin': {'kredi': 120, 'fiyat': 40},
            'elmas': {'kredi': 240, 'fiyat': 80},
            'peer_pro': {'kredi': 300, 'fiyat': 100},
            'peer_ultra': {'kredi': 600, 'fiyat': 200},
        }

        if paket_id in paketler:
            secilen = paketler[paket_id]
            user = request.user
            user.kredi += secilen['kredi']
            user.save()
            
            # 🔥 CRITICAL FIX: satici=None yerine satici=user verilerek NOT NULL hatası ebediyen çözüldü.
            # Sistem kendi kendine bakiye yüklediği için satıcı ve alıcı aynı kişi olarak kaydoluyor.
            Transaction.objects.create(
                alici=user,
                satici=user, 
                miktar=secilen['kredi'],
                tarih=timezone.now()
            )
            
            messages.success(request, f"Mühürlendi! {secilen['kredi']} bakiye hesabına yüklendi. 🔥")
            return redirect('shop') # Mağazaya (Kategori ekranına) geri dönsün

    return render(request, 'notes/kredi_yukle.html')

@login_required
def satinal_view(request, item_id):
    item = get_object_or_404(StoreItem, id=item_id)
    user = request.user

    if Inventory.objects.filter(user=user, item=item).exists():
        messages.info(request, f"{item.isim} zaten envanterinizde mevcut.")
        return redirect('magaza')

    if user.kredi >= item.fiyat:
        user.kredi -= item.fiyat
        user.save()
        Inventory.objects.create(user=user, item=item)
        messages.success(request, f"{item.isim} başarıyla satın alındı!")
    else:
        messages.error(request, "Yetersiz kredi bakiyesi.")
    
    # Satın almadan sonra o kategorinin içinde kalması için yönlendirme
    return redirect('magaza_kategori', kategori_slug=item.kategori.replace('theme','tema').replace('frame','cerceve').replace('font','font').replace('effect','efekt'))


@login_required
def paket_olustur(request):
    if request.method == 'POST':
        form = NotePackageForm(request.POST, request.FILES, user=request.user)
        # Formdan gelen yeni dosyaları al
        yeni_files = request.FILES.getlist('yeni_dosyalar')
        
        if form.is_valid():
            paket = form.save(commit=False)
            paket.olusturan = request.user
            paket.save()
            
            # 1. Kütüphaneden seçilen eski notları bağla
            form.save_m2m() 
            
            # 2. Bilgisayardan yüklenen yeni dosyaları 'Note' olarak kaydet ve pakete ekle
            for f in yeni_files:
                yeni_not = Note.objects.create(
                    yukleyen=request.user,
                    baslik=f"{paket.baslik} - Ek Dosya",
                    dosya=f,
                    fiyat=0, # Paket içinde olduğu için tekil fiyatı 0
                    ders_kategorisi="Paket İçeriği"
                )
                paket.notlar.add(yeni_not)
            
            messages.success(request, "Paket başarıyla oluşturuldu!")
            return redirect('paket_detay', pk=paket.pk)
    else:
        form = NotePackageForm(user=request.user)
    
    kullanici_notlari = Note.objects.filter(yukleyen=request.user)
    return render(request, 'notes/paket_olustur.html', {'form': form, 'kullanici_notlari': kullanici_notlari})

# 1. PAKET DÜZENLEME FONKSİYONU
@login_required
def paket_duzenle(request, pk):
    paket = get_object_or_404(NotePackage, pk=pk, olusturan=request.user)
    kullanici_notlari = Note.objects.filter(yukleyen=request.user)
    
    if request.method == 'POST':
        form = NotePackageForm(request.POST, request.FILES, instance=paket, user=request.user)
        yeni_files = request.FILES.getlist('yeni_dosyalar')
        
        if form.is_valid():
            paket = form.save()
            
            # Yeni yüklenen dosyaları ekle
            for f in yeni_files:
                yeni_not = Note.objects.create(
                    yukleyen=request.user,
                    baslik=f"{paket.baslik} - Ek Dosya",
                    dosya=f,
                    fiyat=0,
                    ders_kategorisi="Paket İçeriği"
                )
                paket.notlar.add(yeni_not)
            
            messages.success(request, "Paket başarıyla güncellendi!")
            return redirect('paket_detay', pk=paket.pk)
    else:
        form = NotePackageForm(instance=paket, user=request.user)
    
    return render(request, 'notes/paket_olustur.html', {
        'form': form, 
        'kullanici_notlari': kullanici_notlari,
        'duzenleme_modu': True # Template'de başlığı değiştirmek için
    })

@login_required
def item_aktif_et(request, inventory_id):
    """ Satın alınan bir ürünü (tema, çerçeve vb.) kullanıma sunar """
    # 1. Envanter kaydını bul (Güvenlik için sadece kullanıcıya ait olanı)
    target_inv = get_object_or_404(Inventory, id=inventory_id, user=request.user)
    
    # 2. Ürünün kategorisini al (tema mı, çerçeve mi?)
    kategori = target_inv.item.kategori
    
    # 3. Aynı kategorideki diğer tüm aktif ürünleri kapat 
    # (Örn: Aynı anda sadece 1 tema aktif olabilir)
    Inventory.objects.filter(
        user=request.user, 
        item__kategori=kategori
    ).update(is_active=False)
    
    # 4. Seçilen yeni ürünü aktif yap
    target_inv.is_active = True
    target_inv.save()
    
    messages.success(request, f"{target_inv.item.isim} başarıyla aktif edildi! PeerLearn şimdi daha şık.")
    
    # 5. Yönlendirme: PK istemeyen 'profil_self' sayfasına gönderiyoruz
    return redirect('profil_self')
    
    
@login_required
def envanter_sifirla(request, kategori):
    """ Aktif olan tüm öğeleri kapatır ve varsayılan temaya döner """
    # GPT'nin uyardığı mükerrer satır temizlendi, tek satırda o kategorideki her şeyi deaktif ediyoruz
    Inventory.objects.filter(user=request.user, item__kategori=kategori).update(is_active=False)
    
    messages.info(request, f"{kategori} ayarları sıfırlandı. Varsayılan görünüme dönüldü.")
    
    # Kendi profil sayfamıza güvenli yönlendirme
    return redirect('profil_self')


@login_required
def envanter_goruntule(request):
    # Kullanıcının satın aldığı tüm ürünleri (tema, çerçeve vb.) getiriyoruz
    envanterim = Inventory.objects.filter(user=request.user)
    return render(request, 'notes/envanter.html', {'envanterim': envanterim})

@login_required
def envanter_aktif_et(request, inventory_id):
    inv_item = get_object_or_404(
        Inventory.objects.select_related('item'),
        id=inventory_id,
        user=request.user
    )

    user = request.user
    kategori = inv_item.item.kategori.lower()

    # kategoriye göre diğerlerini pasif et
    Inventory.objects.filter(user=user, item__kategori=kategori).update(is_active=False)

    inv_item.is_active = True
    inv_item.save()

    # profile objesi garanti olsun
    profile, created = Profile.objects.get_or_create(user=user)

    if kategori == 'avatar':
        if inv_item.item.preview_image:
            profile.profil_resmi = inv_item.item.preview_image
            profile.save()
            messages.success(request, f"Profil fotoğrafınız '{inv_item.item.isim}' olarak güncellendi.")

    elif kategori in ['frame', 'cerceve']:
        user.aktif_cerceve = inv_item.item
        user.save()
        messages.success(request, f"'{inv_item.item.isim}' çerçevesi uygulandı.")

    elif kategori in ['theme', 'tema']:
        messages.success(request, f"'{inv_item.item.isim}' teması aktif edildi.")

    return redirect(request.META.get('HTTP_REFERER', 'envanter_goruntule'))

# ==============================================================================
# İÇERİK YÖNETİMİ: NOT SİLME
# ==============================================================================
@login_required
def not_sil(request, pk):
    not_obj = get_object_or_404(Note, pk=pk, yukleyen=request.user)
    
    if request.method == 'POST':
        # 1. Puanı cebimize koyuyoruz
        korunacak_puan = request.user.profile.peerscore
        
        # 2. Notu siliyoruz (Sistemi kandıran o gizli kod burada çalışıp puanı düşürüyor)
        not_obj.delete()
        
        # 3. NÜKLEER ÇÖZÜM (DOĞRUDAN SQL MÜDAHALESİ)
        # save() kullanmıyoruz! update() ile veritabanı tablosuna direkt yazıyoruz.
        # Bu yöntemi sistemdeki hiçbir kod, sinyal veya cache engelleyemez.
        request.user.profile.__class__.objects.filter(user=request.user).update(peerscore=korunacak_puan)
        
        messages.success(request, "İçerik imha edildi. Puanın veritabanı seviyesinde kilitlendi! 🛡️")
        return redirect('profil_self') 
    
    return redirect('profil_self')
# ==============================================================================
# İÇERİK YÖNETİMİ: NOT DÜZENLEME
# ==============================================================================
@login_required
def not_duzenle(request, pk):
    """
    Mevcut bir notun bilgilerini (başlık, fiyat, dosya vb.) güncellemek için kullanılır.
    """
    not_obj = get_object_or_404(Note, pk=pk, yukleyen=request.user)
    
    if request.method == 'POST':
        # 'instance=not_obj' diyerek yeni kayıt oluşturmak yerine mevcut olanı güncelliyoruz
        form = NoteUploadForm(request.POST, request.FILES, instance=not_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Notun başarıyla güncellendi! ✅")
            return redirect('profil_self') 
    else:
        # Formu mevcut bilgilerle doldurarak kullanıcıya gösteriyoruz
        form = NoteUploadForm(instance=not_obj)
    
    context = {
        'form': form, 
        'duzenleme': True, 
        'not_obj': not_obj
    }
    return render(request, 'notes/upload_notes.html', context)

def search(request):
    """
    Gelişmiş Arama Motoru:
    - Notlar
    - Kullanıcılar
    - Paketler
    """

    AktifUser = get_user_model()
    query = request.GET.get('q', '').strip()

    notlar = Note.objects.none()
    kullanicilar = AktifUser.objects.none()
    paketler = NotePackage.objects.none()

    if query:

        # 1. NOT ARAMA
        notlar = (
            Note.objects
            .filter(baslik__icontains=query)
            .exclude(ders_kategorisi="Paket İçeriği")
            .order_by('-yuklenme_tarihi')
        )

        # 2. PAKET ARAMA
        paketler = (
            NotePackage.objects
            .filter(
                Q(baslik__icontains=query) |
                Q(aciklama__icontains=query)
            )
            .order_by('-olusturulma_tarihi')
        )

        # 3. KULLANICI ARAMA
        if query.startswith('#'):
            clean_id = query.replace('#', '')
            kullanicilar = AktifUser.objects.filter(profile__peer_id=clean_id)

        else:
            base_qs = AktifUser.objects.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )

            kullanicilar = base_qs.distinct().order_by('-kredi')

    return render(request, 'notes/search_results.html', {
        'notlar': notlar,
        'paketler': paketler,
        'kullanicilar': kullanicilar,
        'query': query
    })

@login_required
def paket_detay(request, pk):
    paket = get_object_or_404(NotePackage, pk=pk)
    notlar = paket.notlar.all()
    
    reviews = paket.package_reviews.all().order_by('-created_at')
    questions = paket.package_questions.all().order_by('-created_at')
    
    if request.method == "POST":
        # 1. YORUM GÖNDERME
        if 'submit_package_review' in request.POST:

            # ✅ EKLENEN GÜVENLİK KONTROLÜ
            if request.user == paket.olusturan:
                messages.error(request, "Kendi paketini değerlendiremezsin kral, ayıp olur! 😊")
                return redirect('paket_detay', pk=pk)

            point = request.POST.get('point', 5)
            comment = request.POST.get('comment')
            NotePackageReview.objects.create(
                package=paket,
                user=request.user,
                point=point,
                comment=comment
            )
            
            # BİLDİRİM: Paketi oluşturana "Yorum Geldi" bildirimi at
            if request.user != paket.olusturan:
                Notification.objects.create(
                    user=paket.olusturan,
                    baslik="Paketine Değerlendirme Geldi 🌟",
                    mesaj=f"@{request.user.username}, '{paket.baslik}' paketini {point} yıldız ile değerlendirdi.",
                    url=reverse('paket_detay', args=[paket.pk]), # HATA BURADAYDI, ÇÖZÜLDÜ!
                    action_text="Değerlendirmeyi İncele" # Senin modelindeki o şık özellik
                )
                
            messages.success(request, "Paket değerlendirmeniz başarıyla yayınlandı.")
            return redirect('paket_detay', pk=pk)
            
        # 2. SORU SORMA
        elif 'submit_package_question' in request.POST:
            text = request.POST.get('question_text')
            NotePackageQuestion.objects.create(
                package=paket,
                user=request.user,
                text=text
            )
            
            # BİLDİRİM: Paketi oluşturana "Soru Geldi" bildirimi at
            if request.user != paket.olusturan:
                Notification.objects.create(
                    user=paket.olusturan,
                    baslik="Paketine Soru Geldi ❓",
                    mesaj=f"@{request.user.username}, '{paket.baslik}' paketi hakkında bir soru sordu.",
                    url=reverse('paket_detay', args=[paket.pk]),
                    action_text="Soruyu Cevapla"
                )
                
            messages.success(request, "Sorunuz paket sahibine iletildi.")
            return redirect('paket_detay', pk=pk)

        # 3. SORUYA CEVAP VERME
        elif 'submit_package_answer' in request.POST:
            question_id = request.POST.get('question_id')
            answer_text = request.POST.get('answer_text')
            
            soru = get_object_or_404(NotePackageQuestion, id=question_id, package=paket)
            
            # Sadece paketi oluşturan cevap verebilir
            if request.user == paket.olusturan:
                soru.answer = answer_text
                soru.is_answered = True
                soru.save()
                
                # BİLDİRİM: Soruyu soran kişiye "Cevap Geldi" bildirimi at
                Notification.objects.create(
                    user=soru.user,
                    baslik="Soruna Cevap Geldi ✍️",
                    mesaj=f"'{paket.baslik}' paketine yazdığın soruya cevap verildi.",
                    url=reverse('paket_detay', args=[paket.pk]),
                    action_text="Cevabı Gör"
                )
                messages.success(request, "Cevabınız başarıyla gönderildi.")
                
            return redirect('paket_detay', pk=pk)

    return render(request, 'notes/paket_detay.html', {
        'paket': paket,
        'notlar': notlar,
        'reviews': reviews,
        'questions': questions
    })

# =====================FOLLOW(TAKİPÇİ SİSTEMİ)===================================
@login_required
def follow_user(request, pk):
    target_user = get_object_or_404(User, pk=pk)

    # Kendini takip etmeyi engelle
    if target_user == request.user:
        messages.warning(request, "Kendini takip edemezsin.")
        return redirect('profil', pk=pk)

    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=target_user
    )

    # ❌ TAKİPTEN ÇIKMA
    if not created:
        follow.delete()

        Notification.objects.filter(
            user=target_user,
            baslik="Yeni Takipçi",
            mesaj__icontains=request.user.username
        ).delete()

        messages.info(request, f"@{target_user.username} takibi bırakıldı.")
        return redirect('profil', pk=target_user.pk)

    # ✅ TAKİP ETME
    Notification.objects.create(
        user=target_user,
        baslik="Yeni Takipçi",
        mesaj=f"@{request.user.username} seni takip etmeye başladı! 🔥",
        is_read=False
    )

    messages.success(request, f"@{target_user.username} takip ediliyor! 🚀")

    return redirect('profil', pk=target_user.pk)


# --- TEKİL BİLDİRİMİ OKUNDU YAP ---
@login_required
def notification_mark_read(request, notif_id):
    # Senin modellerindeki yapıya uygun olarak 'user' üzerinden çekiyoruz
    notification = get_object_or_404(Notification, id=notif_id, user=request.user)
    
    if request.method == "POST":
        notification.is_read = True
        notification.save()
    
    return redirect("notifications")


# --- OKUNMAMIŞLARI OKUNDU YAP ---
@login_required
def notifications_mark_all_read(request):
    if request.method != "POST":
        messages.error(request, "Geçersiz istek.")
        return redirect("notifications")

    # Senin is_read=False filtrenle toplu güncelleme yapıyoruz
    updated_count = request.user.notifications.filter(is_read=False).update(is_read=True)

    if updated_count > 0:
        messages.success(request, f"{updated_count} bildirim okundu olarak işaretlendi.")
    else:
        messages.info(request, "Okunmamış bildirim yok.")

    return redirect("notifications")


# --- TÜM BİLDİRİMLERİ SİL ---
@login_required
def notifications_delete_all(request):
    if request.method != "POST":
        messages.error(request, "Geçersiz istek.")
        return redirect("notifications")

    deleted_count, _ = request.user.notifications.all().delete()

    if deleted_count > 0:
        messages.success(request, f"{deleted_count} bildirim silindi.")
    else:
        messages.info(request, "Silinecek bildirim yok.")

    return redirect("notifications")

@login_required
def notification_delete(request, notif_id):
    notification = get_object_or_404(Notification, id=notif_id, user=request.user)

    if request.method == "POST":
        notification.delete()

    return redirect("notifications")

#--- SORU SORMA VE DEĞERLENDİRME ---
@login_required
def add_question(request, pk):
    """Herkes not hakkında soru sorabilir."""
    if request.method == 'POST':
        note = get_object_or_404(Note, pk=pk)
        content = request.POST.get('content')
        if content:
            Question.objects.create(
                note=note,
                author=request.user,
                content=content
            )
            # Not sahibine bildirim gönder
            Notification.objects.create(
            user=note.yukleyen,
            baslik="Yeni Soru Geldi ❓",
            mesaj=f"@{request.user.username}, '{note.baslik}' notuna soru sordu.",
            url=f"/not/{note.pk}/#questionsTab",
            action_text="Hemen Cevapla"
            )
            messages.success(request, "Sorunuz başarıyla iletildi.")
    return redirect('not_detay', pk=pk)

@login_required
def add_review(request, pk):
    if request.method == 'POST':
        note = get_object_or_404(Note, pk=pk)

        is_owner = note.yukleyen == request.user
        is_purchased = Transaction.objects.filter(alici=request.user, not_obj=note).exists()
        is_rented = Rental.objects.filter(user=request.user, note=note, kira_bitis__gt=timezone.now()).exists()

        if is_owner or is_purchased or is_rented:
            rating = request.POST.get('rating')
            comment = request.POST.get('comment')

            if rating and comment:
                review_obj, created = Review.objects.update_or_create(
                    note=note,
                    author=request.user,
                    defaults={'rating': rating, 'comment': comment}
                )

                Notification.objects.create(
                    user=note.yukleyen,
                    baslik="Yeni Değerlendirme! ⭐",
                    mesaj=f"@{request.user.username}, '{note.baslik}' notuna {rating} yıldız verdi.",
                    url=f"/not/{note.pk}/#reviewsTab",
                    action_text="Yorumu Gör"
                )

                messages.success(request, "Değerlendirmeniz kaydedildi.")
        else:
            messages.error(request, "Değerlendirme yapabilmek için bu notun kütüphanenizde olması gerekir.")

    return redirect('not_detay', pk=pk)

#--- SORU VE YORUMLARA CEVAP VERME ---
@login_required
def reply_to_interaction(request, pk):
    """Not sahibinin soru veya yorumlara cevap vermesini sağlar."""
    if request.method == 'POST':
        item_type = request.POST.get('item_type')
        item_id = request.POST.get('item_id')
        reply_content = request.POST.get('reply_content')

        note = get_object_or_404(Note, pk=pk)
        
        print(f"DEBUG: item_type={item_type}, item_id={item_id}, reply_content={reply_content[:20] if reply_content else 'EMPTY'}")
        print(f"DEBUG: note.yukleyen={note.yukleyen}, request.user={request.user}, equal={note.yukleyen == request.user}")

        # sadece not sahibi cevap verebilir
        if note.yukleyen == request.user and reply_content:
            print(f"DEBUG: Koşul geçti, item_type={item_type}")

            if item_type == 'question':
                question = get_object_or_404(Question, id=item_id, note=note)
                print(f"DEBUG: Question bulundu: {question.id}")
                question.answer = reply_content
                question.is_answered = True
                question.answered_at = timezone.now()
                question.save()
                print(f"DEBUG: Question kaydedildi. answer={question.answer}")

                Notification.objects.create(
                user=question.author,
                baslik="Soruna Cevap Geldi ✍️",
                mesaj=f"'{note.baslik}' notuna yazdığın soruya cevap verildi.",
                url=f"/not/{note.pk}/#questionsTab",
                action_text="Cevabı Gör"
                )

            elif item_type == 'review':
                review = get_object_or_404(Review, id=item_id, note=note)
                review.reply = reply_content
                review.replied_at = timezone.now()
                review.save()

                Notification.objects.create(
                    user=review.author,
                    baslik="Yorumuna Cevap Geldi! 💬",
                    mesaj=f"'{note.baslik}' notuna yaptığın yoruma not sahibi cevap verdi."
                )

            messages.success(request, "Cevabınız başarıyla kaydedildi! 🔥")
        else:
            print(f"DEBUG: Koşul başarısız! yukleyen={note.yukleyen}, user={request.user}, reply_content boş mı={not reply_content}")

    return redirect('not_detay', pk=pk)

#--- BAŞARI VE SERTİFİKA VİTRİNİ ---
@login_required
def add_achievement(request):
    """Kullanıcının profilinde sergilenecek başarı ve sertifikaları ekler."""
    if request.method == "POST":
        category = request.POST.get("category")
        title = request.POST.get("title")
        institution = request.POST.get("institution")
        file = request.FILES.get("evidence_file")

        
        if title and file and category:
            try:
                UserAchievement.objects.create(
                    user=request.user,
                    title=title,
                    category=category,
                    institution=institution,
                    evidence_file=file
                )
                messages.success(request, f"'{title}' başarısı vitrinine eklendi! ✨")
            except Exception as e:
                messages.error(request, "Belge yüklenirken bir teknik hata oluştu.")
        else:
            messages.warning(request, "Lütfen gerekli tüm alanları (Başlık, Kategori, Dosya) doldurun.")

    # İşlem bitince geldiği sayfaya (Profile) geri döner
    return redirect(request.META.get('HTTP_REFERER', '/'))

#--- BAŞARI SİLME ---
@login_required
def delete_achievement(request, pk):
    achievement = get_object_or_404(UserAchievement, pk=pk, user=request.user)
    if request.method == "POST":
        # Dosyayı sunucudan (klasörden) de siler
        if achievement.evidence_file:
            if os.path.isfile(achievement.evidence_file.path):
                os.remove(achievement.evidence_file.path)
        
        achievement.delete()
        messages.success(request, "Başarı vitrinden kaldırıldı.")
    return redirect(request.META.get('HTTP_REFERER', '/'))


#--- BAŞARI DÜZENLEME ---
@login_required
def edit_achievement(request, pk):
    achievement = get_object_or_404(UserAchievement, pk=pk, user=request.user)
    if request.method == "POST":
        achievement.title = request.POST.get("title")
        achievement.institution = request.POST.get("institution")
        # Eğer yeni dosya seçildiyse eskisiyle değiştirir
        if request.FILES.get("evidence_file"):
            achievement.evidence_file = request.FILES.get("evidence_file")
        
        achievement.save()
        messages.success(request, "Başarı bilgileri güncellendi.")
    return redirect(request.META.get('HTTP_REFERER', '/'))


#--- TAKİPÇİ SİSTEMİ AJAX ---
@login_required
@require_POST
def takip_et_ajax(request):
    target_id = request.POST.get('id')
    target_user = get_object_or_404(User, id=target_id)
    
    # Kendi kendini takip etme engeli
    if target_user == request.user:
        return JsonResponse({'status': 'error', 'message': 'Kendini takip edemezsin!'})

    follow_obj, created = Follow.objects.get_or_create(follower=request.user, following=target_user)
    
    if not created:
        # Zaten takip ediyorsa takibi bırak (Unfollow)
        follow_obj.delete()
        action = "unfollowed"
    else:
        action = "followed"

    # Canlı takipçi sayısını geri gönderiyoruz
    follower_count = target_user.followers.count()
    
    return JsonResponse({
        'status': 'ok',
        'action': action,
        'count': follower_count
    })
    
@login_required
def paket_sil(request, pk):
    # 1. Paketi bul, eğer kullanıcı oluşturmamışsa 404 döndür (Güvenlik)
    paket = get_object_or_404(NotePackage, pk=pk, olusturan=request.user)
    
    if request.method == 'POST':
        # 2. Pakete özel yüklenen "Ek Dosya" notlarını da temizleyelim
        # (Kütüphaneden seçilen orijinal notlara dokunmaz, sadece paket içeriği olanları siler)
        paket.notlar.filter(ders_kategorisi="Paket İçeriği").delete()
        
        # 3. Paketi sil
        paket.delete()
        
        messages.success(request, "Paket ve pakete özel içerikler başarıyla silindi.")
        return redirect('profil_self') # Silince profile yönlendir
        
    return render(request, 'notes/paket_sil_onay.html', {'paket': paket})

@login_required
def paket_satin_al(request, pk):
    paket = get_object_or_404(NotePackage, pk=pk)
    
    # 1. GÜVENLİK: Kendi paketini satın alamaz
    if paket.olusturan == request.user:
        messages.warning(request, "Kendi oluşturduğunuz paketi satın alamazsınız.")
        return redirect('paket_detay', pk=pk)
    
    # 2. GÜVENLİK: Zaten satın almış mı? (Transaction kaydı kontrolü)
    # Not: Transaction modelinde not_obj yerine paket_obj alanı eklemediysen, 
    # sadece kredinin yetip yetmediğine bakıyoruz.
    if request.user.kredi >= paket.fiyat:
        with transaction.atomic():
            # Krediyi alıcıdan düş
            request.user.kredi -= paket.fiyat
            request.user.save()
            
            # Krediyi satıcıya ekle (Platform komisyonu kesmek istersen burayı güncellersin)
            paket.olusturan.kredi += paket.fiyat
            paket.olusturan.save()
            
            # Satın alma kaydı oluştur
            Transaction.objects.create(
                alici=request.user,
                satici=paket.olusturan,
                # not_obj=None, # Paket olduğu için not_obj boş kalabilir
                miktar=paket.fiyat
            )
            
            # BİLDİRİM: Satıcıya haber ver
            Notification.objects.create(
                user=paket.olusturan,
                baslik="Paket Satışı Başarılı! 💰",
                mesaj=f"@{request.user.username}, '{paket.baslik}' paketini satın aldı.",
                url=reverse('paket_detay', args=[paket.pk]),
                action_text="Paketi Gör"
            )
            
        messages.success(request, f"'{paket.baslik}' paketi kütüphanenize eklendi! Keyifli çalışmalar. 🚀")
        return redirect('profil_self')
    else:
        messages.error(request, "Yetersiz kredi bakiyesi. Lütfen kredi yükleyin.")
        return redirect('paket_detay', pk=pk)

@login_required
def paket_kirala(request, pk):
    paket = get_object_or_404(NotePackage, pk=pk)
    
    # 1. GÜVENLİK: Kendi paketi mi veya zaten aktif bir kiralaması var mı?
    if paket.olusturan == request.user:
        messages.info(request, "Bu paket size ait olduğu için kiralamanıza gerek yok.")
        return redirect('paket_detay', pk=pk)
    
    aktif_kira = Rental.objects.filter(
        user=request.user, 
        package=paket, # Models.py'da eklediğimiz yeni alan
        kira_bitis__gt=timezone.now()
    ).exists()
    
    if aktif_kira:
        messages.warning(request, "Bu paket için zaten aktif bir kiralamanız bulunuyor.")
        return redirect('paket_detay', pk=pk)

    # 2. KREDİ VE İŞLEM
    if paket.kira_fiyati and request.user.kredi >= paket.kira_fiyati:
        with transaction.atomic():
            request.user.kredi -= paket.kira_fiyati
            request.user.save()
            
            # Kiralama kaydı oluştur
            Rental.objects.create(user=request.user, package=paket)
            
            # BİLDİRİM: Satıcıya haber ver (Opsiyonel)
            Notification.objects.create(
                user=paket.olusturan,
                baslik="Yeni Kiralama Geldi ⏱️",
                mesaj=f"@{request.user.username}, '{paket.baslik}' paketini 24 saatliğine kiraladı.",
                url=reverse('paket_detay', args=[paket.pk]),
                action_text="Paketi İncele"
            )
            
        messages.success(request, f"'{paket.baslik}' paketi 24 saatliğine kiralandı. Başarılar! 🦁")
        return redirect('profil_self')
    else:
        messages.error(request, "Yetersiz kredi veya geçersiz kira fiyatı.")
        return redirect('paket_detay', pk=pk)
   #--- NOT BEĞENME AJAX --- 
@login_required
@require_POST
def not_begen_ajax(request):
    not_id = request.POST.get('id')
    try:
        not_obj = Note.objects.get(id=not_id)
        
        # Eğer kullanıcı zaten beğendiyse, beğeniyi geri çek (UnLike)
        if request.user in not_obj.begenenler.all():
            not_obj.begenenler.remove(request.user)
            action = "unliked"
        else:
            # Kullanıcı beğenmediyse, beğen (Like) ve bildirim at
            not_obj.begenenler.add(request.user)
            action = "liked"
            
            # Bildirim Gönderme (Kendi kendine beğenmiyorsa)
            if not_obj.yukleyen != request.user:
                Notification.objects.create(
                    user=not_obj.yukleyen,
                    baslik="Yeni Beğeni! ❤️",
                    mesaj=f"@{request.user.username}, '{not_obj.baslik}' adlı notunu beğendi!",
                    is_read=False
                )

        # Güncel beğeni sayısını döndür
        begeni_sayisi = not_obj.begenenler.count()
        return JsonResponse({'status': 'ok', 'action': action, 'count': begeni_sayisi})

    except Note.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Not bulunamadı!'})
    
# ==========================================================
# PEERMESAJ (INSTAGRAM TARZI DM) VİEW'LARI
# ==========================================================
@login_required
def mesaj_kutusu(request):
    """Kullanıcının tüm sohbetlerini ve Arkadaş/Diğerleri listesini ayarlar"""
    conversations = request.user.conversations.all().order_by('-updated_at')
    
    # 1. Takipçi ve Takip Edilenlerin ID'lerini çek
    takip_ettigim_idler = request.user.following.values_list('following_id', flat=True)
    beni_takip_eden_idler = request.user.followers.values_list('follower_id', flat=True)

    # 2. Karşılıklı Takipler (Arkadaşlar)
    arkadas_idler = set(takip_ettigim_idler).intersection(set(beni_takip_eden_idler))
    
    # 3. Tek Taraflı Takipler (Diğerleri)
    diger_idler = set(takip_ettigim_idler).symmetric_difference(set(beni_takip_eden_idler))

    AktifUser = get_user_model()
    arkadaslar = AktifUser.objects.filter(id__in=arkadas_idler)
    digerleri = AktifUser.objects.filter(id__in=diger_idler)

    return render(request, 'notes/mesaj_kutusu.html', {
        'conversations': conversations,
        'arkadaslar': arkadaslar,
        'digerleri': digerleri
    })

@login_required
def sohbet_odasi(request, username):
    """İki kişi arasındaki özel sohbet ve Reels Not penceresi (AJAX DESTEKLİ)"""
    from notes.models import Note, Transaction, Message, Conversation
    from django.http import JsonResponse
    from django.utils import timezone
    
    AktifUser = get_user_model()
    diger_kullanici = get_object_or_404(AktifUser, username=username)
    
    if diger_kullanici == request.user:
        from django.contrib import messages
        messages.warning(request, "Kendinize mesaj gönderemezsiniz kral. 😅")
        return redirect('mesaj_kutusu')

    conversation = Conversation.objects.filter(participants=request.user).filter(participants=diger_kullanici).first()
    
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, diger_kullanici)

    # Odaya girildiğinde karşı tarafın mesajlarını okundu yap
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    # 🔥 AJAX VE NORMAL FORM POST MOTORU
    if request.method == 'POST':
        icerik = request.POST.get('content')
        if icerik and icerik.strip():
            yeni_mesaj = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=icerik.strip()
            )
            conversation.updated_at = timezone.now()
            conversation.save()
            
            # Eğer istek JavaScript (AJAX) ile geldiyse sayfayı yenileme, JSON fırlat!
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'ok',
                    'message': yeni_mesaj.content,
                    'time': yeni_mesaj.created_at.strftime('%H:%M')
                })
                
            return redirect('sohbet_odasi', username=username)

    mesajlar = conversation.messages.all()
    
    kutuphanem = Note.objects.filter(
        Q(yukleyen=request.user) |
        Q(id__in=Transaction.objects.filter(alici=request.user, not_obj__isnull=False).values_list('not_obj_id', flat=True))
    ).distinct()

    return render(request, 'notes/sohbet_odasi.html', {
        'conversation': conversation,
        'diger_kullanici': diger_kullanici,
        'mesajlar': mesajlar,
        'kutuphanem': kutuphanem
    })

@login_required
@require_POST
def not_paylas_ajax(request):
    """Not detay sayfasından DM ile not fırlatır"""
    not_id = request.POST.get('not_id')
    alici_username = request.POST.get('alici_username')
    mesaj = request.POST.get('mesaj', '') # Opsiyonel mesaj

    try:
        alici = User.objects.get(username=alici_username)
        paylasilacak_not = Note.objects.get(id=not_id)

        if alici == request.user:
            return JsonResponse({'status': 'error', 'message': 'Kendine not gönderemezsin kral.'})

        # Sohbet odasını bul veya yarat
        conversation = Conversation.objects.filter(participants=request.user).filter(participants=alici).first()
        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, alici)

        # Mesajı yolla (shared_note alanını doldurarak)
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=mesaj.strip() if mesaj else None,
            shared_note=paylasilacak_not
        )
        
        conversation.updated_at = timezone.now()
        conversation.save()

        # Bildirim atalım şık olsun
        Notification.objects.create(
            user=alici,
            baslik="Sana Bir Not Gönderildi! 🚀",
            mesaj=f"@{request.user.username}, sana '{paylasilacak_not.baslik}' adlı notu DM'den fırlattı.",
            is_read=False
        )

        return JsonResponse({'status': 'ok', 'message': 'Not başarıyla fırlatıldı!'})

    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Böyle bir kullanıcı yok!'})
    except Note.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Not bulunamadı!'})

# --- PEERODAK BAŞARI ÖDÜL MOTORU ---
@login_required
def pomodoro_odul_ajax(request):
    if request.method == 'POST':
        from django.http import JsonResponse
        from notes.models import Profile
        
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        # Sunumda gövde gösterisi: Kullanıcıya hak ettiği 30 puanı mühürle
        profile.peerscore += 30
        profile.save()
        
        return JsonResponse({
            'status': 'ok',
            'new_score': profile.peerscore,
            'message': 'Harika! Odaklanma başarıyla tamamlandı, +30 PeerScore hesabına mühürlendi! 👑'
        })
    return JsonResponse({'status': 'error', 'message': 'Geçersiz istek.'})