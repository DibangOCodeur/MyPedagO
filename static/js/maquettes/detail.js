/**
 * ========================================
 * MAQUETTE DETAIL - JAVASCRIPT
 * Fichier: maquette_detail.js
 * ========================================
 */

// Variables globales
let allCharts = {};
let currentView = 'table';
let currentFilter = 'all';
let searchTerm = '';
let sortBy = 'nom';

// ========================================
// INITIALISATION
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initialisation de la page de détail maquette...');
    
    // Initialiser tous les composants
    initializeTabs();
    initializeViewToggle();
    initializeFilters();
    initializeSearch();
    initializeSort();
    initializeTableEffects();
    
    console.log('Initialisation terminée');
});

// ========================================
// GESTION DES ONGLETS
// ========================================
function initializeTabs() {
    const tabs = document.querySelectorAll('.custom-tab');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Retirer la classe active de tous les onglets
            tabs.forEach(t => t.classList.remove('active'));
            tabPanes.forEach(pane => {
                pane.classList.remove('active');
                pane.style.display = 'none';
            });
            
            // Activer l'onglet cliqué
            this.classList.add('active');
            const targetPane = document.getElementById(`tab-${targetTab}`);
            if (targetPane) {
                targetPane.classList.add('active');
                targetPane.style.display = 'block';
            }
            
            console.log(`Onglet activé: ${targetTab}`);
        });
    });
}

// ========================================
// TOGGLE VUE TABLEAU/CARTES
// ========================================
function initializeViewToggle() {
    const toggleTable = document.getElementById('toggleTable');
    const toggleCards = document.getElementById('toggleCards');
    const tableView = document.getElementById('tableView');
    const cardsView = document.getElementById('cardsView');
    
    if (!toggleTable || !toggleCards || !tableView || !cardsView) {
        console.warn('Éléments de toggle de vue non trouvés');
        return;
    }
    
    toggleTable.addEventListener('click', function() {
        currentView = 'table';
        tableView.style.display = 'block';
        cardsView.style.display = 'none';
        toggleTable.classList.add('active');
        toggleCards.classList.remove('active');
        console.log('Vue tableau activée');
    });
    
    toggleCards.addEventListener('click', function() {
        currentView = 'cards';
        tableView.style.display = 'none';
        cardsView.style.display = 'flex';
        toggleCards.classList.add('active');
        toggleTable.classList.remove('active');
        console.log('Vue cartes activée');
    });
}

// ========================================
// FILTRES PAR SEMESTRE
// ========================================
function initializeFilters() {
    const filterPills = document.querySelectorAll('.filter-pill');
    
    filterPills.forEach(pill => {
        pill.addEventListener('click', function() {
            // Retirer la classe active de tous les filtres
            filterPills.forEach(p => p.classList.remove('active'));
            
            // Ajouter la classe active au filtre cliqué
            this.classList.add('active');
            
            currentFilter = this.getAttribute('data-filter');
            applyFilters();
            
            console.log(`Filtre activé: ${currentFilter}`);
        });
    });
}

// Fonction pour filtrer par semestre (appelée depuis le template)
function filterBySemestre(semestre) {
    // Activer l'onglet matières
    document.querySelector('.custom-tab[data-tab="matieres"]').click();
    
    // Attendre un peu que l'onglet se charge
    setTimeout(() => {
        const filterPill = document.querySelector(`.filter-pill[data-filter="semestre-${semestre}"]`);
        if (filterPill) {
            filterPill.click();
            // Scroller vers les matières
            document.getElementById('tab-matieres').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, 100);
}

// ========================================
// RECHERCHE
// ========================================
function initializeSearch() {
    const searchInput = document.getElementById('searchMatieres');
    
    if (!searchInput) {
        console.warn('Champ de recherche non trouvé');
        return;
    }
    
    // Recherche en temps réel avec debounce
    let searchTimeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            searchTerm = this.value.toLowerCase().trim();
            applyFilters();
            console.log(`Recherche: "${searchTerm}"`);
        }, 300);
    });
}

// ========================================
// TRI
// ========================================
function initializeSort() {
    const sortOptions = document.querySelectorAll('.sort-option');
    
    sortOptions.forEach(option => {
        option.addEventListener('click', function() {
            sortBy = this.getAttribute('data-sort');
            sortMatieres();
            console.log(`Tri par: ${sortBy}`);
        });
    });
}

