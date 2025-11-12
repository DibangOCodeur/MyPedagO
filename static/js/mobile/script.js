// Gestion du menu mobile
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.querySelector('.sidebar');
    const themeToggle = document.getElementById('themeToggle');
    const body = document.body;

    // Fonction pour mettre à jour l'heure en temps réel
    function updateCurrentTime() {
        const now = new Date();
        const dateString = now.toLocaleDateString('fr-FR', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
        const timeString = now.toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        const currentTimeElement = document.getElementById('currentTime');
        if (currentTimeElement) {
            currentTimeElement.textContent = `${dateString} à ${timeString}`;
        }
    }

    // Initialiser et mettre à jour l'heure
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    // Gestion du menu mobile
    if (mobileMenuToggle && sidebar) {
        mobileMenuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebar.classList.toggle('active');
            mobileMenuToggle.classList.toggle('active');
            
            // Animation de l'icône hamburger
            const icon = this.querySelector('i');
            if (sidebar.classList.contains('active')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });

        // Fermer le menu en cliquant à l'extérieur
        document.addEventListener('click', function(e) {
            if (sidebar.classList.contains('active') && 
                !sidebar.contains(e.target) && 
                e.target !== mobileMenuToggle &&
                !mobileMenuToggle.contains(e.target)) {
                sidebar.classList.remove('active');
                mobileMenuToggle.classList.remove('active');
                const icon = mobileMenuToggle.querySelector('i');
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });

        // Empêcher la fermeture quand on clique dans le menu
        sidebar.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        // Fermer le menu en appuyant sur Echap
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && sidebar.classList.contains('active')) {
                sidebar.classList.remove('active');
                mobileMenuToggle.classList.remove('active');
                const icon = mobileMenuToggle.querySelector('i');
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    }

    // Gestion des sous-menus
    const submenuToggles = document.querySelectorAll('.submenu-toggle');
    submenuToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const parentItem = this.closest('.nav-item.has-submenu');
            
            // Fermer les autres sous-menus
            document.querySelectorAll('.nav-item.has-submenu').forEach(item => {
                if (item !== parentItem && item.classList.contains('open')) {
                    item.classList.remove('open');
                }
            });
            
            // Ouvrir/fermer le sous-menu actuel
            parentItem.classList.toggle('open');
            
            // Sur mobile, garder le menu ouvert après avoir cliqué sur un sous-menu
            if (window.innerWidth <= 768) {
                e.stopPropagation();
            }
        });
    });

    // Fermer le menu mobile en cliquant sur un lien (sauf les sous-menus)
    document.querySelectorAll('.sidebar-nav .nav-link:not(.submenu-toggle)').forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('active');
                mobileMenuToggle.classList.remove('active');
                const icon = mobileMenuToggle.querySelector('i');
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    });

    // Gestion du thème sombre/clair
    if (themeToggle) {
        // Vérifier le thème sauvegardé ou la préférence système
        const currentTheme = localStorage.getItem('theme') || 
                           (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        setTheme(currentTheme);
        
        themeToggle.addEventListener('click', function() {
            const newTheme = body.classList.contains('dark-theme') ? 'light' : 'dark';
            setTheme(newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Animation du bouton
            themeToggle.classList.add('pulse');
            setTimeout(() => themeToggle.classList.remove('pulse'), 500);
        });
        
        function setTheme(theme) {
            if (theme === 'dark') {
                body.classList.add('dark-theme');
                themeToggle.querySelector('.fa-moon').style.display = 'none';
                themeToggle.querySelector('.fa-sun').style.display = 'inline-block';
            } else {
                body.classList.remove('dark-theme');
                themeToggle.querySelector('.fa-moon').style.display = 'inline-block';
                themeToggle.querySelector('.fa-sun').style.display = 'none';
            }
        }
    }

    // Gestion du redimensionnement de la fenêtre
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            // Sur desktop, s'assurer que le menu est visible
            if (window.innerWidth > 768) {
                sidebar.classList.remove('active');
                if (mobileMenuToggle) {
                    mobileMenuToggle.classList.remove('active');
                    const icon = mobileMenuToggle.querySelector('i');
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            }
        }, 250);
    });

    // Animation de chargement
    setTimeout(() => {
        document.body.style.opacity = '1';
    }, 100);
});

// Animation pour le bouton de notification
document.addEventListener('DOMContentLoaded', function() {
    const notificationBell = document.querySelector('.user-notification');
    if (notificationBell) {
        notificationBell.addEventListener('click', function() {
            this.classList.add('shake');
            setTimeout(() => {
                this.classList.remove('shake');
            }, 500);
        });
    }
});

// Gestion des modales (si présentes)
document.addEventListener('DOMContentLoaded', function() {
    // Fermeture des modales
    document.querySelectorAll('.modal-close, .modal-btn.cancel').forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal-overlay');
            if (modal) {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    });

    // Fermer la modale en cliquant à l'extérieur
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    });

    // Empêcher la fermeture de la modale en cliquant à l'intérieur
    document.querySelectorAll('.modal-content').forEach(modalContent => {
        modalContent.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    });
});