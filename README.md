# PeerLearn - Akran Öğrenim Platformu

PeerLearn, öğrencilerin akademik içerik paylaşımı yapabildiği, birbirlerinin başarılarını takip edebildiği ve verimlilik odaklı araçlarla (Pomodoro) çalışma süreçlerini optimize edebildiği bir akran öğrenim platformudur.

## 🚀 Proje Özellikleri

### 1. PeerScore Liderlik Tablosu
Kullanıcıların platformda paylaştığı içerikler ve etkileşimleri üzerinden hesaplanan `PeerScore` sistemi ile anlık güncellenen liderlik sıralaması.

### 2. PeerOdak (Pomodoro Motoru)
JS `visibilitychange` API'si ile entegre edilmiş, hile korumalı odaklanma modu. Kullanıcı sekmeyi değiştirdiğinde odaklanma süreci otomatik olarak izlenir.

### 3. Peerİstatistik (Akademik Analiz)
Chart.js kütüphanesi kullanılarak, kullanıcının akademik gelişimini ve çalışma trendlerini görselleştiren istatistik paneli.

### 4. Profil ve Envanter Yönetimi
Cropper.js destekli profil düzenleme ve platform içi aktivitelerden kazanılan puanlarla yönetilen kişiselleştirilebilir avatar/tema sistemi.

### 5. Sosyal Etkileşim ve Haberleşme
AJAX altyapısı ile sayfa yenilemeye gerek kalmadan anlık takip etme, içerik paylaşma ve gerçek zamanlı mesajlaşma (DM) deneyimi.

### 6. İçerik Arama ve Keşfet
Veritabanı üzerinde optimize edilmiş filtreleme motoru sayesinde, öğrenciler ihtiyaç duydukları notlara ve kaynaklara hızla erişebilir.

---

## 🛠 Kullanılan Teknolojiler

* **Backend:** Django (Python), PostgreSQL
* **Frontend:** HTML5, CSS3, JavaScript (AJAX, Chart.js, Cropper.js)
* **Araçlar:** Git, Gunicorn, PostgreSQL

---

## ⚙️ Kurulum ve Çalıştırma

Projeyi kendi yerel ortamınızda ayağa kaldırmak için aşağıdaki adımları izleyebilirsiniz:

1. **Depoyu Klonlayın:**
   ```bash
   git clone [https://github.com/ismail7eren-tech/PeerLearn.git](https://github.com/ismail7eren-tech/PeerLearn.git)
   cd PeerLearn


   Sanal Ortam Oluşturun:
   python -m venv venv
source venv/bin/activate  # Windows için: .\venv\Scripts\activate


Gerekli Kütüphaneleri Yükleyin:
pip install -r requirements.txt

Veritabanını Hazırlayın:
python manage.py migrete

Sunucuyu Başlatın:

python manage.py runserver


📜 Lisans
Bu proje akademik amaçlı geliştirilmiştir. Tüm hakları saklıdır.
