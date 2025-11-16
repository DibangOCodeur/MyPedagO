document.addEventListener('DOMContentLoaded', function() {
    // Auto-submit des filtres
    const statusSelect = document.getElementById('status');
    const anneeSelect = document.getElementById('annee');
    
    [statusSelect, anneeSelect].forEach(select => {
        if (select) {
            select.addEventListener('change', function() {
                this.form.submit();
            });
        }
    });
    
    // Gestion de la modal de soumission
    const submitModal = document.getElementById('submitModal');
    const submitButtons = document.querySelectorAll('.action-btn.small.submit');
    const modalPrecontratRef = document.getElementById('modalPrecontratRef');
    const submitForm = document.getElementById('submitForm');
    const modalClose = document.querySelector('.modal-close');
    const modalCancel = document.querySelector('.modal-btn.cancel');
    
    submitButtons.forEach(button => {
        button.addEventListener('click', function() {
            const precontratId = this.getAttribute('data-precontrat-id');
            const precontratRef = this.getAttribute('data-precontrat-ref');
            
            modalPrecontratRef.textContent = precontratRef;
            submitForm.action = `/gestion/precontrats/${precontratId}/soumettre/`;
            
            submitModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        });
    });
    
    // Fermeture de la modal
    function closeModal() {
        submitModal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
    
    if (modalClose) {
        modalClose.addEventListener('click', closeModal);
    }
    
    if (modalCancel) {
        modalCancel.addEventListener('click', closeModal);
    }
    
    submitModal.addEventListener('click', function(e) {
        if (e.target === submitModal) {
            closeModal();
        }
    });
    
    // Animation des cartes de statistiques
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Tooltips pour les boutons d'action
    const tooltips = document.querySelectorAll('[title]');
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', function(e) {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.getAttribute('title');
            tooltip.style.position = 'absolute';
            tooltip.style.background = 'rgba(0, 0, 0, 0.8)';
            tooltip.style.color = 'white';
            tooltip.style.padding = '5px 10px';
            tooltip.style.borderRadius = '4px';
            tooltip.style.fontSize = '0.8rem';
            tooltip.style.zIndex = '1000';
            tooltip.style.whiteSpace = 'nowrap';
            
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.left = `${rect.left + window.scrollX}px`;
            tooltip.style.top = `${rect.top + window.scrollY - tooltip.offsetHeight - 5}px`;
            
            this._tooltip = tooltip;
        });
        
        element.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                this._tooltip.remove();
                this._tooltip = null;
            }
        });
    });
    
    // Highlight des lignes au survol
    const tableRows = document.querySelectorAll('.table-row');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(5px)';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
    });
    
    // Confirmation avant actions importantes
    const deleteButtons = document.querySelectorAll('.action-btn.delete');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Êtes-vous sûr de vouloir supprimer ce précontrat ? Cette action est irréversible.')) {
                e.preventDefault();
            }
        });
    });
});