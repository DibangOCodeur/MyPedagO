document.addEventListener('DOMContentLoaded', function() {
    // Gestion des modaux
    const modals = document.querySelectorAll('.modal-overlay');
    const modalTriggers = document.querySelectorAll('[data-modal]');
    const modalCloses = document.querySelectorAll('.modal-close, [data-modal-close]');
    
    // Ouvrir les modaux
    modalTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const modalId = this.getAttribute('data-modal');
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
        });
    });
    
    // Fermer les modaux
    modalCloses.forEach(close => {
        close.addEventListener('click', function() {
            const modal = this.closest('.modal-overlay');
            if (modal) {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    });
    
    // Fermer en cliquant à l'extérieur
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    });
    
    // Animation des cartes
    const infoCards = document.querySelectorAll('.info-card, .module-card, .note-card');
    infoCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Validation des formulaires modaux
    const validateForm = document.querySelector('#validateModal form');
    const rejectForm = document.querySelector('#rejectModal form');
    
    if (validateForm) {
        validateForm.addEventListener('submit', function(e) {
            const textarea = this.querySelector('textarea');
            if (textarea && textarea.value.trim().length > 500) {
                e.preventDefault();
                alert('Les notes ne peuvent pas dépasser 500 caractères.');
            }
        });
    }
    
    if (rejectForm) {
        rejectForm.addEventListener('submit', function(e) {
            const textarea = this.querySelector('textarea');
            if (!textarea.value.trim()) {
                e.preventDefault();
                alert('Veuillez saisir la raison du rejet.');
                textarea.focus();
            } else if (textarea.value.trim().length < 10) {
                e.preventDefault();
                alert('La raison du rejet doit contenir au moins 10 caractères.');
                textarea.focus();
            }
        });
    }
    
    // Tooltips pour les badges de statut
    const statusBadges = document.querySelectorAll('.status-badge');
    statusBadges.forEach(badge => {
        badge.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.textContent;
            tooltip.style.position = 'absolute';
            tooltip.style.background = 'rgba(0, 0, 0, 0.8)';
            tooltip.style.color = 'white';
            tooltip.style.padding = '5px 10px';
            tooltip.style.borderRadius = '4px';
            tooltip.style.fontSize = '0.8rem';
            tooltip.style.zIndex = '1000';
            
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.left = `${rect.left + window.scrollX}px`;
            tooltip.style.top = `${rect.top + window.scrollY - tooltip.offsetHeight - 5}px`;
            
            this._tooltip = tooltip;
        });
        
        badge.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                this._tooltip.remove();
                this._tooltip = null;
            }
        });
    });
    
    // Mise en évidence des montants
    const amountValues = document.querySelectorAll('.amount-value, .total-value');
    amountValues.forEach(amount => {
        amount.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        amount.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    // Copie d'email
    const emailLinks = document.querySelectorAll('.email-link');
    emailLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (e.ctrlKey) {
                e.preventDefault();
                const email = this.textContent;
                navigator.clipboard.writeText(email).then(() => {
                    const originalText = this.textContent;
                    this.textContent = 'Email copié !';
                    setTimeout(() => {
                        this.textContent = originalText;
                    }, 2000);
                });
            }
        });
    });
    
    // Animation de chargement
    const mainContent = document.querySelector('.main-column');
    if (mainContent) {
        mainContent.style.opacity = '0';
        mainContent.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            mainContent.style.transition = 'all 0.5s ease';
            mainContent.style.opacity = '1';
            mainContent.style.transform = 'translateY(0)';
        }, 300);
    }
});