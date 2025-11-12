document.addEventListener('DOMContentLoaded', function() {
    // Mode Sombre/Clair
    const themeToggle = document.querySelector('.theme-toggle');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Vérifier le préférence système
    if (prefersDarkScheme.matches) {
        document.body.classList.add('dark-mode');
        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    }
    
    // Basculer entre les modes
    themeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        
        if (document.body.classList.contains('dark-mode')) {
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            localStorage.setItem('theme', 'dark');
        } else {
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
            localStorage.setItem('theme', 'light');
        }
    });
    
    // Vérifier le stockage local pour le thème
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'dark') {
        document.body.classList.add('dark-mode');
        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    } else if (currentTheme === 'light') {
        document.body.classList.remove('dark-mode');
        themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
    }
    
    // Gestion des sous-menus
    const submenuToggles = document.querySelectorAll('.has-submenu > a');
    
    submenuToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const parent = this.parentElement;
            
            // Fermer les autres sous-menus
            document.querySelectorAll('.has-submenu').forEach(item => {
                if (item !== parent) {
                    item.classList.remove('active');
                }
            });
            
            parent.classList.toggle('active');
        });
    });
    
    // Animation des cartes au scroll
    const animateElements = document.querySelectorAll('.animate-card');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationPlayState = 'running';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    animateElements.forEach(element => {
        observer.observe(element);
    });
    
    // Simulation de données dynamiques
    function updateStats() {
        // Exemple de mise à jour dynamique
        const stats = {
            classes: 12 + Math.floor(Math.random() * 3),
            contracts: 47 + Math.floor(Math.random() * 5),
            courses: 156 + Math.floor(Math.random() * 10),
            completed: 89 + Math.floor(Math.random() * 7)
        };
        
        document.querySelector('.stat-number:nth-child(1)').textContent = stats.classes;
        document.querySelector('.stat-number:nth-child(2)').textContent = stats.contracts;
        document.querySelector('.stat-number:nth-child(3)').textContent = stats.courses;
        document.querySelector('.stat-number:nth-child(4)').textContent = stats.completed;
        
        // Mettre à jour la barre de progression
        const progressValue = Math.min(Math.floor(Math.random() * 100), 100);
        document.querySelector('.progress-bar-fill').style.width = `${progressValue}%`;
        document.querySelector('.progress-value').textContent = `${progressValue}%`;
    }
    
    // Mettre à jour les stats toutes les 30 secondes (simulation)
    setInterval(updateStats, 30000);
    
    // Gestion des boutons de validation
    document.querySelectorAll('.btn-validate').forEach(btn => {
        btn.addEventListener('click', function() {
            const card = this.closest('.validation-item');
            card.querySelector('.status-badge').classList.remove('status-pending');
            card.querySelector('.status-badge').classList.add('status-validated');
            card.querySelector('.status-badge').textContent = 'Validé';
            this.textContent = 'Validé';
            this.style.backgroundColor = '#20c997';
            this.style.color = 'white';
            this.disabled = true;
            
            // Animation de confirmation
            card.style.boxShadow = '0 0 0 3px rgba(32, 201, 151, 0.3)';
            setTimeout(() => {
                card.style.boxShadow = 'none';
            }, 1000);
        });
    });
    
    // Gestion des boutons de rappel
    document.querySelectorAll('.btn-remind').forEach(btn => {
        btn.addEventListener('click', function() {
            const card = this.closest('.validation-item');
            
            // Animation de rappel
            this.innerHTML = '<i class="fas fa-check"></i> Rappel envoyé';
            this.style.backgroundColor = '#ffc107';
            this.style.color = '#343a40';
            
            setTimeout(() => {
                this.innerHTML = '<i class="fas fa-bell"></i> Relancer';
            }, 2000);
        });
    });
    
    // Menu mobile (pour les écrans petits)
    const mobileMenuToggle = document.createElement('div');
    mobileMenuToggle.className = 'mobile-menu-toggle';
    mobileMenuToggle.innerHTML = '<i class="fas fa-bars"></i>';
    document.querySelector('.top-bar').prepend(mobileMenuToggle);
    
    mobileMenuToggle.addEventListener('click', function() {
        document.querySelector('.sidebar').classList.toggle('active');
    });
    
    // Simuler des notifications
    function showNotification() {
        const notification = document.createElement('div');
        notification.className = 'notification-toast';
        notification.innerHTML = `
            <div class="notification-icon">
                <i class="fas fa-bell"></i>
            </div>
            <div class="notification-content">
                <h4>Nouveau contrat à valider</h4>
                <p>Le professeur Diallo a soumis son syllabus pour le cours d'Algorithmique</p>
            </div>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 5000);
        
        notification.querySelector('.notification-close').addEventListener('click', function() {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
    }
    
    // Afficher une notification après 3 secondes (simulation)
    setTimeout(showNotification, 3000);
    
    // Initialiser les graphiques (simulation)
    function initCharts() {
        console.log("Initialisation des graphiques...");
        // Ici vous intégrerez Chart.js avec des données réelles
    }
    
    initCharts();
});

// Styles dynamiques pour les notifications
const notificationStyle = document.createElement('style');
notificationStyle.textContent = `
.notification-toast {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 5px 20px rgba(0, 0, 0, 0.15);
    display: flex;
    align-items: center;
    padding: 15px;
    width: 350px;
    transform: translateX(120%);
    transition: transform 0.3s ease;
    z-index: 1000;
}

.dark-mode .notification-toast {
    background: #2c3034;
    box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
}

.notification-toast.show {
    transform: translateX(0);
}

.notification-icon {
    font-size: 1.5rem;
    color: #20c997;
    margin-right: 15px;
}

.notification-content h4 {
    margin: 0 0 5px 0;
    font-size: 1rem;
}

.notification-content p {
    margin: 0;
    font-size: 0.85rem;
    color: #6c757d;
}

.dark-mode .notification-content p {
    color: #adb5bd;
}

.notification-close {
    background: none;
    border: none;
    color: #6c757d;
    font-size: 1rem;
    margin-left: auto;
    cursor: pointer;
    padding: 5px;
}

.dark-mode .notification-close {
    color: #adb5bd;
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
    }
    to {
        transform: translateX(0);
    }
}

