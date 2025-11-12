// Gestion du thème clair/sombre
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.querySelector('.sidebar');
    const submenuToggles = document.querySelectorAll('.submenu-toggle');
    const modalOverlay = document.getElementById('actionModal');
    const modalClose = document.querySelector('.modal-close');
    const modalCancel = document.querySelector('.modal-btn.cancel');
    const actionButtons = document.querySelectorAll('.action-btn, .evaluation-action, .btn');
    const statMenus = document.querySelectorAll('.stat-menu');
    const sectionMenus = document.querySelectorAll('.section-menu');

    // Initialisation du thème
    function initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        updateThemeToggleIcon(savedTheme);
    }

    // Mise à jour de l'icône du bouton thème
    function updateThemeToggleIcon(theme) {
        const moonIcon = themeToggle.querySelector('.fa-moon');
        const sunIcon = themeToggle.querySelector('.fa-sun');
        
        if (theme === 'dark') {
            moonIcon.style.display = 'none';
            sunIcon.style.display = 'block';
        } else {
            moonIcon.style.display = 'block';
            sunIcon.style.display = 'none';
        }
    }

    // Basculer le thème
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeToggleIcon(newTheme);
    }

    // Gestion du menu mobile
    function toggleMobileMenu() {
        sidebar.classList.toggle('active');
    }

    // Gestion des sous-menus
    function toggleSubmenu(event) {
        event.preventDefault();
        const parent = this.parentElement;
        parent.classList.toggle('active');
        
        // Fermer les autres sous-menus
        const otherSubmenus = document.querySelectorAll('.has-submenu.active');
        otherSubmenus.forEach(submenu => {
            if (submenu !== parent) {
                submenu.classList.remove('active');
            }
        });
    }

    // Gestion des modals
    function openModal(title) {
        const modalTitle = document.getElementById('modalTitle');
        modalTitle.textContent = title;
        modalOverlay.classList.add('active');
    }

    function closeModal() {
        modalOverlay.classList.remove('active');
    }

    // Gestion des menus contextuels
    function toggleContextMenu(event) {
        event.stopPropagation();
        // Implémentation des menus contextuels pour les statistiques et sections
        console.log('Menu contextuel ouvert pour:', this.closest('.stat-card, section'));
    }

    // Événements
    themeToggle.addEventListener('click', toggleTheme);
    mobileMenuToggle.addEventListener('click', toggleMobileMenu);
    
    submenuToggles.forEach(toggle => {
        toggle.addEventListener('click', toggleSubmenu);
    });

    if (modalClose) modalClose.addEventListener('click', closeModal);
    if (modalCancel) modalCancel.addEventListener('click', closeModal);

    // Fermer le modal en cliquant à l'extérieur
    modalOverlay.addEventListener('click', function(event) {
        if (event.target === modalOverlay) {
            closeModal();
        }
    });

    // Gestion des actions rapides
    actionButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const buttonText = this.textContent.trim() || this.querySelector('i').className;
            openModal(buttonText);
        });
    });

    // Menus contextuels
    statMenus.forEach(menu => {
        menu.addEventListener('click', toggleContextMenu);
    });

    sectionMenus.forEach(menu => {
        menu.addEventListener('click', toggleContextMenu);
    });

    // Fermer le sidebar en cliquant à l'extérieur sur mobile
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 1024 && 
            !sidebar.contains(event.target) && 
            !mobileMenuToggle.contains(event.target) &&
            sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
        }
    });

    // Fermer les sous-menus en cliquant à l'extérieur
    document.addEventListener('click', function(event) {
        if (!event.target.closest('.has-submenu')) {
            document.querySelectorAll('.has-submenu.active').forEach(menu => {
                menu.classList.remove('active');
            });
        }
    });

    // Initialisation
    initTheme();

    // Animation au chargement
    setTimeout(() => {
        document.body.style.opacity = '1';
    }, 100);
});

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

// Effet de fondu au chargement
window.addEventListener('load', function() {
    document.body.style.transition = 'opacity 0.3s ease';
    document.body.style.opacity = '1';
});

// Gestion du redimensionnement
window.addEventListener('resize', function() {
    if (window.innerWidth > 1024) {
        document.querySelector('.sidebar').classList.remove('active');
    }
});