function sortMatieres() {
    const tableBody = document.querySelector('#matieresTable tbody');
    const cardsContainer = document.getElementById('cardsView');
    
    if (!tableBody || !cardsContainer) return;
    
    // Récupérer toutes les lignes et cartes
    const rows = Array.from(tableBody.querySelectorAll('.matiere-row'));
    const cards = Array.from(cardsContainer.querySelectorAll('.matiere-card-wrapper'));
    
    // Fonction de tri
    const sortFunction = (a, b) => {
        let valueA, valueB;
        
        switch(sortBy) {
            case 'nom':
                valueA = a.getAttribute('data-nom');
                valueB = b.getAttribute('data-nom');
                return valueA.localeCompare(valueB);
            
            case 'semestre':
                valueA = a.getAttribute('data-semestre');
                valueB = b.getAttribute('data-semestre');
                if (valueA === 'semestre-none') return 1;
                if (valueB === 'semestre-none') return -1;
                return valueA.localeCompare(valueB);
            
            case 'coefficient':
                valueA = parseFloat(a.getAttribute('data-coefficient')) || 0;
                valueB = parseFloat(b.getAttribute('data-coefficient')) || 0;
                return valueB - valueA; // Ordre décroissant
            
            case 'volume':
                valueA = parseFloat(a.getAttribute('data-volume')) || 0;
                valueB = parseFloat(b.getAttribute('data-volume')) || 0;
                return valueB - valueA; // Ordre décroissant
            
            case 'cout':
                valueA = parseFloat(a.getAttribute('data-cout')) || 0;
                valueB = parseFloat(b.getAttribute('data-cout')) || 0;
                return valueB - valueA; // Ordre décroissant
            
            default:
                return 0;
        }
    };
    
    // Trier et réorganiser
    rows.sort(sortFunction);
    cards.sort(sortFunction);
    
    // Réinsérer dans l'ordre trié
    rows.forEach(row => tableBody.appendChild(row));
    cards.forEach(card => cardsContainer.appendChild(card));
    
    // Mettre à jour les numéros de ligne
    rows.forEach((row, index) => {
        const numberCell = row.querySelector('td:first-child');
        if (numberCell) {
            numberCell.textContent = index + 1;
        }
    });
}

// ========================================
// APPLICATION DES FILTRES
// ========================================
function applyFilters() {
    const rows = document.querySelectorAll('.matiere-row');
    const cards = document.querySelectorAll('.matiere-card-wrapper');
    
    let visibleCount = 0;
    
    // Filtrer les lignes du tableau
    rows.forEach(row => {
        const semestre = row.getAttribute('data-semestre');
        const nom = row.getAttribute('data-nom');
        const code = row.getAttribute('data-code');
        const ue = row.getAttribute('data-ue');
        
        let show = true;
        
        // Filtre par semestre
        if (currentFilter !== 'all' && semestre !== currentFilter) {
            show = false;
        }
        
        // Filtre par recherche
        if (searchTerm && show) {
            const searchMatch = nom.includes(searchTerm) || 
                              code.includes(searchTerm) || 
                              ue.includes(searchTerm);
            if (!searchMatch) {
                show = false;
            }
        }
        
        row.style.display = show ? '' : 'none';
        if (show) visibleCount++;
    });
    
    // Filtrer les cartes
    cards.forEach(card => {
        const semestre = card.getAttribute('data-semestre');
        const nom = card.getAttribute('data-nom');
        const code = card.getAttribute('data-code');
        const ue = card.getAttribute('data-ue');
        
        let show = true;
        
        // Filtre par semestre
        if (currentFilter !== 'all' && semestre !== currentFilter) {
            show = false;
        }
        
        // Filtre par recherche
        if (searchTerm && show) {
            const searchMatch = nom.includes(searchTerm) || 
                              code.includes(searchTerm) || 
                              ue.includes(searchTerm);
            if (!searchMatch) {
                show = false;
            }
        }
        
        card.style.display = show ? '' : 'none';
    });
    
    // Mettre à jour le compteur
    updateResultCount(visibleCount);
}

function updateResultCount(count) {
    const resultCount = document.getElementById('resultCount');
    if (resultCount) {
        resultCount.innerHTML = `
            <i class="fas fa-info-circle me-2"></i>
            <strong>${count}</strong> matière(s) trouvée(s)
        `;
    }
}