@keyframes slideOut {
    from {
        transform: translateX(0);
    }
    to {
        transform: translateX(120%);
    }
}
`;
document.head.appendChild(notificationStyle);


// Styles dynamiques pour les cartes animées
document.addEventListener('DOMContentLoaded', function() {
    // Thème sombre/clair
    const themeToggle = document.getElementById('themeToggle');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Vérifier le thème système ou le localStorage
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'dark' || (!currentTheme && prefersDarkScheme.matches)) {
        document.body.classList.add('dark-theme');
    }
    
    // Basculer le thème
    themeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-theme');
        const theme = document.body.classList.contains('dark-theme') ? 'dark' : 'light';
        localStorage.setItem('theme', theme);
    });
    
    // Menu mobile
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.querySelector('.sidebar');
    
    mobileMenuToggle.addEventListener('click', function() {
        sidebar.classList.toggle('active');
    });
    
    // Sous-menus
    const submenuToggles = document.querySelectorAll('.submenu-toggle');
    
    submenuToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const parentItem = this.closest('.nav-item.has-submenu');
            parentItem.classList.toggle('open');
            
            // Fermer les autres sous-menus ouverts
            document.querySelectorAll('.nav-item.has-submenu').forEach(item => {
                if (item !== parentItem && item.classList.contains('open')) {
                    item.classList.remove('open');
                }
            });
        });
    });
    
    // Fermer le menu mobile lorsqu'un lien est cliqué (sauf pour les sous-menus)
    document.querySelectorAll('.sidebar-nav .nav-link:not(.submenu-toggle)').forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('active');
            }
        });
    });
    
    // Modal
    const modalOverlay = document.getElementById('actionModal');
    const modalButtons = document.querySelectorAll('.action-btn, .stat-menu');
    const modalClose = document.querySelector('.modal-close');
    const modalCancel = document.querySelector('.modal-btn.cancel');
    
    function openModal() {
        modalOverlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
    
    function closeModal() {
        modalOverlay.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
    
    modalButtons.forEach(button => {
        button.addEventListener('click', openModal);
    });
    
    modalClose.addEventListener('click', closeModal);
    modalCancel.addEventListener('click', closeModal);
    
    modalOverlay.addEventListener('click', function(e) {
        if (e.target === modalOverlay) {
            closeModal();
        }
    });
    
    // Animation au chargement
    setTimeout(() => {
        document.body.style.opacity = '1';
    }, 100);
});