from django.contrib.auth import get_user_model
from notes.models import Conversation

def unread_notifications_count(request):
    if request.user.is_authenticated:
        # 1. Senin orijinal sistem bildirim sayacın (Aynen korundu)
        system_count = request.user.notifications.filter(is_read=False).count()
        
        # 2. Instagram stili DM sayacı: Okunmamış mesajı olan benzersiz sohbet odalarını sayar
        dm_count = Conversation.objects.filter(
            participants=request.user,
            messages__is_read=False
        ).exclude(messages__sender=request.user).distinct().count()
        
        return {
            'unread_count': system_count,
            'unread_dm_count': dm_count
        }
    return {
        'unread_count': 0,
        'unread_dm_count': 0
    }