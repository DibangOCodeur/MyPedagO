// Gestion des sous-menus - Version améliorée
document.addEventListener('DOMContentLoaded', function() {
    // Sélectionner tous les éléments avec sous-menu
    const submenuToggles = document.querySelectorAll('.submenu-toggle');
    
    submenuToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const parentItem = this.closest('.nav-item.has-submenu');
            const submenu = this.nextElementSibling;
            const icon = this.querySelector('.submenu-icon');
            
            // Vérifier si le sous-menu est déjà ouvert
            const isAlreadyOpen = parentItem.classList.contains('open');
            
            // Fermer tous les autres sous-menus
            document.querySelectorAll('.nav-item.has-submenu.open').forEach(openItem => {
                if (openItem !== parentItem) {
                    closeSubmenu(openItem);
                }
            });
            
            // Basculer l'état actuel
            if (isAlreadyOpen) {
                closeSubmenu(parentItem);
            } else {
                openSubmenu(parentItem, submenu, icon);
            }
        });
    });
    
    // Fonction pour ouvrir un sous-menu
    function openSubmenu(parentItem, submenu, icon) {
        parentItem.classList.add('open');
        submenu.style.maxHeight = submenu.scrollHeight + 'px';
        icon.style.transform = 'rotate(180deg)';
        
        // Ajouter une animation plus fluide
        submenu.style.opacity = '1';
        submenu.style.transform = 'translateY(0)';
    }
    
    // Fonction pour fermer un sous-menu
    function closeSubmenu(parentItem) {
        const submenu = parentItem.querySelector('.submenu');
        const icon = parentItem.querySelector('.submenu-icon');
        
        parentItem.classList.remove('open');
        submenu.style.maxHeight = '0';
        submenu.style.opacity = '0';
        submenu.style.transform = 'translateY(-5px)';
        icon.style.transform = 'rotate(0deg)';
    }
    
    // Fermer les sous-menus en cliquant ailleurs
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.nav-item.has-submenu')) {
            document.querySelectorAll('.nav-item.has-submenu.open').forEach(item => {
                closeSubmenu(item);
            });
        }
    });
    
    // Fermer les sous-menus avec la touche Échap
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.nav-item.has-submenu.open').forEach(item => {
                closeSubmenu(item);
            });
        }
    });
    
    // Gestion du menu mobile
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (mobileMenuToggle && sidebar) {
        mobileMenuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
        });
        
        // Fermer le menu mobile en cliquant sur un lien
        sidebar.addEventListener('click', function(e) {
            if (e.target.tagName === 'A' && window.innerWidth <= 768) {
                sidebar.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
        
        // Fermer le menu mobile en cliquant en dehors
        document.addEventListener('click', function(e) {
            if (sidebar.classList.contains('active') && 
                !sidebar.contains(e.target) && 
                e.target !== mobileMenuToggle && 
                !mobileMenuToggle.contains(e.target)) {
                sidebar.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }
    
    // Gestion responsive des sous-menus
    function handleResize() {
        if (window.innerWidth > 768) {
            // Sur desktop, réinitialiser certains styles
            document.body.style.overflow = '';
        }
    }
    
    window.addEventListener('resize', handleResize);
    handleResize();
});

// Gestion du thème (si pas déjà inclus)
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-theme');
            
            // Sauvegarder la préférence
            const isDark = document.body.classList.contains('dark-theme');
            localStorage.setItem('darkTheme', isDark);
        });
        
        // Charger la préférence de thème
        const darkTheme = localStorage.getItem('darkTheme') === 'true';
        if (darkTheme) {
            document.body.classList.add('dark-theme');
        }
    }
});