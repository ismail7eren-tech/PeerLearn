from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, UserProfileUpdateForm

def register(request):
    """Yeni kullanıcı kayıt fonksiyonu."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='users.backends.EmailOrUsernameModelBackend')
            messages.success(request, f'Hoş geldin {user.username}! Kaydın başarıyla tamamlandı.')
            return redirect('ana_sayfa')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def user_settings(request):
    """Profil bilgilerini güncelleme (setting.html)."""
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil bilgileriniz güncellendi.')
            return redirect('user_settings')
    else:
        form = UserProfileUpdateForm(instance=request.user)
    return render(request, 'users/setting.html', {'form': form})