// ========================================
// EFFETS TABLEAU
// ========================================
function initializeTableEffects() {
    const tableRows = document.querySelectorAll('.matiere-row');
    
    tableRows.forEach(row => {
        // Effet hover
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8f9fa';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
}

// ========================================
// MODAL DÉTAILS MATIÈRE
// ========================================
function showMatiereDetails(nom, code, ue, semestre, coefficient, volumeCM, tauxCM, volumeTD, tauxTD, volumeTotal, coutTotal, description) {
    const modalTitle = document.getElementById('matiereModalTitle');
    const modalBody = document.getElementById('matiereModalBody');
    
    if (!modalTitle || !modalBody) {
        console.error('Modal non trouvé');
        return;
    }
    
    // Mettre à jour le titre
    modalTitle.innerHTML = `<i class="fas fa-book me-2"></i>${nom}`;
    
    // Créer le contenu du modal
    const content = `
        <div class="row">
            <div class="col-md-6 mb-3">
                <div class="p-3 bg-light rounded">
                    <h6 class="text-muted mb-3"><i class="fas fa-info-circle me-2"></i>Informations Générales</h6>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Code:</span>
                        <strong>${code || '-'}</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>UE:</span>
                        <strong>${ue || '-'}</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Semestre:</span>
                        <strong>${semestre || '-'}</strong>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Coefficient:</span>
                        <strong class="text-success">${coefficient}</strong>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6 mb-3">
                <div class="p-3 bg-light rounded">
                    <h6 class="text-muted mb-3"><i class="fas fa-clock me-2"></i>Volumes Horaires</h6>
                    <div class="d-flex justify-content-between mb-2">
                        <span><i class="fas fa-chalkboard-teacher text-primary me-1"></i>CM:</span>
                        <strong>${volumeCM}h</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span><i class="fas fa-users text-info me-1"></i>TD:</span>
                        <strong>${volumeTD}h</strong>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span><i class="fas fa-clock text-primary me-1"></i>Total:</span>
                        <strong class="text-primary">${volumeTotal}h</strong>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6 mb-3">
                <div class="p-3 bg-light rounded">
                    <h6 class="text-muted mb-3"><i class="fas fa-money-bill-wave me-2"></i>Taux Horaires</h6>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Taux CM:</span>
                        <strong>${formatNumber(tauxCM)} F</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Taux TD:</span>
                        <strong>${formatNumber(tauxTD)} F</strong>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Coût CM:</span>
                        <strong>${formatNumber(volumeCM * tauxCM)} F</strong>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Coût TD:</span>
                        <strong>${formatNumber(volumeTD * tauxTD)} F</strong>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6 mb-3">
                <div class="p-3 bg-success bg-opacity-10 rounded border border-success">
                    <h6 class="text-success mb-3"><i class="fas fa-calculator me-2"></i>Coût Total</h6>
                    <div class="text-center">
                        <h2 class="text-success mb-0">${formatNumber(coutTotal)} F CFA</h2>
                        <small class="text-muted">
                            ${volumeCM}h × ${formatNumber(tauxCM)} + ${volumeTD}h × ${formatNumber(tauxTD)}
                        </small>
                    </div>
                </div>
            </div>
            
            ${description ? `
            <div class="col-12">
                <div class="p-3 bg-light rounded">
                    <h6 class="text-muted mb-2"><i class="fas fa-align-left me-2"></i>Description</h6>
                    <p class="mb-0">${description}</p>
                </div>
            </div>
            ` : ''}
        </div>
    `;
    
    modalBody.innerHTML = content;
    
    // Afficher le modal
    const modal = new bootstrap.Modal(document.getElementById('matiereModal'));
    modal.show();
}

// ========================================
// GRAPHIQUES (Chart.js)
// ========================================
function initializeCharts(data) {
    console.log('Initialisation des graphiques...', data);
    
    // Configuration commune
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    padding: 15,
                    font: {
                        size: 12
                    }
                }
            }
        }
    };
    
    // Graphique CM/TD Volume
    const ctxCmTdVolume = document.getElementById('chartCmTdVolume');
    if (ctxCmTdVolume) {
        allCharts.cmTdVolume = new Chart(ctxCmTdVolume, {
            type: 'doughnut',
            data: {
                labels: data.cmTd.labels,
                datasets: [{
                    data: data.cmTd.volumes,
                    backgroundColor: ['#4e73df', '#36b9cc'],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                ...commonOptions,
                cutout: '60%'
            }
        });
    }
    
    // Graphique CM/TD Coût
    const ctxCmTdCout = document.getElementById('chartCmTdCout');
    if (ctxCmTdCout) {
        allCharts.cmTdCout = new Chart(ctxCmTdCout, {
            type: 'doughnut',
            data: {
                labels: data.cmTd.labels,
                datasets: [{
                    data: data.cmTd.couts,
                    backgroundColor: ['#1cc88a', '#f6c23e'],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                ...commonOptions,
                cutout: '60%'
            }
        });
    }
    
    // Graphique Volumes par Semestre
    const ctxSemestresVolumes = document.getElementById('chartSemestresVolumes');
    if (ctxSemestresVolumes) {
        allCharts.semestresVolumes = new Chart(ctxSemestresVolumes, {
            type: 'bar',
            data: {
                labels: data.semestres.labels,
                datasets: [{
                    label: 'Volume Horaire (h)',
                    data: data.semestres.volumesCM.map((cm, i) => cm + data.semestres.volumesTD[i]),
                    backgroundColor: '#4e73df',
                    borderRadius: 5
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + 'h';
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Graphique Top 10 Matières
    const ctxTopMatieres = document.getElementById('chartTopMatieres');
    if (ctxTopMatieres) {
        allCharts.topMatieres = new Chart(ctxTopMatieres, {
            type: 'bar',
            data: {
                labels: data.topMatieres.labels,
                datasets: [{
                    label: 'Coût (F CFA)',
                    data: data.topMatieres.couts,
                    backgroundColor: '#f6c23e',
                    borderRadius: 5
                }]
            },
            options: {
                ...commonOptions,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    ...commonOptions.plugins,
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    // Graphique Volumes par UE
    const ctxUesVolumes = document.getElementById('chartUesVolumes');
    if (ctxUesVolumes) {
        allCharts.uesVolumes = new Chart(ctxUesVolumes, {
            type: 'bar',
            data: {
                labels: data.ues.labels,
                datasets: [{
                    label: 'Volume Horaire (h)',
                    data: data.ues.volumes,
                    backgroundColor: '#36b9cc',
                    borderRadius: 5
                }]
            },
            options: {
                ...commonOptions,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + 'h';
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Graphique Comparaison Semestres
    const ctxComparaisonSemestres = document.getElementById('chartComparaisonSemestres');
    if (ctxComparaisonSemestres) {
        allCharts.comparaisonSemestres = new Chart(ctxComparaisonSemestres, {
            type: 'bar',
            data: {
                labels: data.semestres.labels,
                datasets: [
                    {
                        label: 'CM (h)',
                        data: data.semestres.volumesCM,
                        backgroundColor: '#4e73df',
                        borderRadius: 5
                    },
                    {
                        label: 'TD (h)',
                        data: data.semestres.volumesTD,
                        backgroundColor: '#36b9cc',
                        borderRadius: 5
                    }
                ]
            },
            options: {
                ...commonOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        stacked: false,
                        ticks: {
                            callback: function(value) {
                                return value + 'h';
                            }
                        }
                    },
                    x: {
                        stacked: false
                    }
                }
            }
        });
    }
    
    // Graphique Répartition Coûts
    const ctxRepartitionCouts = document.getElementById('chartRepartitionCouts');
    if (ctxRepartitionCouts) {
        allCharts.repartitionCouts = new Chart(ctxRepartitionCouts, {
            type: 'pie',
            data: {
                labels: data.semestres.labels,
                datasets: [{
                    data: data.semestres.couts,
                    backgroundColor: [
                        '#4e73df',
                        '#1cc88a',
                        '#36b9cc',
                        '#f6c23e',
                        '#e74a3b',
                        '#858796'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: commonOptions
        });
    }
    
    // Graphique Distribution Volumes
    const ctxDistributionVolumes = document.getElementById('chartDistributionVolumes');
    if (ctxDistributionVolumes) {
        allCharts.distributionVolumes = new Chart(ctxDistributionVolumes, {
            type: 'polarArea',
            data: {
                labels: data.ues.labels,
                datasets: [{
                    data: data.ues.volumes,
                    backgroundColor: [
                        'rgba(78, 115, 223, 0.7)',
                        'rgba(28, 200, 138, 0.7)',
                        'rgba(54, 185, 204, 0.7)',
                        'rgba(246, 194, 62, 0.7)',
                        'rgba(231, 74, 59, 0.7)',
                        'rgba(133, 135, 150, 0.7)'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: commonOptions
        });
    }
    
    console.log('Graphiques initialisés:', Object.keys(allCharts));
}

// ========================================
// EXPORT CSV
// ========================================
function exportToCSV() {
    console.log('Export CSV...');
    
    // Afficher le spinner
    showSpinner();
    
    // BOM pour UTF-8
    let csv = '\uFEFF';
    csv += 'N°,Matière,Code,UE,Semestre,Coefficient,Volume CM,Taux CM,Volume TD,Taux TD,Volume Total,Coût Total\n';
    
    // Récupérer toutes les lignes visibles
    const rows = document.querySelectorAll('.matiere-row');
    let rowNumber = 1;
    
    rows.forEach(row => {
        if (row.style.display !== 'none') {
            const cells = row.querySelectorAll('td');
            const rowData = [
                rowNumber++,
                cleanCellText(cells[1]), // Matière
                extractCode(cells[1]),    // Code
                cleanCellText(cells[2]),  // UE
                cleanCellText(cells[3]),  // Semestre
                cleanCellText(cells[4]),  // Coefficient
                cleanCellText(cells[5]),  // Volume CM
                cleanCellText(cells[6]),  // Taux CM
                cleanCellText(cells[7]),  // Volume TD
                cleanCellText(cells[8]),  // Taux TD
                cleanCellText(cells[9]),  // Volume Total
                cleanCellText(cells[10])  // Coût Total
            ];
            
            csv += rowData.map(value => `"${value}"`).join(',') + '\n';
        }
    });
    
    // Créer et télécharger le fichier
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `matieres_maquette_${getFormattedDate()}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Masquer le spinner
    hideSpinner();
    
    console.log('Export CSV terminé');
}

// ========================================
// EXPORT EXCEL
// ========================================
function exportToExcel() {
    alert('Fonctionnalité d\'export Excel à venir!\n\nPour l\'instant, utilisez l\'export CSV qui peut être ouvert avec Excel.');
}

// ========================================
// FONCTIONS UTILITAIRES
// ========================================
function cleanCellText(cell) {
    if (!cell) return '';
    let text = cell.textContent || cell.innerText;
    text = text.trim();
    text = text.replace(/\s+/g, ' '); // Remplacer les espaces multiples
    text = text.replace(/"/g, '""');  // Échapper les guillemets
    return text;
}

function extractCode(cell) {
    if (!cell) return '';
    const codeMatch = cell.textContent.match(/Code:\s*(\S+)/);
    return codeMatch ? codeMatch[1] : '';
}

function getFormattedDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
}

function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '0';
    return new Intl.NumberFormat('fr-FR').format(Math.round(num));
}

function showSpinner() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.classList.add('show');
        spinner.style.display = 'flex';
    }
}

function hideSpinner() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.classList.remove('show');
        spinner.style.display = 'none';
    }
}

// ========================================
// GESTION DE L'IMPRESSION
// ========================================
window.onbeforeprint = function() {
    console.log('Préparation de l\'impression...');
    
    // Afficher la vue tableau pour l'impression
    const cardsView = document.getElementById('cardsView');
    const tableView = document.getElementById('tableView');
    
    if (cardsView && cardsView.style.display !== 'none') {
        tableView.style.display = 'block';
        cardsView.style.display = 'none';
    }
    
    // Afficher toutes les matières (retirer les filtres)
    const rows = document.querySelectorAll('.matiere-row');
    const cards = document.querySelectorAll('.matiere-card-wrapper');
    
    rows.forEach(row => row.style.display = '');
    cards.forEach(card => card.style.display = '');
};

window.onafterprint = function() {
    console.log('Impression terminée');
    
    // Réappliquer les filtres
    applyFilters();
    
    // Restaurer la vue précédente
    if (currentView === 'cards') {
        document.getElementById('toggleCards').click();
    }
};

// ========================================
// GESTION DES ERREURS
// ========================================
window.addEventListener('error', function(e) {
    console.error('Erreur JavaScript:', e.error);
});

// ========================================
// CONSOLE LOG
// ========================================
console.log('Script maquette_detail.js chargé avec succès');