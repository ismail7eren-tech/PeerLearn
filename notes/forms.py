from django import forms
from .models import Note, NotePackage
from django.contrib.auth import get_user_model
User = get_user_model()

# ==============================================================================
# 1. TEKİL VE ÇOKLU NOT YÜKLEME FORMU (ÖĞRENCİ PANELİ)
# ==============================================================================
class NoteUploadForm(forms.ModelForm):
    """
    Kullanıcıların tekil notlarını veya bir başlık altında birden fazla 
    dosyayı (PDF, Word vb.) yüklemesini sağlayan ana form yapısı.
    """
    class Meta:
        model = Note
        # Form alanlarının profesyonel sıralaması
        fields = [
            'baslik', 'ders_kategorisi', 'aciklama', 
            'dosya', 'kapak_resmi', 'fiyat', 'is_nadir', 'onizleme_sayfalari','is_nadir'
        ]
        
        # HTML elemanlarını Bootstrap ve Pro-SaaS sınıflarıyla giydiriyoruz
        widgets = {
            'baslik': forms.TextInput(attrs={
                'class': 'form-control pro-input', 
                'placeholder': 'Örn: Diferansiyel Denklemler Final Notları'
            }),
            'ders_kategorisi': forms.TextInput(attrs={
                'class': 'form-control pro-input',
                'placeholder': 'Örn: Matematik Mühendisliği'
            }),
            'aciklama': forms.Textarea(attrs={
                'class': 'form-control pro-input', 
                'rows': 3,
                'placeholder': 'Not içeriği hakkında kısa ve öz bir bilgi verin...'
            }),
            # 'multiple' özelliği hata almamak için __init__ içinde eklenecek
            'dosya': forms.FileInput(attrs={
                'class': 'form-control pro-input'
            }),
            'kapak_resmi': forms.FileInput(attrs={
                'class': 'form-control pro-input'
            }),
            'fiyat': forms.NumberInput(attrs={
                'max': '30', 
                'min': '1', 
                'class': 'form-control pro-input',
                'placeholder': 'Kredi Tutarı'
            }),
            'is_nadir': forms.CheckboxInput(attrs={
                'class': 'form-check-input', 
                'role': 'switch'
            }),
            'onizleme_sayfalari': forms.TextInput(attrs={
                'class': 'form-control pro-input',
                'placeholder': 'Örn: 1, 3, 5 (Aralarına virgül koyarak yazın)'
            }),
            'is_nadir': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Form başlatıldığında çoklu dosya desteğini enjekte eder.
        """
        super().__init__(*args, **kwargs)
        
        # Django'nun ValueError fırlatmasını bu şekilde bypass ediyoruz
        self.fields['dosya'].widget.attrs.update({'multiple': True})
        
        # Kullanıcı dostu etiketlemeler
        self.fields['is_nadir'].label = "Bu İçeriği 'VIP / Özel Not' Olarak İşaretle"
        self.fields['dosya'].label = "Not Dosyalarınız (Sınırsız Seçebilirsiniz)"
        self.fields['onizleme_sayfalari'].label = "Önizlemede Gösterilecek Sayfalar"

    def clean(self):
        """
        Ekonomi dengesi için fiyat sınırlarını denetler.
        """
        cleaned_data = super().clean()
        fiyat = cleaned_data.get('fiyat')
        is_nadir = cleaned_data.get('is_nadir')

        if fiyat:
            if not is_nadir and fiyat > 17:
                raise forms.ValidationError(
                    "Standart notlar için maksimum 17 kredi yazabilirsiniz. "
                    "Daha fazlası için 'VIP İçerik' olarak işaretleyin."
                )
            if is_nadir and fiyat > 30:
                raise forms.ValidationError("VIP içeriklerde bile azami kredi sınırı 30'dur.")
        
        return cleaned_data


# ==============================================================================
# 2. PAKET NOT OLUŞTURMA FORMU (HİBRİT SİSTEM)
# ==============================================================================
class NotePackageForm(forms.ModelForm):
    """
    Hem bilgisayardan yeni dosyalar yükleyen hem de eski notları 
    seçerek paket oluşturan hibrit yapı.
    """
    # Kütüphanedeki eski notlar için çoklu seçim alanı
    secilen_notlar = forms.ModelMultipleChoiceField(
        queryset=Note.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input d-none'}),
        required=False,
    )
    
    # Bilgisayardan yüklenecek YENİ dosyalar alanı
    yeni_dosyalar = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control pro-input'
        }),
        required=False,
    )

    class Meta:
        model = NotePackage
        # 🔥 'is_nadir' ve 'onizleme_sayfalari' alanlarını ekledik (Modelinde varsa)
        fields = ['baslik', 'aciklama', 'fiyat', 'kira_fiyati', 'kapak_resmi', 'is_nadir']
        widgets = {
            'baslik': forms.TextInput(attrs={
                'class': 'form-control pro-input', 
                'placeholder': 'Örn: 2024 Vize + Final Hazırlık Seti'
            }),
            'aciklama': forms.Textarea(attrs={
                'class': 'form-control pro-input', 
                'rows': 3,
                'placeholder': 'Bu paketin içeriği hakkında bilgi verin...'
            }),
            'fiyat': forms.NumberInput(attrs={
                'class': 'form-control pro-input',
                'placeholder': 'Paket Toplam Kredisi'
            }),
            'kapak_resmi': forms.FileInput(attrs={'class': 'form-control pro-input'}),
            # 🔥 Switch tasarımı buraya eklendi
            'is_nadir': forms.CheckboxInput(attrs={
                'class': 'form-check-input', 
                'role': 'switch'
            }),
            
            'kira_fiyati': forms.NumberInput(attrs={
    'class': 'form-control pro-input',
    'placeholder': '24 Saatlik Kira Bedeli'
}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.fields['yeni_dosyalar'].widget.attrs.update({'multiple': True})
        
        if user:
            self.fields['secilen_notlar'].queryset = Note.objects.filter(yukleyen=user)
        
        self.fields['secilen_notlar'].label = "Kütüphanenizden Dahil Edilecek Notlar"
        self.fields['yeni_dosyalar'].label = "Pakete Yeni Dosyalar Yükle (PDF/Word)"
        # Etiket güncellemesi
        self.fields['is_nadir'].label = "Bu Paketi 'VIP / Özel Paket' Olarak İşaretle"