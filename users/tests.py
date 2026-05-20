from django.test import TestCase
from .models import CustomUser

class UsersConfigTest(TestCase):
    def setUp(self):
        # Test için bir kullanıcı mühürleyelim
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='password123',
            email='test@peerlearn.com'
        )

    def test_user_creation(self):
        # Kullanıcı doğru oluşturuldu mu?
        self.assertEqual(self.user.username, 'testuser')
        # Başlangıç kredisi (senin modelinde 100) doğru mu?
        self.assertEqual(self.user.kredi, 100)

    def test_premium_status(self):
        # Default olarak premium kapalı olmalı
        self.assertFalse(self.user.is_premium)