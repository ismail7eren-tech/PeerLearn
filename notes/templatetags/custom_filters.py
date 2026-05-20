import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='render_skills')
def render_skills(value):
    if not value:
        return ""
    
    # Eşleşecek kelimeler ve ikonları
    icons = {
        # --- YAZILIM / BACK-END ---
        'python': 'fab fa-python text-primary',
        'c#': 'fas fa-code text-purple',
        'c++': 'fas fa-square-c text-info',
        'c': 'fas fa-copyright text-primary',
        'java': 'fab fa-java text-danger',
        'php': 'fab fa-php text-indigo',
        'ruby': 'fas fa-gem text-danger',
        'golang': 'fas fa-gear text-info',
        'rust': 'fas fa-shield-halved text-secondary',
        'node.js': 'fab fa-node-js text-success',
        'nodejs': 'fab fa-node-js text-success',
        'django': 'fas fa-leaf text-success',
        'flask': 'fas fa-flask text-secondary',
        'laravel': 'fab fa-laravel text-danger',
        'asp.net': 'fas fa-network-wired text-primary',
        
        # --- FRONT-END / TASARIM ---
        'html': 'fab fa-html5 text-danger',
        'css': 'fab fa-css3-alt text-primary',
        'javascript': 'fab fa-js text-warning',
        'js': 'fab fa-js text-warning',
        'typescript': 'fas fa-code text-info',
        'react': 'fab fa-react text-info',
        'vue': 'fab fa-vuejs text-success',
        'angular': 'fab fa-angular text-danger',
        'sass': 'fab fa-sass text-danger',
        'bootstrap': 'fab fa-bootstrap text-purple',
        'tailwind': 'fas fa-wind text-info',
        'figma': 'fab fa-figma text-danger',
        'ui/ux': 'fas fa-object-group text-primary',
        'photoshop': 'fas fa-image text-info',
        'illustrator': 'fas fa-pen-nib text-warning',

        # --- VERİTABANI / DEVOPS ---
        'sql': 'fas fa-database text-dark',
        'mysql': 'fas fa-database text-primary',
        'postgresql': 'fas fa-database text-info',
        'mongodb': 'fas fa-leaf text-success',
        'docker': 'fab fa-docker text-info',
        'kubernetes': 'fas fa-dharmachakra text-primary',
        'aws': 'fab fa-aws text-warning',
        'github': 'fab fa-github text-dark',
        'git': 'fab fa-git-alt text-danger',
        'linux': 'fab fa-linux text-dark',
        'ubuntu': 'fab fa-ubuntu text-danger',

        # --- SİBER GÜVENLİK ---
        'cybersecurity': 'fas fa-user-secret text-dark',
        'siber güvenlik': 'fas fa-shield-virus text-danger',
        'kali': 'fas fa-skull text-dark',
        'nmap': 'fas fa-search text-secondary',
        'pentest': 'fas fa-user-ninja text-dark',

        # Mühendislik
        'mühendis': 'fas fa-cogs text-dark',
        'inşaat': 'fas fa-hard-hat text-warning',
        'makine': 'fas fa-industry text-secondary',
        'elektrik': 'fas fa-bolt text-warning',
        'yazılım mühendisi': 'fas fa-laptop-code text-dark',

        # Mimarlık / Tasarım
        'mimarlık': 'fas fa-drafting-compass text-info',
        'autocad': 'fas fa-ruler-combined text-secondary',
        'grafik tasarım': 'fas fa-palette text-danger',
        'ui/ux': 'fas fa-object-group text-primary',
        'photoshop': 'fas fa-image text-info',
        'illustrator': 'fas fa-pen-nib text-warning',

        # Eğitim
        'öğretmen': 'fas fa-chalkboard-teacher text-success',
        'öğrenci': 'fas fa-user-graduate text-primary',
        'matematik': 'fas fa-square-root-alt text-dark',
        'fizik': 'fas fa-atom text-info',
        'kimya': 'fas fa-flask text-success',
        'biyoloji': 'fas fa-dna text-danger',

        # Sağlık
        'doktor': 'fas fa-user-md text-danger',
        'hemşire': 'fas fa-heartbeat text-danger',
        'eczacı': 'fas fa-pills text-warning',
        'psikolog': 'fas fa-brain text-info',
        'diyetisyen': 'fas fa-apple-alt text-success',

        # Güvenlik / Kamu
        'polis': 'fas fa-shield-alt text-primary',
        'asker': 'fas fa-fighter-jet text-dark',
        'avukat': 'fas fa-gavel text-warning',
        'hakim': 'fas fa-balance-scale text-secondary',

        # İş / Finans
        'muhasebe': 'fas fa-calculator text-dark',
        'finans': 'fas fa-chart-line text-success',
                'bankacı': 'fas fa-university text-primary',
        'girişimci': 'fas fa-lightbulb text-warning',
        'yönetici': 'fas fa-briefcase text-dark',

        # Medya / Sanat
        'müzik': 'fas fa-music text-info',
        'ressam': 'fas fa-paint-brush text-danger',
        'fotoğrafçı': 'fas fa-camera text-dark',
        'yazar': 'fas fa-pen text-secondary',
        'oyuncu': 'fas fa-theater-masks text-warning',

        # Spor
        'futbol': 'fas fa-futbol text-success',
        'basketbol': 'fas fa-basketball-ball text-warning',
        'fitness': 'fas fa-dumbbell text-danger',
        'yüzme': 'fas fa-swimmer text-info',
        'koşu': 'fas fa-running text-primary',

        # Diğer Popüler
        'şef': 'fas fa-utensils text-warning',
        'garson': 'fas fa-concierge-bell text-secondary',
        'pilot': 'fas fa-plane text-info',
        'şoför': 'fas fa-car text-dark',
        'tamirci': 'fas fa-tools text-secondary',
        'elektronik': 'fas fa-microchip text-dark',

        # Default / Genel
        'genel': 'fas fa-star text-warning',
        'diğer': 'fas fa-rocket text-danger',
        'bilinmeyen': 'fas fa-question-circle text-secondary',
        
        'cybersecurity': 'fas fa-user-secret text-dark',
        'siber güvenlik': 'fas fa-shield-virus text-danger',
        'kali': 'fas fa-skull text-dark',
        'cloud': 'fas fa-cloud text-info',
        
        # Sosyal Medya / Dijital Pazarlama
        'sosyal medya': 'fab fa-instagram text-danger',
        'pazarlama': 'fas fa-bullhorn text-warning',
        'seo': 'fas fa-search-dollar text-success',
        'video': 'fas fa-video text-dark',
        'youtube': 'fab fa-youtube text-danger',

        # Dil / Çeviri
        'ingilizce': 'fas fa-language text-primary',
        'tercüman': 'fas fa-comment-dots text-info',

        # El Sanatları / Hobiler
        'yemek': 'fas fa-hamburger text-warning',
        'kahve': 'fas fa-coffee text-brown',
        'seyahat': 'fas fa-map-marked-alt text-success',
        'kamp': 'fas fa-campground text-success',
    } # Sözlük burada kapandı.

    # Kullanıcının girdiği yetenekleri parçala
    skills = [s.strip() for s in value.split(',')]
    html_output = '<div class="d-flex flex-wrap gap-2 mt-2">'
    
    for skill in skills:
        # clean_skill yaparken # ve + işaretlerini silmiyoruz, sadece küçük harf yapıp boşlukları temizliyoruz
        clean_skill = skill.lower().replace(" ", "")
        
        # Sözlükte tam eşleşme ara, yoksa 'diğer' ikonu koy
        icon_class = icons.get(clean_skill, icons.get('diğer', 'fas fa-star'))
        
        html_output += f'''
            <div class="skill-badge px-3 py-1 bg-white border rounded-pill shadow-sm d-flex align-items-center gap-2" 
                 style="font-size: 12px; font-weight: 700; color: #1e293b; transition: 0.3s ease;">
                <i class="{icon_class}"></i> {skill}
            </div>
        '''
    
    html_output += '</div>'
    return mark_safe(html_output)