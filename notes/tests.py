from django.test import TestCase

# Kral, burası projenin test laboratuvarı. 
# Şimdilik burayı boş bırakıyoruz çünkü manuel testlerle mermi gibi gidiyoruz.
# İleride otomatik testler eklemek istersen kodlarını buraya yazacağız.

class NotesTest(TestCase):
    def test_example(self):
        # Örnek bir test mühürü
        self.assertEqual(1, 1)