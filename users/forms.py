from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    """Kayıt ekranında kullanılacak form."""
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control pro-input'})

class CustomUserChangeForm(UserChangeForm): # veya UserProfileUpdateForm
    class Meta:
        model = CustomUser
       
        fields = ('username', 'email', 'first_name', 'last_name', 'profil_resmi', 'kredi', 'is_premium')

class UserProfileUpdateForm(forms.ModelForm):
    """Ayarlar sayfasında bilgileri güncellemek için."""
    class Meta:
        model = CustomUser
        # BURAYA 'bio' ve 'yetenekler' alanlarını ekledik
        fields = ['first_name', 'last_name', 'email', 'profil_resmi', 'bio','yetenekler'] 
        
        widgets = {
            # Biyografi için şık bir textarea tanımlıyoruz
            'bio': forms.Textarea(attrs={
                'class': 'form-control pro-input',
                'rows': 3,
                'placeholder': 'Kendinden bahset... (Örn: Python geliştirici | Basketbol sever)'
            }),
            # Yetenekler için şık bir input tanımlıyoruz
            'yetenekler': forms.TextInput(attrs={
                'class': 'form-control pro-input',
                'placeholder': 'Yetenekler (virgülle ayrılmış)'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            # Senin mevcut pro-input tasarımını koruyoruz
            if 'class' not in field.widget.attrs:
                field.widget.attrs.update({'class': 'form-control pro-input'})