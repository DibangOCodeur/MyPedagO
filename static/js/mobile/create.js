// Ajoutez cette fonction dans votre script existant
function updateProgressBar() {
    const totalSteps = 4;
    const progress = ((currentStep - 1) / (totalSteps - 1)) * 100;
    
    // Créer la barre de progression si elle n'existe pas
    let progressContainer = document.querySelector('.progress-container');
    if (!progressContainer) {
        progressContainer = document.createElement('div');
        progressContainer.className = 'progress-container';
        document.querySelector('.step-indicator').after(progressContainer);
        
        const progressLabel = document.createElement('div');
        progressLabel.className = 'progress-label';
        progressLabel.innerHTML = `<span>Progression</span><span>${Math.round(progress)}%</span>`;
        
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar';
        
        const progressFill = document.createElement('div');
        progressFill.className = 'progress-fill';
        progressFill.style.width = progress + '%';
        
        progressBar.appendChild(progressFill);
        progressContainer.appendChild(progressLabel);
        progressContainer.appendChild(progressBar);
    } else {
        const progressFill = progressContainer.querySelector('.progress-fill');
        const progressLabel = progressContainer.querySelector('.progress-label span:last-child');
        
        if (progressFill) {
            progressFill.style.width = progress + '%';
        }
        if (progressLabel) {
            progressLabel.textContent = Math.round(progress) + '%';
        }
    }
}

// Appelez cette fonction dans goToStep()
function goToStep(step) {
    // Code existant...
    
    currentStep = step;
    
    // Mettre à jour la barre de progression
    updateProgressBar();
    
    // Mettre à jour le récapitulatif à l'étape 4
    if (step === 4) {
        updateSummary();
    }
}

// Initialiser la barre de progression au chargement
document.addEventListener('DOMContentLoaded', function() {
    // Code existant...
    
    // Initialiser la barre de progression
    setTimeout(updateProgressBar, 100);
});