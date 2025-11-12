// ============================================================================
// WIZARD DE CRÉATION DE PRÉCONTRAT - VERSION CORRIGÉE ET ISOLÉE
// Ce script est isolé pour éviter les conflits avec script.js externe
// ============================================================================

(function() {
    'use strict';
    
    // ===== PROTECTION CONTRE LES ERREURS DU SCRIPT.JS EXTERNE =====
    // Intercepter les erreurs du script.js global pour ne pas bloquer notre wizard
    const originalConsoleError = console.error;
    console.error = function(...args) {
        // Ignorer les erreurs de script.js qui ne concernent pas notre wizard
        const errorMessage = args.join(' ');
        if (!errorMessage.includes('precontrat') && !errorMessage.includes('wizard')) {
            // On log quand même mais sans bloquer
            originalConsoleError.apply(console, args);
        }
    };
    
    // ===== VARIABLES GLOBALES =====
    let currentStep = 1;
    let selectedModules = [];
    let modulesData = [];
    let formData = {
        professeur: null,
        classe: null,
        modules: []
    };
    
    // ===== CONFIGURATION =====
    const CONFIG = {
        animationDuration: 600,
        apiEndpoint: '/gestion/precontrat/classes/{id}/modules/',
        csrfToken: document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
        totalSteps: 4
    };
    
    // ===== INITIALISATION SÉCURISÉE =====
    function safeInit() {
        try {
            console.log('🚀 Initialisation du wizard de création de précontrat');
            console.log('📍 API Endpoint configuré:', CONFIG.apiEndpoint);
            
            initializeEventListeners();
            setupFormValidation();
            updateProgressBar();
            animatePageLoad();
            
            console.log('✅ Wizard initialisé avec succès');
        } catch (error) {
            console.error('❌ Erreur lors de l\'initialisation du wizard:', error);
        }
    }
    
    // ===== UTILITAIRE: ACCÈS SÉCURISÉ AUX ÉLÉMENTS DOM =====
    function safeGetElement(id, required = false) {
        const element = document.getElementById(id);
        if (!element && required) {
            console.warn(`⚠️ Élément requis non trouvé: ${id}`);
        }
        return element;
    }
    
    function safeSetText(id, text) {
        const element = safeGetElement(id);
        if (element) {
            element.textContent = text;
        }
    }
    
    function safeSetHTML(id, html) {
        const element = safeGetElement(id);
        if (element) {
            element.innerHTML = html;
        }
    }
    
    // ===== ÉCOUTEURS D'ÉVÉNEMENTS =====
    function initializeEventListeners() {
        // Sélection du professeur
        const profSelect = safeGetElement('id_professeur');
        if (profSelect) {
            profSelect.addEventListener('change', handleProfesseurChange);
        }
        
        // Sélection de la classe
        const classeSelect = safeGetElement('id_classe');
        if (classeSelect) {
            classeSelect.addEventListener('change', handleClasseChange);
        }
        
        // Boutons de navigation
        setupNavigationButtons();
        
        // Soumission du formulaire
        const form = safeGetElement('precontrat-form');
        if (form) {
            form.addEventListener('submit', handleFormSubmit);
        }
        
        // Gestion des clics sur les modules (délégation d'événements)
        document.addEventListener('click', handleModuleCardClick);
        
        // Raccourcis clavier
        document.addEventListener('keydown', handleKeyboardShortcuts);
    }
    
    // ===== NAVIGATION ENTRE LES ÉTAPES =====
    function setupNavigationButtons() {
        const buttons = [
            { id: 'btn-step-1-next', action: () => validateAndShowStep(1, 2) },
            { id: 'btn-step-2-prev', action: () => showStep(1) },
            { id: 'btn-step-2-next', action: () => validateAndShowStep(2, 3) },
            { id: 'btn-step-3-prev', action: () => showStep(2) },
            { id: 'btn-step-3-next', action: () => validateAndShowStep(3, 4) },
            { id: 'btn-step-4-prev', action: () => showStep(3) }
        ];
        
        buttons.forEach(({ id, action }) => {
            const button = safeGetElement(id);
            if (button) {
                button.addEventListener('click', action);
            }
        });
    }
    
    function validateAndShowStep(currentStepNum, nextStepNum) {
        if (validateStep(currentStepNum)) {
            showStep(nextStepNum);
        }
    }
    
    function showStep(step) {
        if (step < 1 || step > CONFIG.totalSteps) return;
        
        // Animation de sortie de l'étape actuelle
        const currentContent = document.querySelector(`.step-content[data-step="${currentStep}"]`);
        if (currentContent) {
            currentContent.style.animation = 'fadeOut 0.3s ease';
            
            setTimeout(() => {
                currentContent.classList.remove('active');
                currentContent.style.animation = '';
                
                // Afficher la nouvelle étape
                const newContent = document.querySelector(`.step-content[data-step="${step}"]`);
                if (newContent) {
                    newContent.classList.add('active');
                    newContent.style.animation = 'fadeInUp 0.4s ease';
                }
                
                // Mettre à jour l'étape actuelle
                currentStep = step;
                updateProgressBar();
                
                // Actions spéciales selon l'étape
                handleStepChange(step);
                
                // Scroll vers le haut
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }, 300);
        }
    }
    
    function handleStepChange(step) {
        if (step === 3 && formData.classe) {
            // Charger les modules quand on arrive à l'étape 3
            loadModules();
        } else if (step === 4) {
            // Générer le récapitulatif à l'étape 4
            generateRecap();
        }
    }
    
    function updateProgressBar() {
        // Mettre à jour l'indicateur d'étapes
        document.querySelectorAll('.step-item').forEach(item => {
            const stepNum = parseInt(item.dataset.step);
            if (stepNum < currentStep) {
                item.classList.add('completed');
                item.classList.remove('active');
            } else if (stepNum === currentStep) {
                item.classList.add('active');
                item.classList.remove('completed');
            } else {
                item.classList.remove('active', 'completed');
            }
        });
    }
    
    function validateStep(step) {
        switch(step) {
            case 1:
                if (!formData.professeur) {
                    showNotification('Veuillez sélectionner un professeur', 'warning');
                    return false;
                }
                return true;
                
            case 2:
                if (!formData.classe) {
                    showNotification('Veuillez sélectionner une classe', 'warning');
                    return false;
                }
                return true;
                
            case 3:
                if (selectedModules.length === 0) {
                    showNotification('Veuillez sélectionner au moins un module', 'warning');
                    return false;
                }
                return true;
                
            default:
                return true;
        }
    }
    
    // ===== GESTION DU PROFESSEUR =====
    function handleProfesseurChange(event) {
        const select = event.target;
        const selectedOption = select.options[select.selectedIndex];
        
        if (selectedOption && selectedOption.value) {
            formData.professeur = {
                id: selectedOption.value,
                nom: selectedOption.dataset.nom || selectedOption.text,
                email: selectedOption.dataset.email || ''
            };
            
            displayProfesseurInfo(formData.professeur);
            updateSummaryProfesseur(formData.professeur);
            enableButton('btn-step-1-next');
        } else {
            formData.professeur = null;
            hideProfesseurInfo();
            disableButton('btn-step-1-next');
        }
    }
    
    function displayProfesseurInfo(profData) {
        const profInfo = safeGetElement('prof-info');
        const profNom = safeGetElement('prof-nom');
        const profEmail = safeGetElement('prof-email');
        const profInitials = safeGetElement('prof-initials');
        
        if (profNom) profNom.textContent = profData.nom;
        if (profEmail) profEmail.textContent = profData.email;
        
        // Générer les initiales
        if (profInitials) {
            const names = profData.nom.split(' ');
            const initials = names.map(n => n.charAt(0)).join('').substring(0, 2).toUpperCase();
            profInitials.textContent = initials;
        }
        
        if (profInfo) {
            profInfo.classList.remove('d-none');
            profInfo.style.animation = 'slideInDown 0.5s ease';
        }
    }
    
    function hideProfesseurInfo() {
        const profInfo = safeGetElement('prof-info');
        if (profInfo) {
            profInfo.classList.add('d-none');
        }
    }
    
    function updateSummaryProfesseur(profData) {
        const summaryProf = safeGetElement('summary-prof');
        if (summaryProf) {
            summaryProf.textContent = profData.nom;
            summaryProf.classList.remove('text-secondary');
            summaryProf.classList.add('text-dark', 'fw-bold');
        }
    }
    
    // ===== GESTION DE LA CLASSE =====
    function handleClasseChange(event) {
        const select = event.target;
        const selectedOption = select.options[select.selectedIndex];
        
        if (selectedOption && selectedOption.value) {
            formData.classe = {
                id: selectedOption.value,
                nom: selectedOption.text,
                niveau: selectedOption.dataset.niveau || '',
                filiere: selectedOption.dataset.filiere || ''
            };
            
            displayClasseInfo(formData.classe);
            updateSummaryClasse(formData.classe);
            enableButton('btn-step-2-next');
        } else {
            formData.classe = null;
            hideClasseInfo();
            disableButton('btn-step-2-next');
        }
    }
    
    function displayClasseInfo(classeData) {
        safeSetText('classe-nom', classeData.nom);
        safeSetText('classe-niveau', classeData.niveau);
        safeSetText('classe-filiere', classeData.filiere);
        
        const classeInfo = safeGetElement('classe-info');
        if (classeInfo) {
            classeInfo.classList.remove('d-none');
            classeInfo.style.animation = 'slideInDown 0.5s ease';
        }
    }
    
    function hideClasseInfo() {
        const classeInfo = safeGetElement('classe-info');
        if (classeInfo) {
            classeInfo.classList.add('d-none');
        }
    }
    
    function updateSummaryClasse(classeData) {
        const summaryClasse = safeGetElement('summary-classe');
        const summaryClasseDetails = safeGetElement('summary-classe-details');
        
        if (summaryClasse) {
            summaryClasse.textContent = classeData.nom;
            summaryClasse.classList.remove('text-secondary');
            summaryClasse.classList.add('text-dark', 'fw-bold');
        }
        
        if (summaryClasseDetails) {
            summaryClasseDetails.textContent = `${classeData.niveau} - ${classeData.filiere}`;
            summaryClasseDetails.classList.remove('d-none');
        }
    }
    
    // ===== CHARGEMENT DES MODULES =====
    function loadModules() {
        if (!formData.classe || !formData.classe.id) {
            console.warn('⚠️ Pas de classe sélectionnée');
            return;
        }
        
        showLoading();
        
        const url = `/gestion/precontrat/classes/${formData.classe.id}/modules/`;
        console.log('📡 Chargement des modules depuis:', url);
        
        fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.csrfToken
            },
            credentials: 'same-origin'
        })
        .then(response => {
            console.log('📥 Réponse reçue:', response.status, response.statusText);
            
            if (!response.ok) {
                throw new Error(`Erreur HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('✅ Données reçues:', data);
            hideLoading();
            
            if (data.success) {
                if (data.modules && data.modules.length > 0) {
                    console.log(`📚 ${data.modules.length} module(s) trouvé(s) pour la classe "${data.classe}"`);
                    
                    modulesData = data.modules;
                    renderModules(data.modules);
                    showModulesContainer();
                    
                    showNotification(
                        `✅ ${data.count} module(s) chargé(s) avec succès`, 
                        'success'
                    );
                } else {
                    console.warn('⚠️ Aucun module disponible pour cette classe');
                    showEmptyModules();
                    showNotification(
                        'Aucun module trouvé pour cette classe', 
                        'warning'
                    );
                }
            } else {
                console.error('❌ Erreur API:', data.error);
                showEmptyModules();
                showNotification(
                    `Erreur: ${data.error || 'Erreur inconnue'}`, 
                    'danger'
                );
            }
        })
        .catch(error => {
            console.error('❌ Erreur de chargement:', error);
            hideLoading();
            showEmptyModules();
            showNotification(
                `Erreur lors du chargement des modules: ${error.message}`, 
                'danger'
            );
        });
    }
    
    // ===== AFFICHAGE DES MODULES =====
    function showLoading() {
        const loading = safeGetElement('modules-loading');
        const container = safeGetElement('modules-container');
        const empty = safeGetElement('modules-empty');
        
        if (loading) loading.classList.remove('d-none');
        if (container) container.classList.add('d-none');
        if (empty) empty.classList.add('d-none');
    }
    
    function hideLoading() {
        const loading = safeGetElement('modules-loading');
        if (loading) loading.classList.add('d-none');
    }
    
    function showModulesContainer() {
        const container = safeGetElement('modules-container');
        const loading = safeGetElement('modules-loading');
        const empty = safeGetElement('modules-empty');
        
        if (container) container.classList.remove('d-none');
        if (loading) loading.classList.add('d-none');
        if (empty) empty.classList.add('d-none');
        
        console.log('✅ Container de modules affiché');
    }
    
    function showEmptyModules() {
        const container = safeGetElement('modules-container');
        const loading = safeGetElement('modules-loading');
        const empty = safeGetElement('modules-empty');
        
        if (loading) loading.classList.add('d-none');
        if (container) container.classList.add('d-none');
        if (empty) empty.classList.remove('d-none');
    }
    
    function renderModules(modules) {
        const container = safeGetElement('modules-list', true);
        if (!container) {
            console.error('❌ Container modules-list non trouvé - impossible d\'afficher les modules');
            return;
        }
        
        console.log('🎨 Rendu de', modules.length, 'modules dans le container');
        container.innerHTML = '';
        
        // Grouper les modules par UE
        const modulesByUE = {};
        modules.forEach(module => {
            const ueNom = module.ue_nom || 'Sans UE';
            if (!modulesByUE[ueNom]) {
                modulesByUE[ueNom] = [];
            }
            modulesByUE[ueNom].push(module);
        });
        
        // Afficher les modules groupés par UE
        Object.keys(modulesByUE).forEach(ueNom => {
            // En-tête de l'UE
            const ueHeader = document.createElement('h6');
            ueHeader.className = 'mt-4 mb-3 text-primary fw-bold';
            ueHeader.innerHTML = `<i class="bi bi-book"></i> ${ueNom}`;
            container.appendChild(ueHeader);
            
            // Liste des modules de cette UE
            modulesByUE[ueNom].forEach(module => {
                const moduleCard = createModuleCard(module);
                container.appendChild(moduleCard);
            });
        });
        
        console.log('✅ Modules rendus avec succès');
    }
    
    function createModuleCard(module) {
        const card = document.createElement('div');
        card.className = 'module-card card mb-3 border hover-shadow';
        card.dataset.moduleId = module.id;
        card.style.cursor = 'pointer';
        card.style.transition = 'all 0.3s ease';
        
        const totalHeures = (module.volume_cm || 0) + (module.volume_td || 0);
        
        card.innerHTML = `
            <div class="card-body">
                <div class="form-check">
                    <input 
                        class="form-check-input module-checkbox" 
                        type="checkbox" 
                        value="${module.id}"
                        id="module-${module.id}"
                    >
                    <label class="form-check-label w-100" for="module-${module.id}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <strong class="text-primary">${module.code}</strong> - ${module.nom}
                            </div>
                            <small class="text-muted ms-2">${totalHeures}h</small>
                        </div>
                    </label>
                </div>
                <div class="module-details mt-2 ms-4">
                    <small class="text-muted">
                        <i class="bi bi-clock"></i> 
                        CM: <strong>${module.volume_cm}h</strong> | 
                        TD: <strong>${module.volume_td}h</strong> | 
                    </small>
                </div>
            </div>
        `;
        
        return card;
    }
    
    // ===== GESTION DES MODULES =====
    function handleModuleCardClick(event) {
        // Détecter si le clic est sur une carte de module ou une checkbox
        const moduleCard = event.target.closest('.module-card');
        if (!moduleCard) return;
        
        const checkbox = moduleCard.querySelector('.module-checkbox');
        if (!checkbox) return;
        
        // Si le clic n'est pas directement sur la checkbox, la toggle
        if (event.target !== checkbox) {
            checkbox.checked = !checkbox.checked;
        }
        
        // Gérer la sélection/désélection
        toggleModuleSelection(checkbox.value, checkbox.checked, moduleCard);
    }
    
    function toggleModuleSelection(moduleId, isSelected, moduleCard) {
        if (isSelected) {
            // Ajouter le module
            if (!selectedModules.includes(moduleId)) {
                selectedModules.push(moduleId);
                console.log('✅ Module', moduleId, 'ajouté');
            }
            moduleCard.classList.add('selected');
            moduleCard.style.backgroundColor = '#e7f3ff';
            moduleCard.style.borderColor = '#0d6efd';
        } else {
            // Retirer le module
            const index = selectedModules.indexOf(moduleId);
            if (index > -1) {
                selectedModules.splice(index, 1);
                console.log('❌ Module', moduleId, 'retiré');
            }
            moduleCard.classList.remove('selected');
            moduleCard.style.backgroundColor = '';
            moduleCard.style.borderColor = '';
        }
        
        // Mettre à jour l'interface
        updateModuleSelection();
    }
    
    function updateModuleSelection() {
        updateSelectedCount();
        updateSelectedList();
        updateTotalHours();
        updateTotalAmount();
        
        // Activer/désactiver le bouton suivant
        if (selectedModules.length > 0) {
            enableButton('btn-step-3-next');
        } else {
            disableButton('btn-step-3-next');
        }
    }
    
    function updateSelectedCount() {
        safeSetText('selected-count', selectedModules.length.toString());
    }
    
    function updateSelectedList() {
        const listElem = safeGetElement('selected-modules-list');
        if (!listElem) return;
        
        if (selectedModules.length === 0) {
            listElem.innerHTML = `
                <div class="empty-state py-3 text-center">
                    <i class="bi bi-inbox fs-4 text-muted"></i>
                    <p class="mb-0 small text-muted mt-2">Aucun module sélectionné</p>
                </div>
            `;
            return;
        }
        
        let html = '<ul class="list-unstyled mb-0">';
        
        selectedModules.forEach(moduleId => {
            const module = modulesData.find(m => String(m.id) === String(moduleId));
            if (module) {
                html += `
                    <li class="mb-2 d-flex align-items-center gap-2">
                        <i class="bi bi-check-circle-fill text-success flex-shrink-0"></i>
                        <small class="text-truncate" title="${module.nom}">${module.code}</small>
                    </li>
                `;
            }
        });
        
        html += '</ul>';
        listElem.innerHTML = html;
    }
    
    function updateTotalHours() {
        let totalHours = 0;
        
        selectedModules.forEach(moduleId => {
            const module = modulesData.find(m => String(m.id) === String(moduleId));
            if (module) {
                totalHours += (module.volume_cm || 0) + (module.volume_td || 0);
            }
        });
        
        safeSetText('summary-total-hours', totalHours.toFixed(1));
    }
    
    function updateTotalAmount() {
        let totalAmount = 0;
        
        selectedModules.forEach(moduleId => {
            const module = modulesData.find(m => String(m.id) === String(moduleId));
            if (module) {
                totalAmount += calculateModuleMontant(module);
            }
        });
        
        safeSetText('summary-total-amount', formatMoney(totalAmount, false));
    }
    
    function calculateModuleMontant(module) {
        // Taux horaires par défaut (à ajuster selon vos besoins)
        const TAUX_CM = 10000; // FCFA par heure de CM
        const TAUX_TD = 8000;  // FCFA par heure de TD
        
        const montantCM = (module.volume_cm || 0) * TAUX_CM;
        const montantTD = (module.volume_td || 0) * TAUX_TD;
        
        return montantCM + montantTD ;
    }
    
    // ===== GÉNÉRATION DU RÉCAPITULATIF =====
    function generateRecap() {
        generateRecapProfesseur();
        generateRecapClasse();
        generateRecapModules();
    }
    
    function generateRecapProfesseur() {
        if (!formData.professeur) return;
        
        safeSetText('recap-prof-nom', formData.professeur.nom);
        safeSetText('recap-prof-email', formData.professeur.email);
    }
    
    function generateRecapClasse() {
        if (!formData.classe) return;
        
        safeSetText('recap-classe-nom', formData.classe.nom);
        safeSetText('recap-classe-niveau', formData.classe.niveau);
        safeSetText('recap-classe-filiere', formData.classe.filiere);
    }
    
    function generateRecapModules() {
        const tbody = safeGetElement('recap-modules-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        safeSetText('recap-modules-count', selectedModules.length.toString());
        
        let totalCM = 0, totalTD = 0, totalMontant = 0;
        
        selectedModules.forEach(moduleId => {
            const module = modulesData.find(m => String(m.id) === String(moduleId));
            if (module) {
                const montant = calculateModuleMontant(module);
                
                totalCM += module.volume_cm || 0;
                totalTD += module.volume_td || 0;
                totalMontant += montant;
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><strong>${module.code}</strong></td>
                    <td>${module.nom}</td>
                    <td class="text-center">${module.volume_cm || 0}h</td>
                    <td class="text-center">${module.volume_td || 0}h</td>
                    <td class="text-end">${formatMoney(montant, false)}F CFA</td>
                `;
                tbody.appendChild(row);
            }
        });
        
        // Mettre à jour les totaux
        safeSetText('recap-total-cm', totalCM.toFixed(1));
        safeSetText('recap-total-td', totalTD.toFixed(1));
        safeSetText('recap-total-montant', formatMoney(totalMontant, false));
    }
    
    // ===== SOUMISSION DU FORMULAIRE =====
    function handleFormSubmit(event) {
        if (!validateForm()) {
            event.preventDefault();
            return false;
        }
        
        // Ajouter les modules sélectionnés au champ caché
        const hiddenInput = safeGetElement('selected_modules_input');
        if (hiddenInput) {
            hiddenInput.value = JSON.stringify(selectedModules);
        }
        
        // Afficher le loading
        showSubmitLoading();
        
        return true;
    }
    
    function validateForm() {
        if (!formData.professeur) {
            showNotification('Professeur non sélectionné', 'danger');
            showStep(1);
            return false;
        }
        
        if (!formData.classe) {
            showNotification('Classe non sélectionnée', 'danger');
            showStep(2);
            return false;
        }
        
        if (selectedModules.length === 0) {
            showNotification('Aucun module sélectionné', 'danger');
            showStep(3);
            return false;
        }
        
        return true;
    }
    
    function showSubmitLoading() {
        const overlay = safeGetElement('loading-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
            setTimeout(() => {
                overlay.style.opacity = '1';
            }, 10);
        }
    }
    
    function setupFormValidation() {
        const form = safeGetElement('precontrat-form');
        if (!form) return;
        
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && submitBtn.disabled) {
                e.preventDefault();
                return false;
            }
            
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Création en cours...';
            }
        });
    }
    
    // ===== RACCOURCIS CLAVIER =====
    function handleKeyboardShortcuts(event) {
        // Échap : retour en arrière
        if (event.key === 'Escape' && currentStep > 1) {
            event.preventDefault();
            showStep(currentStep - 1);
        }
        
        // Entrée : étape suivante (si valide)
        if (event.key === 'Enter' && event.target.tagName !== 'TEXTAREA') {
            const nextBtn = document.querySelector(`#btn-step-${currentStep}-next`);
            if (nextBtn && !nextBtn.disabled) {
                event.preventDefault();
                nextBtn.click();
            }
        }
    }
    
    // ===== UTILITAIRES =====
    function enableButton(buttonId) {
        const btn = safeGetElement(buttonId);
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('opacity-50');
        }
    }
    
    function disableButton(buttonId) {
        const btn = safeGetElement(buttonId);
        if (btn) {
            btn.disabled = true;
            btn.classList.add('opacity-50');
        }
    }
    
    function formatMoney(amount, withCurrency = true) {
        const formatted = new Intl.NumberFormat('fr-FR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
        
        return withCurrency ? `${formatted} FCFA` : formatted;
    }
    
    function showNotification(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3 shadow-lg`;
        toast.style.zIndex = '9999';
        toast.style.minWidth = '300px';
        toast.style.animation = 'slideInRight 0.5s ease';
        toast.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <i class="bi bi-${getNotificationIcon(type)} fs-5"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Supprimer après 4 secondes
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.5s ease';
            setTimeout(() => {
                toast.remove();
            }, 500);
        }, 4000);
    }
    
    function getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle-fill',
            'danger': 'x-circle-fill',
            'warning': 'exclamation-triangle-fill',
            'info': 'info-circle-fill'
        };
        return icons[type] || 'info-circle-fill';
    }
    
    function animatePageLoad() {
        const elements = document.querySelectorAll('.card, .summary-card');
        elements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                el.style.transition = 'all 0.6s ease';
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }
    
    // ===== ANIMATIONS CSS =====
    const style = document.createElement('style');
    style.textContent = `
        .hover-shadow:hover {
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15) !important;
            transform: translateY(-2px);
        }
        
        @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; transform: translateY(-20px); }
        }
        
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes slideInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(100px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .module-card.selected {
            background-color: #e7f3ff !important;
            border-color: #0d6efd !important;
        }
    `;
    document.head.appendChild(style);
    
    // ===== DÉMARRAGE =====
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', safeInit);
    } else {
        safeInit();
    }
    
    console.log('✅ Wizard de création de précontrat chargé et prêt');
})();